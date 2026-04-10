package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Drozer-equivalent: app.broadcast.*
 *
 * Enumerate exported broadcast receivers, retrieve intent-filter details,
 * and send broadcasts with constructed intents.
 */
class BroadcastInspector(private val shell: ShellRunner) {

    /** app.broadcast.info — list broadcast receivers with export/permission details. */
    fun info(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val result = shell.run("dumpsys package $pkg | grep -B3 -A8 'Receiver' | grep -E 'Receiver|exported|permission|Action|Categor'")
        return ok(request, mapOf("package" to pkg, "receivers" to result.stdout.trim().take(4096)))
    }

    /** app.broadcast.send — send a broadcast with a fully-specified intent. */
    fun send(request: CommandRequest): CommandResponse {
        val action = request.params["action"]
        val component = request.params["component"]
        val pkg = request.params["package"]
        val receiver = request.params["receiver"]
        val dataUri = request.params["data_uri"]
        val mimeType = request.params["mime_type"]
        val extras = request.params["extras"]
        val flags = request.params["flags"]
        val category = request.params["category"]

        val cmd = buildString {
            append("am broadcast")
            if (action != null) append(" -a $action")
            if (component != null) {
                append(" -n $component")
            } else if (pkg != null && receiver != null) {
                append(" -n $pkg/$receiver")
            }
            if (category != null) {
                for (cat in category.split(",")) {
                    append(" -c ${cat.trim()}")
                }
            }
            if (dataUri != null) append(" -d '$dataUri'")
            if (mimeType != null) append(" -t '$mimeType'")
            if (flags != null) append(" -f $flags")
            if (extras != null) {
                for (extra in extras.split(",")) {
                    val parts = extra.trim().split(":")
                    if (parts.size >= 3) {
                        val type = parts[0]
                        val key = parts[1]
                        val value = parts.drop(2).joinToString(":")
                        val flag = when (type) {
                            "string", "s" -> "--es"
                            "int", "i" -> "--ei"
                            "long", "l" -> "--el"
                            "float", "f" -> "--ef"
                            "bool", "b" -> "--ez"
                            "uri", "u" -> "--eu"
                            else -> "--es"
                        }
                        append(" $flag '$key' '$value'")
                    }
                }
            }
        }

        if (action == null && component == null && (pkg == null || receiver == null)) {
            return CommandResponse(id = request.id, status = "error", error = "must specify action or component (package+receiver)")
        }

        val result = shell.run(cmd)
        return ok(request, mapOf(
            "command" to cmd,
            "stdout" to result.stdout.trim(),
            "stderr" to result.stderr.trim(),
            "exit_code" to result.exitCode.toString(),
        ))
    }

    /** Enumerate all exported broadcast receivers across all packages (or filtered). */
    fun findExported(request: CommandRequest): CommandResponse {
        val filter = request.params["filter"]
        val cmd = if (filter != null) {
            "dumpsys package | grep -B5 'exported=true' | grep -i 'Receiver' | grep -i '$filter' | head -60"
        } else {
            "dumpsys package | grep -B5 'exported=true' | grep -i 'Receiver' | head -60"
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("exported_receivers" to result.stdout.trim()))
    }

    /** Send a test broadcast to check if a receiver is responsive. */
    fun probe(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val receiver = request.params["receiver"] ?: return missing(request, "receiver")
        val action = request.params["action"] ?: "android.intent.action.BOOT_COMPLETED"
        val result = shell.run("am broadcast -a $action -n $pkg/$receiver 2>&1")
        return ok(request, mapOf(
            "package" to pkg,
            "receiver" to receiver,
            "action" to action,
            "stdout" to result.stdout.trim(),
            "stderr" to result.stderr.trim(),
            "exit_code" to result.exitCode.toString(),
        ))
    }

    private fun ok(request: CommandRequest, data: Map<String, String>): CommandResponse =
        CommandResponse(id = request.id, status = "success", data = data)

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}
