package com.mobsec.companion.modules

import com.mobsec.companion.ShellRunner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

/**
 * Drozer-equivalent: information.* and device inspection.
 *
 * Retrieves device info, system properties, build details,
 * installed CA certs, SELinux status, and runtime info.
 */
class DeviceInfo(private val shell: ShellRunner) {

    /** Comprehensive device information. */
    fun deviceInfo(request: CommandRequest): CommandResponse {
        val build = shell.run("getprop ro.build.display.id")
        val sdk = shell.run("getprop ro.build.version.sdk")
        val release = shell.run("getprop ro.build.version.release")
        val model = shell.run("getprop ro.product.model")
        val manufacturer = shell.run("getprop ro.product.manufacturer")
        val device = shell.run("getprop ro.product.device")
        val board = shell.run("getprop ro.product.board")
        val abi = shell.run("getprop ro.product.cpu.abi")
        val serial = shell.run("getprop ro.serialno")
        val fingerprint = shell.run("getprop ro.build.fingerprint")
        val selinux = shell.run("getenforce 2>/dev/null || echo 'unknown'")
        val uptime = shell.run("uptime")
        val kernel = shell.run("uname -a")

        return ok(request, mapOf(
            "manufacturer" to manufacturer.stdout.trim(),
            "model" to model.stdout.trim(),
            "device" to device.stdout.trim(),
            "board" to board.stdout.trim(),
            "android_version" to release.stdout.trim(),
            "sdk_version" to sdk.stdout.trim(),
            "build_id" to build.stdout.trim(),
            "cpu_abi" to abi.stdout.trim(),
            "serial" to serial.stdout.trim(),
            "fingerprint" to fingerprint.stdout.trim(),
            "selinux" to selinux.stdout.trim(),
            "kernel" to kernel.stdout.trim(),
            "uptime" to uptime.stdout.trim(),
        ))
    }

    /** List all system properties (getprop). */
    fun systemProperties(request: CommandRequest): CommandResponse {
        val filter = request.params["filter"]
        val cmd = if (filter != null) "getprop | grep -i '$filter'" else "getprop"
        val result = shell.run(cmd)
        return ok(request, mapOf("properties" to result.stdout.trim().take(8192)))
    }

    /** List installed CA certificates (trust store). */
    fun caCertificates(request: CommandRequest): CommandResponse {
        val system = shell.run("ls /system/etc/security/cacerts/ 2>/dev/null | wc -l")
        val user = shell.run("ls /data/misc/user/0/cacerts-added/ 2>/dev/null | wc -l")
        val userCerts = shell.run("ls /data/misc/user/0/cacerts-added/ 2>/dev/null")
        return ok(request, mapOf(
            "system_cert_count" to system.stdout.trim(),
            "user_cert_count" to user.stdout.trim(),
            "user_certs" to userCerts.stdout.trim(),
        ))
    }

    /** Check root status and common root indicators. */
    fun rootCheck(request: CommandRequest): CommandResponse {
        val su = shell.run("which su 2>/dev/null")
        val magisk = shell.run("ls /data/adb/magisk 2>/dev/null && echo 'magisk_found'")
        val supersu = shell.run("ls /system/xbin/su 2>/dev/null && echo 'supersu_found'")
        val adbd = shell.run("getprop ro.debuggable")
        val testKeys = shell.run("getprop ro.build.tags | grep test-keys")
        val rwSystem = shell.run("mount | grep ' /system ' | grep 'rw'")
        return ok(request, mapOf(
            "su_binary" to su.stdout.trim(),
            "magisk" to magisk.stdout.trim(),
            "supersu" to supersu.stdout.trim(),
            "debuggable" to adbd.stdout.trim(),
            "test_keys" to testKeys.stdout.trim(),
            "system_rw" to rwSystem.stdout.trim(),
        ))
    }

    /** Network interfaces and connectivity info. */
    fun networkInfo(request: CommandRequest): CommandResponse {
        val ifconfig = shell.run("ifconfig 2>/dev/null || ip addr")
        val dns = shell.run("getprop net.dns1; getprop net.dns2")
        val proxy = shell.run("settings get global http_proxy")
        val wifi = shell.run("dumpsys wifi | grep 'mWifiInfo' | head -3")
        val iptables = shell.run("iptables -L -n 2>/dev/null | head -40")
        return ok(request, mapOf(
            "interfaces" to ifconfig.stdout.trim().take(4096),
            "dns" to dns.stdout.trim(),
            "proxy" to proxy.stdout.trim(),
            "wifi" to wifi.stdout.trim(),
            "iptables" to iptables.stdout.trim().take(2048),
        ))
    }

    /** Disk and storage info. */
    fun storageInfo(request: CommandRequest): CommandResponse {
        val df = shell.run("df -h 2>/dev/null || df")
        val mounts = shell.run("mount | head -30")
        return ok(request, mapOf(
            "disk_usage" to df.stdout.trim().take(4096),
            "mounts" to mounts.stdout.trim().take(4096),
        ))
    }

    /** Process listing. */
    fun processList(request: CommandRequest): CommandResponse {
        val filter = request.params["filter"]
        val cmd = if (filter != null) "ps -A | grep -i '$filter'" else "ps -A | head -80"
        val result = shell.run(cmd)
        return ok(request, mapOf("processes" to result.stdout.trim()))
    }

    private fun ok(request: CommandRequest, data: Map<String, String>): CommandResponse =
        CommandResponse(id = request.id, status = "success", data = data)
}
