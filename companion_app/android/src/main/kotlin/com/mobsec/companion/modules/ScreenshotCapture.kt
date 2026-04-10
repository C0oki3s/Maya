package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class ScreenshotCapture(private val shell: ShellRunner) {
    fun capture(request: CommandRequest): CommandResponse {
        val output = request.params["output_path"] ?: "/sdcard/mobsec_screenshot.png"
        val result = shell.run("screencap -p $output")
        return if (result.exitCode == 0) {
            CommandResponse(id = request.id, status = "success", data = mapOf("path" to output, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim()))
        } else {
            CommandResponse(id = request.id, status = "error", data = mapOf("path" to output, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim()), error = result.stderr.ifBlank { "screenshot failed" })
        }
    }
}