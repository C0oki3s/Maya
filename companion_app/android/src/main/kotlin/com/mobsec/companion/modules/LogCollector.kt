package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class LogCollector(private val shell: ShellRunner) {
    fun collect(request: CommandRequest): CommandResponse {
        val packageName = request.params["package_name"]
        val baseCommand = if (packageName.isNullOrBlank()) {
            "logcat -d -v threadtime"
        } else {
            "logcat -d -v threadtime | grep $packageName"
        }
        val result = shell.run(baseCommand)
        return if (result.exitCode == 0) {
            CommandResponse(id = request.id, status = "success", data = mapOf("logs" to result.stdout))
        } else {
            CommandResponse(id = request.id, status = "error", data = mapOf("logs" to result.stdout), error = result.stderr.ifBlank { "log collection failed" })
        }
    }
}