package com.mobsec.companion

import com.mobsec.companion.protocol.CommandRequest
import kotlinx.serialization.json.Json
import kotlinx.serialization.encodeToString
import java.io.BufferedReader
import java.io.Closeable
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Minimal HTTP server that works in Android's app_process runtime.
 * Avoids Ktor/Netty which require JVM features not available on-device.
 */
private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }
private val router = CommandRouter.default()
private const val COMPANION_SERVICE_NAME = "maya-companion-android"

object CompanionHttpServer : Closeable {
    private val running = AtomicBoolean(false)
    private var server: ServerSocket? = null
    private var acceptThread: Thread? = null
    private var executor: ExecutorService? = null

    fun isRunning(): Boolean = running.get()

    @Synchronized
    fun start(port: Int = defaultPort()): Result<Int> {
        if (running.get()) {
            return Result.success(server?.localPort ?: port)
        }

        return runCatching {
            val serverSocket = ServerSocket(port)
            val pool = Executors.newFixedThreadPool(4)
            server = serverSocket
            executor = pool
            running.set(true)

            acceptThread = Thread({
                while (running.get()) {
                    try {
                        val client = serverSocket.accept()
                        pool.submit { handleClient(client) }
                    } catch (e: Exception) {
                        if (running.get()) {
                            System.err.println("Accept error: ${e.message}")
                        }
                    }
                }
            }, "companion-http-accept")
            acceptThread?.isDaemon = true
            acceptThread?.start()

            println("MOBSEC Companion Server v2.0.0 listening on 0.0.0.0:$port")
            CompanionLog.add("Server started on port $port")
            port
        }
    }

    @Synchronized
    override fun close() {
        running.set(false)
        CompanionLog.add("Server stopped")
        try {
            server?.close()
        } catch (_: Exception) {
        }
        server = null
        acceptThread = null
        executor?.shutdownNow()
        executor = null
    }
}

fun defaultPort(): Int = System.getenv("COMPANION_PORT")?.toIntOrNull() ?: 9999

fun main() {
    val port = defaultPort()
    val result = CompanionHttpServer.start(port)
    if (result.isFailure) {
        val error = result.exceptionOrNull()
        System.err.println(
            "Failed to start companion server on port $port: ${error?.message ?: "unknown error"}",
        )
        return
    }

    while (true) {
        Thread.sleep(60_000)
    }
}

private fun handleClient(socket: Socket) {
    try {
        socket.soTimeout = 30_000
        val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
        val writer = PrintWriter(socket.getOutputStream(), false)

        // Read HTTP request line
        val requestLine = reader.readLine() ?: return
        val parts = requestLine.split(" ")
        if (parts.size < 2) return
        val method = parts[0]
        val path = parts[1]

        // Read headers
        val headers = mutableMapOf<String, String>()
        var contentLength = 0
        while (true) {
            val line = reader.readLine() ?: break
            if (line.isEmpty()) break
            val (key, value) = line.split(": ", limit = 2).let {
                if (it.size == 2) it[0].lowercase() to it[1] else it[0].lowercase() to ""
            }
            headers[key] = value
            if (key == "content-length") contentLength = value.trim().toIntOrNull() ?: 0
        }

        // Read body
        val body = if (contentLength > 0) {
            val buf = CharArray(contentLength)
            var read = 0
            while (read < contentLength) {
                val n = reader.read(buf, read, contentLength - read)
                if (n == -1) break
                read += n
            }
            String(buf, 0, read)
        } else ""

        // Route
        val (statusCode, responseBody) = route(method, path, body)

        CompanionLog.add("$method $path → $statusCode")
        // Send HTTP response
        writer.print("HTTP/1.1 $statusCode\r\n")
        writer.print("Content-Type: application/json\r\n")
        writer.print("Content-Length: ${responseBody.toByteArray().size}\r\n")
        writer.print("Connection: close\r\n")
        writer.print("\r\n")
        writer.print(responseBody)
        writer.flush()
    } catch (e: Exception) {
        System.err.println("Client error: ${e.message}")
    } finally {
        try { socket.close() } catch (_: Exception) {}
    }
}

private fun route(method: String, path: String, body: String): Pair<String, String> {
    return try {
        when {
            path == "/health" && method == "GET" -> {
                val data = mapOf("status" to "ok", "service" to COMPANION_SERVICE_NAME, "version" to "2.0.0")
                "200 OK" to json.encodeToString(data)
            }
            path == "/commands" && method == "GET" -> {
                val data = mapOf("status" to "ok", "info" to "Use POST /command with {id, command, params}")
                "200 OK" to json.encodeToString(data)
            }
            path == "/command" && method == "POST" -> {
                val request = json.decodeFromString<CommandRequest>(body)
                val response = router.handle(request)
                val status = if (response.status == "success") "200 OK" else "400 Bad Request"
                status to json.encodeToString(response)
            }
            else -> {
                val err = mapOf("error" to "not found", "path" to path)
                "404 Not Found" to json.encodeToString(err)
            }
        }
    } catch (e: Exception) {
        val err = mapOf("error" to (e.message ?: "internal error"))
        "500 Internal Server Error" to json.encodeToString(err)
    }
}