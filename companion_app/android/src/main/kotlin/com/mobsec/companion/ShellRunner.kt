package com.mobsec.companion

import java.io.InputStreamReader
import java.util.concurrent.TimeUnit

data class ShellResult(val stdout: String, val stderr: String, val exitCode: Int)

class ShellRunner(
    /** Default command timeout in seconds. */
    private val defaultTimeoutSec: Long = 30,
    /** Maximum output size in chars to prevent OOM on huge outputs. */
    private val maxOutputChars: Int = 64 * 1024,
) {
    fun run(command: String, useRoot: Boolean = false, timeoutSec: Long? = null): ShellResult {
        return try {
            val timeout = timeoutSec ?: defaultTimeoutSec
            val shellCommand = if (useRoot) {
                arrayOf("sh", "-c", "su -c '$command'")
            } else {
                arrayOf("sh", "-c", command)
            }
            val process = Runtime.getRuntime().exec(shellCommand)

            // Read output with size limit — read char-by-char into StringBuilder
            val stdoutSb = StringBuilder()
            val stderrSb = StringBuilder()
            val stdoutReader = InputStreamReader(process.inputStream)
            val stderrReader = InputStreamReader(process.errorStream)

            val deadline = System.currentTimeMillis() + timeout * 1000
            val buf = CharArray(4096)

            // Non-blocking drain loop
            while (System.currentTimeMillis() < deadline) {
                var didRead = false
                if (stdoutReader.ready() && stdoutSb.length < maxOutputChars) {
                    val n = stdoutReader.read(buf)
                    if (n > 0) { stdoutSb.append(buf, 0, n); didRead = true }
                }
                if (stderrReader.ready() && stderrSb.length < maxOutputChars) {
                    val n = stderrReader.read(buf)
                    if (n > 0) { stderrSb.append(buf, 0, n); didRead = true }
                }
                if (!didRead) {
                    if (process.waitFor(200, TimeUnit.MILLISECONDS)) break
                }
            }

            // Final drain after process completes
            if (stdoutSb.length < maxOutputChars) {
                val rest = stdoutReader.readText()
                if (rest.length + stdoutSb.length <= maxOutputChars) stdoutSb.append(rest)
                else stdoutSb.append(rest.take(maxOutputChars - stdoutSb.length)).append("\n[truncated]")
            }

            val completed = process.waitFor(1, TimeUnit.SECONDS)
            if (!completed) {
                process.destroyForcibly()
                return ShellResult(stdout = stdoutSb.toString(), stderr = "timed out after ${timeout}s", exitCode = 124)
            }

            stdoutReader.close()
            stderrReader.close()

            ShellResult(
                stdout = stdoutSb.toString(),
                stderr = stderrSb.toString().take(maxOutputChars),
                exitCode = process.exitValue()
            )
        } catch (exc: Exception) {
            ShellResult(stdout = "", stderr = exc.message ?: "unknown shell error", exitCode = 1)
        }
    }
}