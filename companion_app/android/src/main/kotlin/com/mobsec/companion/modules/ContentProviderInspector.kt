package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Drozer-equivalent: app.provider.*
 *
 * Query, insert, update, delete content provider data. Read files through
 * file-backed providers. Enumerate content URIs and test for SQL injection
 * and path-traversal vulnerabilities.
 */
class ContentProviderInspector(private val shell: ShellRunner) {

    /** app.provider.info — list content providers with permissions and path-permissions. */
    fun info(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val result = shell.run("dumpsys package $pkg | grep -A20 'ContentProvider' | grep -E 'Provider|authority|permission|Grant|Path|multiprocess|exported'")
        return ok(request, mapOf("package" to pkg, "providers" to result.stdout.trim().take(4096)))
    }

    /** app.provider.query — query a content URI (equivalent to drozer's provider.query). */
    fun query(request: CommandRequest): CommandResponse {
        val uri = request.params["uri"] ?: return missing(request, "uri")
        val projection = request.params["projection"]
        val selection = request.params["selection"]
        val selectionArgs = request.params["selection_args"]
        val sortOrder = request.params["sort_order"]

        val cmd = buildString {
            append("content query --uri $uri")
            if (projection != null) append(" --projection '$projection'")
            if (selection != null) append(" --where '$selection'")
            if (selectionArgs != null) append(" --arg '$selectionArgs'")
            if (sortOrder != null) append(" --sort '$sortOrder'")
        }
        val result = shell.run(cmd)
        return ok(request, mapOf(
            "uri" to uri,
            "command" to cmd,
            "result" to result.stdout.trim().take(8192),
            "stderr" to result.stderr.trim(),
            "exit_code" to result.exitCode.toString(),
        ))
    }

    /** app.provider.insert — insert a row into a content provider. */
    fun insert(request: CommandRequest): CommandResponse {
        val uri = request.params["uri"] ?: return missing(request, "uri")
        val bindings = request.params["bindings"] ?: return missing(request, "bindings")
        // bindings format: "type:column:value,type:column:value"
        // types: s=string, i=integer, l=long, f=float, d=double, b=boolean
        val cmd = buildString {
            append("content insert --uri $uri")
            for (binding in bindings.split(",")) {
                val parts = binding.trim().split(":")
                if (parts.size >= 3) {
                    val type = parts[0]
                    val col = parts[1]
                    val value = parts.drop(2).joinToString(":")
                    val typeFlag = when (type) {
                        "s" -> "s"
                        "i" -> "i"
                        "l" -> "l"
                        "f" -> "f"
                        "d" -> "d"
                        "b" -> "b"
                        else -> "s"
                    }
                    append(" --bind $col:$typeFlag:$value")
                }
            }
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("uri" to uri, "command" to cmd, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim(), "exit_code" to result.exitCode.toString()))
    }

    /** app.provider.update — update rows in a content provider. */
    fun update(request: CommandRequest): CommandResponse {
        val uri = request.params["uri"] ?: return missing(request, "uri")
        val bindings = request.params["bindings"] ?: return missing(request, "bindings")
        val selection = request.params["selection"]
        val cmd = buildString {
            append("content update --uri $uri")
            for (binding in bindings.split(",")) {
                val parts = binding.trim().split(":")
                if (parts.size >= 3) {
                    append(" --bind ${parts[1]}:${parts[0]}:${parts.drop(2).joinToString(":")}")
                }
            }
            if (selection != null) append(" --where '$selection'")
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("uri" to uri, "command" to cmd, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim(), "exit_code" to result.exitCode.toString()))
    }

    /** app.provider.delete — delete rows from a content provider. */
    fun delete(request: CommandRequest): CommandResponse {
        val uri = request.params["uri"] ?: return missing(request, "uri")
        val selection = request.params["selection"]
        val cmd = buildString {
            append("content delete --uri $uri")
            if (selection != null) append(" --where '$selection'")
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("uri" to uri, "command" to cmd, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim(), "exit_code" to result.exitCode.toString()))
    }

    /** app.provider.read — read a file through a file-backed content provider. */
    fun readFile(request: CommandRequest): CommandResponse {
        val uri = request.params["uri"] ?: return missing(request, "uri")
        val result = shell.run("content read --uri $uri")
        return ok(request, mapOf("uri" to uri, "content" to result.stdout.trim().take(8192), "stderr" to result.stderr.trim(), "exit_code" to result.exitCode.toString()))
    }

    /** scanner.provider.finduris — brute-force content URIs for a package. */
    fun findUris(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")

        // Step 1: Get authorities from the package
        val authResult = shell.run("dumpsys package $pkg | grep -E 'authority=' | sed 's/.*authority=//' | sed 's/ .*//'")
        val authorities = authResult.stdout.trim().lines().filter { it.isNotBlank() }.distinct()

        if (authorities.isEmpty()) {
            return ok(request, mapOf("package" to pkg, "note" to "no content providers found"))
        }

        // Step 2: Try common path patterns against each authority
        val commonPaths = listOf(
            "", "/", "/data", "/items", "/users", "/keys", "/passwords",
            "/accounts", "/files", "/notes", "/settings", "/config",
            "/entries", "/records", "/content", "/values", "/list",
        )
        val accessibleUris = mutableListOf<String>()
        val inaccessibleUris = mutableListOf<String>()

        for (authority in authorities) {
            for (path in commonPaths) {
                val uri = "content://$authority$path"
                val result = shell.run("content query --uri '$uri' 2>&1 | head -3")
                val output = result.stdout + result.stderr
                when {
                    output.contains("Permission Denial") || output.contains("SecurityException") ->
                        inaccessibleUris.add("$uri (permission denied)")
                    output.contains("Unknown URI") || output.contains("UnsupportedOperationException") ||
                    output.contains("No content provider") -> {} // not valid
                    result.exitCode == 0 && output.isNotBlank() && !output.contains("Error") ->
                        accessibleUris.add(uri)
                }
            }
        }

        // Step 3: Also try to guess paths from strings in the APK
        val apkPath = shell.run("pm path $pkg | head -1 | sed 's/package://'").stdout.trim()
        if (apkPath.isNotBlank()) {
            val strings = shell.run("strings $apkPath 2>/dev/null | grep 'content://' | head -20")
            for (line in strings.stdout.lines()) {
                val match = Regex("content://[\\w./]+").find(line)
                if (match != null) {
                    val uri = match.value
                    if (uri !in accessibleUris && uri !in inaccessibleUris.map { it.substringBefore(" (") }) {
                        val test = shell.run("content query --uri '$uri' 2>&1 | head -3")
                        if (test.exitCode == 0 && !test.stdout.contains("Unknown URI")) {
                            accessibleUris.add(uri)
                        }
                    }
                }
            }
        }

        return ok(request, mapOf(
            "package" to pkg,
            "authorities" to authorities.joinToString("\n"),
            "accessible_uris" to accessibleUris.joinToString("\n"),
            "inaccessible_uris" to inaccessibleUris.joinToString("\n"),
            "accessible_count" to accessibleUris.size.toString(),
        ))
    }

    /** scanner.provider.injection — test content URIs for SQL injection. */
    fun injectionScan(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")

        // Get accessible URIs first
        val findResult = findUris(request)
        val accessibleUris = (findResult.data["accessible_uris"] ?: "").lines().filter { it.isNotBlank() }

        val projectionVulnerable = mutableListOf<String>()
        val selectionVulnerable = mutableListOf<String>()
        val notVulnerable = mutableListOf<String>()

        for (uri in accessibleUris) {
            // Test projection injection
            val projTest = shell.run("content query --uri '$uri' --projection \"'\" 2>&1")
            val projOutput = projTest.stdout + projTest.stderr
            if (projOutput.contains("unrecognized token") || projOutput.contains("SQLITE_ERROR") || projOutput.contains("syntax error")) {
                projectionVulnerable.add(uri)
            }

            // Test selection / where injection
            val selTest = shell.run("content query --uri '$uri' --where \"'\" 2>&1")
            val selOutput = selTest.stdout + selTest.stderr
            if (selOutput.contains("unrecognized token") || selOutput.contains("SQLITE_ERROR") || selOutput.contains("syntax error")) {
                selectionVulnerable.add(uri)
            }

            if (uri !in projectionVulnerable && uri !in selectionVulnerable) {
                notVulnerable.add(uri)
            }
        }

        return ok(request, mapOf(
            "package" to pkg,
            "injection_in_projection" to projectionVulnerable.joinToString("\n"),
            "injection_in_selection" to selectionVulnerable.joinToString("\n"),
            "not_vulnerable" to notVulnerable.joinToString("\n"),
            "total_scanned" to accessibleUris.size.toString(),
        ))
    }

    /** scanner.provider.traversal — test file-backed providers for path traversal. */
    fun traversalScan(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")

        val authResult = shell.run("dumpsys package $pkg | grep -E 'authority=' | sed 's/.*authority=//' | sed 's/ .*//'")
        val authorities = authResult.stdout.trim().lines().filter { it.isNotBlank() }.distinct()

        val traversalPaths = listOf(
            "../../../etc/hosts",
            "../../../../etc/hosts",
            "../../../../../etc/hosts",
            "../../../../../../etc/hosts",
            "../../../../../data/local.prop",
            "../../../../../system/build.prop",
        )

        val vulnerable = mutableListOf<String>()
        val notVulnerable = mutableListOf<String>()

        for (authority in authorities) {
            var isVuln = false
            for (path in traversalPaths) {
                val uri = "content://$authority/$path"
                val result = shell.run("content read --uri '$uri' 2>&1 | head -5")
                val output = result.stdout + result.stderr
                if (output.contains("127.0.0.1") || output.contains("localhost") ||
                    output.contains("ro.") || (result.exitCode == 0 && output.length > 10 && !output.contains("FileNotFoundException"))) {
                    vulnerable.add("content://$authority (path: $path)")
                    isVuln = true
                    break
                }
            }
            if (!isVuln) notVulnerable.add("content://$authority")
        }

        return ok(request, mapOf(
            "package" to pkg,
            "vulnerable" to vulnerable.joinToString("\n"),
            "not_vulnerable" to notVulnerable.joinToString("\n"),
        ))
    }

    private fun ok(request: CommandRequest, data: Map<String, String>): CommandResponse =
        CommandResponse(id = request.id, status = "success", data = data)

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}
