package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class AppManager(private val shell: ShellRunner) {
    fun install(request: CommandRequest): CommandResponse {
        val path = request.params["apk_path"] ?: request.params["path"] ?: return missing(request, "apk_path")
        val result = shell.run("pm install -r $path", useRoot = true)
        return response(request, result.stdout, result.stderr, result.exitCode)
    }

    fun uninstall(request: CommandRequest): CommandResponse {
        val packageName = request.params["package_name"] ?: request.params["package"] ?: return missing(request, "package_name")
        val result = shell.run("pm uninstall $packageName", useRoot = true)
        return response(request, result.stdout, result.stderr, result.exitCode)
    }

    fun launch(request: CommandRequest): CommandResponse {
        val packageName = request.params["package_name"] ?: request.params["package"] ?: return missing(request, "package_name")
        val result = shell.run("monkey -p $packageName -c android.intent.category.LAUNCHER 1")
        return response(request, result.stdout, result.stderr, result.exitCode)
    }

    fun listPackages(request: CommandRequest): CommandResponse {
        val result = shell.run("pm list packages")
        return response(request, result.stdout, result.stderr, result.exitCode)
    }

    private fun response(request: CommandRequest, stdout: String, stderr: String, exitCode: Int): CommandResponse {
        return if (exitCode == 0) {
            CommandResponse(id = request.id, status = "success", data = mapOf("stdout" to stdout.trim(), "stderr" to stderr.trim(), "exit_code" to exitCode.toString()))
        } else {
            CommandResponse(id = request.id, status = "error", data = mapOf("stdout" to stdout.trim(), "stderr" to stderr.trim(), "exit_code" to exitCode.toString()), error = stderr.ifBlank { "command failed" })
        }
    }

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}