package com.mobsec.companion.protocol

import kotlinx.serialization.Serializable

@Serializable
data class CommandRequest(
    val id: String,
    val command: String,
    val params: Map<String, String> = emptyMap(),
)

@Serializable
data class CommandResponse(
    val id: String,
    val status: String,
    val data: Map<String, String> = emptyMap(),
    val error: String? = null,
)