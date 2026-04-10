package com.mobsec.companion

// Routing is now handled directly in Application.kt using a plain ServerSocket.
// This file is kept for reference only — the SUPPORTED_COMMANDS map is used
// by the old Ktor-based setup.  The new Application.kt routes directly.

/** All supported command names grouped by category for discoverability. */
val SUPPORTED_COMMANDS = mapOf(
    "status" to listOf("get_status"),
    "app_management" to listOf(
        "install_app", "uninstall_app", "launch_app", "list_packages",
    ),
    "package_analysis" to listOf(
        "package_list", "package_info", "package_attacksurface", "attack_surface",
        "package_manifest", "dump_manifest", "package_launchintent",
        "package_native", "native_libs", "package_shareduid",
        "package_permissions", "app_permissions", "package_backup", "backup_info",
    ),
    "activity" to listOf(
        "activity_info", "activity_start", "start_activity",
        "activity_browsable", "find_deeplinks", "activity_intents",
    ),
    "content_provider" to listOf(
        "provider_info", "provider_query", "query_provider",
        "provider_insert", "provider_update", "provider_delete",
        "provider_read", "provider_finduris", "find_uris",
        "provider_injection", "scan_injection",
        "provider_traversal", "scan_traversal",
    ),
    "broadcast" to listOf(
        "broadcast_info", "broadcast_send", "send_broadcast",
        "broadcast_find_exported", "broadcast_probe",
    ),
    "service" to listOf(
        "service_info", "service_start", "start_service",
        "service_stop", "stop_service", "service_send",
        "service_list_running", "service_find_exported",
    ),
    "device_info" to listOf(
        "device_info", "system_properties", "getprop",
        "ca_certificates", "root_check", "network_info",
        "storage_info", "process_list", "ps",
    ),
    "vulnerability_scanner" to listOf(
        "scan_debuggable", "scan_backup", "scan_full", "full_scan",
        "scan_world_writable", "scan_world_readable",
        "scan_network_security", "scan_tapjack",
        "scan_webview", "scan_signing",
    ),
    "frida" to listOf("hook_runtime", "ssl_unpin"),
    "traffic" to listOf("capture_traffic", "configure_proxy", "clear_proxy"),
    "filesystem" to listOf("inspect_filesystem", "read_file", "get_app_data", "dump_app_data"),
    "misc" to listOf("collect_logs", "run_shell", "run_exploit", "screenshot"),
)