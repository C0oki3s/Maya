package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Drozer-equivalent: app.activity.*
 *
 * Lists exported activities, retrieves activity info, launches activities
 * with constructed intents including extras, categories, data URIs, and flags.
 */
class ActivityInspector(private val shell: ShellRunner) {

    /** app.activity.info — list activities for a package with export/permission details. */
    fun info(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val unexported = request.params["include_unexported"] == "true"
        val filter = if (unexported) "Activity" else "exported=true"
        val result = shell.run("dumpsys package $pkg | grep -B5 -A5 'Activity' | grep -E 'Activity|exported|permission'")
        val activities = shell.run("pm dump $pkg | grep -E '^\\s+[a-z].*Activity' | head -40")
        return ok(request, mapOf(
            "package" to pkg,
            "activities" to activities.stdout.trim(),
            "activity_details" to result.stdout.trim().take(4096),
        ))
    }

    /** app.activity.start — launch an activity with a fully-specified intent. */
    fun start(request: CommandRequest): CommandResponse {
        val component = request.params["component"] // format: "package/activity"
        val pkg = request.params["package"]
        val activity = request.params["activity"]
        val action = request.params["action"]
        val category = request.params["category"]
        val dataUri = request.params["data_uri"]
        val mimeType = request.params["mime_type"]
        val extras = request.params["extras"] // format: "type:key:value,type:key:value"
        val flags = request.params["flags"]

        val cmd = buildString {
            append("am start")
            if (action != null) append(" -a $action")
            if (category != null) {
                for (cat in category.split(",")) {
                    append(" -c ${cat.trim()}")
                }
            }
            if (component != null) {
                append(" -n $component")
            } else if (pkg != null && activity != null) {
                append(" -n $pkg/$activity")
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

        if (!cmd.contains("-n ") && action == null && dataUri == null) {
            return CommandResponse(id = request.id, status = "error", error = "must specify component, action, or data_uri")
        }

        val result = shell.run(cmd)
        return ok(request, mapOf(
            "command" to cmd,
            "stdout" to result.stdout.trim(),
            "stderr" to result.stderr.trim(),
            "exit_code" to result.exitCode.toString(),
        ))
    }

    /** Find browsable activities (scanner.activity.browsable equivalent). */
    fun browsable(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"]
        val cmd = if (pkg != null) {
            "dumpsys package $pkg | grep -B10 'android.intent.category.BROWSABLE' | grep -E 'scheme|host|Activity|path|BROWSABLE'"
        } else {
            "dumpsys package | grep -B10 'android.intent.category.BROWSABLE' | grep -E 'scheme|host|Activity|path'"
        }
        val result = shell.run(cmd)
        return ok(request, mapOf(
            "browsable_activities" to result.stdout.trim().take(8192),
            "note" to "Deep-link / browsable activity enumeration",
        ))
    }

    /** Enumerate intent filters for exported activities. */
    fun intentFilters(request: CommandRequest): CommandResponse {
        val pkg = request.params["package"] ?: return missing(request, "package")
        val result = shell.run("dumpsys package $pkg | grep -A20 'Activity Resolver Table' | head -60")
        return ok(request, mapOf("package" to pkg, "intent_filters" to result.stdout.trim()))
    }

    private fun ok(request: CommandRequest, data: Map<String, String>): CommandResponse =
        CommandResponse(id = request.id, status = "success", data = data)

    private fun missing(request: CommandRequest, parameter: String) =
        CommandResponse(id = request.id, status = "error", error = "missing parameter: $parameter")
}
