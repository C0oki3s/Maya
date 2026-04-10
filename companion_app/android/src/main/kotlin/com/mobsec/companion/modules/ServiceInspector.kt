package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Drozer-equivalent: app.service.*
 *
 * Enumerate exported services, retrieve service info, start/stop services,
 * and send messages to bound services.
 */
class ServiceInspector(private val shell: ShellRunner) {

    /** app.service.info — list services for a package with export/permission details. */
    fun info(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val result = shell.run("dumpsys package $pkg | grep -B3 -A8 'Service' | grep -E 'Service|exported|permission|Action|intent'")
        return ok(request, mapOf("package" to pkg, "services" to result.stdout.trim().take(4096)))
    }

    /** app.service.start — start a service with a constructed intent. */
    fun start(request: CommandRequest): CommandResponse {
        val component = request.params["component"]
        val pkg = request.params["package"]
        val service = request.params["service"]
        val action = request.params["action"]
        val extras = request.params["extras"]
        val mimeType = request.params["mime_type"]
        val dataUri = request.params["data_uri"]

        val cmd = buildString {
            append("am startservice")
            if (action != null) append(" -a $action")
            if (component != null) {
                append(" -n $component")
            } else if (pkg != null && service != null) {
                append(" -n $pkg/$service")
            }
            if (dataUri != null) append(" -d '$dataUri'")
            if (mimeType != null) append(" -t '$mimeType'")
            if (extras != null) {
                for (extra in extras.split(",")) {
                    val parts = extra.trim().split(":")
                    if (parts.size >= 3) {
                        val flag = when (parts[0]) {
                            "string", "s" -> "--es"
                            "int", "i" -> "--ei"
                            "long", "l" -> "--el"
                            "float", "f" -> "--ef"
                            "bool", "b" -> "--ez"
                            else -> "--es"
                        }
                        append(" $flag '${parts[1]}' '${parts.drop(2).joinToString(":")}'")
                    }
                }
            }
        }

        if (component == null && (pkg == null || service == null) && action == null) {
            return CommandResponse(id = request.id, status = "error", error = "must specify component, action, or package+service")
        }

        val result = shell.run(cmd)
        return ok(request, mapOf(
            "command" to cmd,
            "stdout" to result.stdout.trim(),
            "stderr" to result.stderr.trim(),
            "exit_code" to result.exitCode.toString(),
        ))
    }

    /** app.service.stop — stop a running service. */
    fun stop(request: CommandRequest): CommandResponse {
        val component = request.params["component"]
        val pkg = request.params["package"]
        val service = request.params["service"]

        val cmd = buildString {
            append("am stopservice")
            if (component != null) {
                append(" -n $component")
            } else if (pkg != null && service != null) {
                append(" -n $pkg/$service")
            } else {
                return missing(request, "component or package+service")
            }
        }

        val result = shell.run(cmd)
        return ok(request, mapOf(
            "command" to cmd,
            "stdout" to result.stdout.trim(),
            "stderr" to result.stderr.trim(),
            "exit_code" to result.exitCode.toString(),
        ))
    }

    /** List all running services on the device. */
    fun listRunning(request: CommandRequest): CommandResponse {
        val filter = request.params["filter"]
        val cmd = if (filter != null) {
            "dumpsys activity services | grep -i '$filter' | head -60"
        } else {
            "dumpsys activity services | grep 'ServiceRecord' | head -60"
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("running_services" to result.stdout.trim()))
    }

    /** Enumerate all exported services (across all or filtered packages). */
    fun findExported(request: CommandRequest): CommandResponse {
        val filter = request.params["filter"]
        val cmd = if (filter != null) {
            "dumpsys package | grep -B5 'exported=true' | grep -i 'Service' | grep -i '$filter' | head -60"
        } else {
            "dumpsys package | grep -B5 'exported=true' | grep -i 'Service' | head -60"
        }
        val result = shell.run(cmd)
        return ok(request, mapOf("exported_services" to result.stdout.trim()))
    }

    /** Send an intent to a service (app.service.send equivalent via am). */
    fun send(request: CommandRequest): CommandResponse {
        val component = request.params["component"]
        val pkg = request.params["package"]
        val service = request.params["service"]
        val action = request.params["action"]
        val extras = request.params["extras"]
        val msg = request.params["msg"]

        val cmd = buildString {
            append("am startservice")
            if (action != null) append(" -a $action")
            if (component != null) {
                append(" -n $component")
            } else if (pkg != null && service != null) {
                append(" -n $pkg/$service")
            }
            if (msg != null) append(" --es msg '$msg'")
            if (extras != null) {
                for (extra in extras.split(",")) {
                    val parts = extra.trim().split(":")
                    if (parts.size >= 3) {
                        val flag = when (parts[0]) {
                            "string", "s" -> "--es"
                            "int", "i" -> "--ei"
                            "bool", "b" -> "--ez"
                            else -> "--es"
                        }
                        append(" $flag '${parts[1]}' '${parts.drop(2).joinToString(":")}'")
                    }
                }
            }
        }

        val result = shell.run(cmd)
        return ok(request, mapOf("command" to cmd, "stdout" to result.stdout.trim(), "stderr" to result.stderr.trim(), "exit_code" to result.exitCode.toString()))
    }

    private fun ok(request: CommandRequest, data: Map<String, String>): CommandResponse =
        CommandResponse(id = request.id, status = "success", data = data)

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}
