package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class FridaGadgetInjector(private val shell: ShellRunner) {
    fun hookRuntime(request: CommandRequest): CommandResponse {
        val packageName = request.params["package_name"] ?: return missing(request, "package_name")
        val script = request.params["script"] ?: ""
        val preview = if (script.length > 120) script.take(120) + "..." else script
        return CommandResponse(
            id = request.id,
            status = "success",
            data = mapOf(
                "package_name" to packageName,
                "mode" to "runtime-hook",
                "script_preview" to preview,
                "note" to "Route custom scripts to frida-server or gadget helper on device",
            ),
        )
    }

    fun sslUnpin(request: CommandRequest): CommandResponse {
        val packageName = request.params["package_name"] ?: return missing(request, "package_name")
        val result = shell.run("pidof $packageName")
        return CommandResponse(
            id = request.id,
            status = "success",
            data = mapOf(
                "package_name" to packageName,
                "pid" to result.stdout.trim(),
                "note" to "Inject SSL bypass via Frida helper or running frida-server session",
            ),
        )
    }

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}