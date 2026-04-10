package com.mobsec.companion

import com.mobsec.companion.modules.ActivityInspector
import com.mobsec.companion.modules.AppManager
import com.mobsec.companion.modules.BroadcastInspector
import com.mobsec.companion.modules.ContentProviderInspector
import com.mobsec.companion.modules.DeviceInfo
import com.mobsec.companion.modules.ExploitRunner
import com.mobsec.companion.modules.FilesystemInspector
import com.mobsec.companion.modules.FridaGadgetInjector
import com.mobsec.companion.modules.LogCollector
import com.mobsec.companion.modules.PackageAnalyzer
import com.mobsec.companion.modules.ScreenshotCapture
import com.mobsec.companion.modules.ServiceInspector
import com.mobsec.companion.modules.TrafficCapture
import com.mobsec.companion.modules.VulnerabilityScanner
import com.mobsec.companion.protocol.CommandRequest
import com.mobsec.companion.protocol.CommandResponse

class CommandRouter(
    private val appManager: AppManager,
    private val fridaGadgetInjector: FridaGadgetInjector,
    private val trafficCapture: TrafficCapture,
    private val filesystemInspector: FilesystemInspector,
    private val logCollector: LogCollector,
    private val exploitRunner: ExploitRunner,
    private val screenshotCapture: ScreenshotCapture,
    private val packageAnalyzer: PackageAnalyzer,
    private val activityInspector: ActivityInspector,
    private val contentProviderInspector: ContentProviderInspector,
    private val broadcastInspector: BroadcastInspector,
    private val serviceInspector: ServiceInspector,
    private val deviceInfo: DeviceInfo,
    private val vulnerabilityScanner: VulnerabilityScanner,
) {
    fun handle(request: CommandRequest): CommandResponse {
        return when (request.command) {
            // ── Status ──────────────────────────────────────────────
            "get_status" -> CommandResponse(
                id = request.id,
                status = "success",
                data = mapOf("platform" to "android", "service" to "companion", "router" to "ktor-http", "version" to "2.0.0"),
            )

            // ── App Management (original) ───────────────────────────
            "install_target", "install_app" -> appManager.install(request)
            "uninstall_target", "uninstall_app" -> appManager.uninstall(request)
            "launch_app" -> appManager.launch(request)
            "list_packages" -> appManager.listPackages(request)

            // ── Drozer: app.package.* ───────────────────────────────
            "package_list" -> packageAnalyzer.listPackages(request)
            "package_info" -> packageAnalyzer.packageInfo(request)
            "package_attacksurface", "attack_surface" -> packageAnalyzer.attackSurface(request)
            "package_manifest", "dump_manifest" -> packageAnalyzer.manifest(request)
            "package_launchintent" -> packageAnalyzer.launchIntent(request)
            "package_native", "native_libs" -> packageAnalyzer.nativeLibraries(request)
            "package_shareduid" -> packageAnalyzer.sharedUid(request)
            "package_permissions", "app_permissions" -> packageAnalyzer.permissions(request)
            "package_backup", "backup_info" -> packageAnalyzer.backupInfo(request)

            // ── Drozer: app.activity.* ──────────────────────────────
            "activity_info" -> activityInspector.info(request)
            "activity_start", "start_activity" -> activityInspector.start(request)
            "activity_browsable", "find_deeplinks" -> activityInspector.browsable(request)
            "activity_intents" -> activityInspector.intentFilters(request)

            // ── Drozer: app.provider.* ──────────────────────────────
            "provider_info" -> contentProviderInspector.info(request)
            "provider_query", "query_provider" -> contentProviderInspector.query(request)
            "provider_insert" -> contentProviderInspector.insert(request)
            "provider_update" -> contentProviderInspector.update(request)
            "provider_delete" -> contentProviderInspector.delete(request)
            "provider_read" -> contentProviderInspector.readFile(request)
            "provider_finduris", "find_uris" -> contentProviderInspector.findUris(request)
            "provider_injection", "scan_injection" -> contentProviderInspector.injectionScan(request)
            "provider_traversal", "scan_traversal" -> contentProviderInspector.traversalScan(request)

            // ── Drozer: app.broadcast.* ─────────────────────────────
            "broadcast_info" -> broadcastInspector.info(request)
            "broadcast_send", "send_broadcast" -> broadcastInspector.send(request)
            "broadcast_find_exported" -> broadcastInspector.findExported(request)
            "broadcast_probe" -> broadcastInspector.probe(request)

            // ── Drozer: app.service.* ───────────────────────────────
            "service_info" -> serviceInspector.info(request)
            "service_start", "start_service" -> serviceInspector.start(request)
            "service_stop", "stop_service" -> serviceInspector.stop(request)
            "service_send" -> serviceInspector.send(request)
            "service_list_running" -> serviceInspector.listRunning(request)
            "service_find_exported" -> serviceInspector.findExported(request)

            // ── Device Info (Drozer: information.*) ─────────────────
            "device_info" -> deviceInfo.deviceInfo(request)
            "system_properties", "getprop" -> deviceInfo.systemProperties(request)
            "ca_certificates" -> deviceInfo.caCertificates(request)
            "root_check" -> deviceInfo.rootCheck(request)
            "network_info" -> deviceInfo.networkInfo(request)
            "storage_info" -> deviceInfo.storageInfo(request)
            "process_list", "ps" -> deviceInfo.processList(request)

            // ── Vulnerability Scanner (Drozer: scanner.*) ───────────
            "scan_debuggable" -> vulnerabilityScanner.debuggableApps(request)
            "scan_backup" -> vulnerabilityScanner.backupAllowed(request)
            "scan_full", "full_scan" -> vulnerabilityScanner.fullScan(request)
            "scan_world_writable" -> vulnerabilityScanner.worldWritable(request)
            "scan_world_readable" -> vulnerabilityScanner.worldReadable(request)
            "scan_network_security" -> vulnerabilityScanner.networkSecurityConfig(request)
            "scan_tapjack" -> vulnerabilityScanner.tapjackCheck(request)
            "scan_webview" -> vulnerabilityScanner.webviewCheck(request)
            "scan_signing" -> vulnerabilityScanner.signingInfo(request)

            // ── Frida / Hooking (original) ──────────────────────────
            "hook_runtime" -> fridaGadgetInjector.hookRuntime(request)
            "ssl_unpin" -> fridaGadgetInjector.sslUnpin(request)

            // ── Traffic / Proxy (original) ──────────────────────────
            "capture_traffic" -> trafficCapture.captureTraffic(request)
            "configure_proxy" -> trafficCapture.configureProxy(request)
            "clear_proxy" -> trafficCapture.clearProxy(request)

            // ── Filesystem (original) ───────────────────────────────
            "inspect_filesystem" -> filesystemInspector.inspect(request)
            "read_file" -> filesystemInspector.readFile(request)
            "get_app_data", "dump_app_data" -> filesystemInspector.getAppData(request)

            // ── Logs / Shell / Exploit (original) ───────────────────
            "collect_logs" -> logCollector.collect(request)
            "run_exploit", "run_shell" -> exploitRunner.run(request)
            "screenshot" -> screenshotCapture.capture(request)

            // ── Fallback ────────────────────────────────────────────
            else -> CommandResponse(id = request.id, status = "error", error = "unknown command: ${request.command}")
        }
    }

    companion object {
        fun default(): CommandRouter {
            val shell = ShellRunner()
            return CommandRouter(
                appManager = AppManager(shell),
                fridaGadgetInjector = FridaGadgetInjector(shell),
                trafficCapture = TrafficCapture(shell),
                filesystemInspector = FilesystemInspector(shell),
                logCollector = LogCollector(shell),
                exploitRunner = ExploitRunner(shell),
                screenshotCapture = ScreenshotCapture(shell),
                packageAnalyzer = PackageAnalyzer(shell),
                activityInspector = ActivityInspector(shell),
                contentProviderInspector = ContentProviderInspector(shell),
                broadcastInspector = BroadcastInspector(shell),
                serviceInspector = ServiceInspector(shell),
                deviceInfo = DeviceInfo(shell),
                vulnerabilityScanner = VulnerabilityScanner(shell),
            )
        }
    }
}