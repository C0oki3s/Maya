package com.mobsec.companion

import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Top-level facade for the MOBSEC Android Companion Server.
 *
 * Can be used programmatically (without HTTP) to dispatch commands
 * directly — useful for testing or embedding in an Android Service.
 */
object CompanionServer {
    private val router = CommandRouter.default()

    /** Dispatch a command and return the response synchronously. */
    fun handle(command: CommandRequest): CommandResponse {
        return router.handle(command)
    }

    /** Convenience: dispatch by command name and params map. */
    fun execute(id: String, command: String, params: Map<String, String> = emptyMap()): CommandResponse {
        return router.handle(CommandRequest(id = id, command = command, params = params))
    }
}
