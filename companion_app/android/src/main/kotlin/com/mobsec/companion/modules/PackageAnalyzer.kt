package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Drozer-equivalent: app.package.*
 *
 * Provides package enumeration, info retrieval, attack surface analysis,
 * manifest dumping, permission enumeration, native library listing,
 * and shared-UID grouping — all via on-device shell commands.
 */
class PackageAnalyzer(private val shell: ShellRunner) {

    /** app.package.list — list installed packages, optionally filter by keyword. */
    fun listPackages(request: CommandRequest): CommandResponse {
        val filter = request.params["filter"] ?: ""
        val flags = request.params["flags"] ?: "" // e.g. "-3" for third-party only
        val cmd = buildString {
            append("pm list packages")
            if (flags.isNotBlank()) append(" $flags")
            if (filter.isNotBlank()) append(" | grep -i '$filter'")
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("packages" to result.stdout.trim(), "count" to result.stdout.trim().lines().filter { it.isNotBlank() }.size.toString()))
    }

    /** app.package.info — detailed info about a specific package. */
    fun packageInfo(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val pm = shell.run("pm dump $pkg | head -80", timeoutSec = 15)
        val apkPath = shell.run("pm path $pkg", timeoutSec = 5)
        val uid = shell.run("dumpsys package $pkg | grep 'userId=' | head -1", timeoutSec = 10)
        val version = shell.run("dumpsys package $pkg | grep 'versionName' | head -1", timeoutSec = 10)
        return ok(request, mapOf(
            "package" to pkg,
            "apk_path" to apkPath.stdout.trim(),
            "uid" to uid.stdout.trim(),
            "version" to version.stdout.trim(),
            "pm_dump" to pm.stdout.trim().take(4096),
        ))
    }

    /** app.package.attacksurface — enumerate exported components. */
    fun attackSurface(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")

        // Android 14+ / Samsung: components in resolver tables indicate exported status
        // Count unique component names from resolver tables
        val actCount = shell.run("dumpsys package $pkg | grep '$pkg.*Activity.*filter' | sort -u | wc -l", timeoutSec = 15)
        val rcvCount = shell.run("dumpsys package $pkg | grep '$pkg.*Receiver.*filter' | sort -u | wc -l", timeoutSec = 15)
        val prvCount = shell.run("dumpsys package $pkg | grep '$pkg.*Provider' | sort -u | wc -l", timeoutSec = 15)
        val svcCount = shell.run("dumpsys package $pkg | grep '$pkg.*Service.*filter' | sort -u | wc -l", timeoutSec = 15)
        val debuggable = shell.run("run-as $pkg id 2>&1 || echo 'not-debuggable'", timeoutSec = 5)
        val dbgCheck = shell.run("dumpsys package $pkg | grep 'DEBUGGABLE' | head -1", timeoutSec = 10)
        val browsable = shell.run("dumpsys package $pkg | grep -B5 'BROWSABLE' | grep '$pkg' | sort -u | head -10", timeoutSec = 15)

        val isDebuggable = dbgCheck.stdout.contains("DEBUGGABLE") || !debuggable.stdout.contains("not-debuggable")

        return ok(request, mapOf(
            "package" to pkg,
            "exported_activities" to (actCount.stdout.trim().toIntOrNull() ?: 0).toString(),
            "exported_receivers" to (rcvCount.stdout.trim().toIntOrNull() ?: 0).toString(),
            "exported_providers" to (prvCount.stdout.trim().toIntOrNull() ?: 0).toString(),
            "exported_services" to (svcCount.stdout.trim().toIntOrNull() ?: 0).toString(),
            "is_debuggable" to isDebuggable.toString(),
            "browsable_activities" to browsable.stdout.trim().take(2048),
        ))
    }

    /** app.package.manifest — dump the AndroidManifest.xml */
    fun manifest(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        // Try multiple approaches for manifest extraction
        val apkPath = shell.run("pm path $pkg | head -1 | sed 's/package://'")
        val path = apkPath.stdout.trim()
        // aapt dump is typically available on device
        val aapt = shell.run("aapt dump xmltree $path AndroidManifest.xml 2>/dev/null || aapt2 dump xmltree --file AndroidManifest.xml $path 2>/dev/null")
        return if (aapt.stdout.isNotBlank()) {
            ok(request, mapOf("package" to pkg, "manifest" to aapt.stdout.take(8192)))
        } else {
            // Fallback: use pm dump
            val dump = shell.run("pm dump $pkg | head -200")
            ok(request, mapOf("package" to pkg, "manifest_excerpt" to dump.stdout.take(8192), "note" to "aapt not available; showing pm dump"))
        }
    }

    /** app.package.launchintent — get the launch intent for a package. */
    fun launchIntent(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val result = shell.run("cmd package resolve-activity --brief $pkg | tail -1")
        val dumpsys = shell.run("dumpsys package $pkg | grep -A2 'android.intent.action.MAIN' | head -6")
        return ok(request, mapOf("package" to pkg, "launch_activity" to result.stdout.trim(), "main_intent" to dumpsys.stdout.trim()))
    }

    /** app.package.native — list native libraries. */
    fun nativeLibraries(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val apkPath = shell.run("pm path $pkg | head -1 | sed 's/package://'")
        val nativeDir = shell.run("ls -la /data/app/*${pkg}*/lib/ 2>/dev/null || ls -la /data/app/${pkg}/lib/ 2>/dev/null")
        val unzip = shell.run("unzip -l ${apkPath.stdout.trim()} 'lib/*' 2>/dev/null | head -40")
        return ok(request, mapOf(
            "package" to pkg,
            "native_libs_dir" to nativeDir.stdout.trim(),
            "apk_native_libs" to unzip.stdout.trim(),
        ))
    }

    /** app.package.shareduid — find packages sharing a UID. */
    fun sharedUid(request: CommandRequest): CommandResponse {
        val uid = request.params["uid"]
        val pkg = request.params["package"]
        if (uid == null && pkg == null) return missing(request, "uid or package")

        val targetUid = if (uid != null) uid else {
            val uidLine = shell.run("dumpsys package ${pkg} | grep 'userId='")
            uidLine.stdout.trim().replace(Regex(".*userId=(\\d+).*"), "$1")
        }
        val result = shell.run("dumpsys package | grep 'userId=$targetUid' -B3 | grep 'Package \\['")
        return ok(request, mapOf("uid" to targetUid, "shared_packages" to result.stdout.trim()))
    }

    /** List permissions used by a package. */
    fun permissions(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val uses = shell.run("dumpsys package $pkg | grep 'android.permission' | sort -u")
        val defines = shell.run("dumpsys package $pkg | grep -A1 'declared permissions' | head -20")
        val granted = shell.run("dumpsys package $pkg | grep 'granted=true'")
        return ok(request, mapOf(
            "package" to pkg,
            "uses_permissions" to uses.stdout.trim(),
            "defines_permissions" to defines.stdout.trim(),
            "granted_permissions" to granted.stdout.trim(),
        ))
    }

    /** Identify backup-allowed packages (app.backup.info equivalent). */
    fun backupInfo(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val result = shell.run("dumpsys package $pkg | grep -i 'allowBackup\\|backup'")
        return ok(request, mapOf("package" to pkg, "backup_info" to result.stdout.trim()))
    }

    private fun ok(request: CommandRequest, data: Map<String, String>): CommandResponse =
        CommandResponse(id = request.id, status = "success", data = data)

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}
