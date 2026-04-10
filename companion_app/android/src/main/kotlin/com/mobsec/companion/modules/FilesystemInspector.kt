package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class FilesystemInspector(private val shell: ShellRunner) {
    fun inspect(request: CommandRequest): CommandResponse {
        val path = request.params["path"] ?: "/sdcard"
        val recursive = request.params["recursive"] == "true"
        val flag = if (recursive) "-laR" else "-la"
        val result = shell.run("ls $flag $path", useRoot = true)
        return response(request, result.stdout, result.stderr, result.exitCode)
    }

    fun readFile(request: CommandRequest): CommandResponse {
        val path = request.params["path"] ?: return missing(request, "path")
        val result = shell.run("cat $path", useRoot = true)
        return response(request, result.stdout, result.stderr, result.exitCode)
    }

    fun getAppData(request: CommandRequest): CommandResponse {
        val packageName = request.params["package_name"] ?: request.params["package"] ?: return missing(request, "package_name")
        val archive = "/sdcard/${packageName}.tar.gz"
        val result = shell.run("tar -czf $archive /data/data/$packageName", useRoot = true)
        return if (result.exitCode == 0) {
            CommandResponse(id = request.id, status = "success", data = mapOf("archive" to archive, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim()))
        } else {
            CommandResponse(id = request.id, status = "error", data = mapOf("archive" to archive, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim()), error = result.stderr.ifBlank { "archive failed" })
        }
    }

    private fun response(request: CommandRequest, stdout: String, stderr: String, exitCode: Int): CommandResponse {
        return if (exitCode == 0) {
            CommandResponse(id = request.id, status = "success", data = mapOf("stdout" to stdout.trim(), "stderr" to stderr.trim(), "exit_code" to exitCode.toString()))
        } else {
            CommandResponse(id = request.id, status = "error", data = mapOf("stdout" to stdout.trim(), "stderr" to stderr.trim(), "exit_code" to exitCode.toString()), error = stderr.ifBlank { "filesystem command failed" })
        }
    }

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}