package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class TrafficCapture(private val shell: ShellRunner) {
    fun captureTraffic(request: CommandRequest): CommandResponse {
        val action = request.params["action"] ?: "status"
        return CommandResponse(
            id = request.id,
            status = "success",
            data = mapOf(
                "action" to action,
                "note" to "Companion should start/stop local capture helpers or report capture state",
            ),
        )
    }

    fun configureProxy(request: CommandRequest): CommandResponse {
        val host = request.params["host"] ?: "127.0.0.1"
        val port = request.params["port"] ?: "8080"
        val result = shell.run("settings put global http_proxy ${host}:${port}")
        return resultToResponse(request, result.stdout, result.stderr, result.exitCode)
    }

    fun clearProxy(request: CommandRequest): CommandResponse {
        val result = shell.run("settings put global http_proxy :0")
        return resultToResponse(request, result.stdout, result.stderr, result.exitCode)
    }

    private fun resultToResponse(request: CommandRequest, stdout: String, stderr: String, exitCode: Int): CommandResponse {
        return if (exitCode == 0) {
            CommandResponse(id = request.id, status = "success", data = mapOf("stdout" to stdout.trim(), "stderr" to stderr.trim(), "exit_code" to exitCode.toString()))
        } else {
            CommandResponse(id = request.id, status = "error", data = mapOf("stdout" to stdout.trim(), "stderr" to stderr.trim(), "exit_code" to exitCode.toString()), error = stderr.ifBlank { "proxy command failed" })
        }
    }
}