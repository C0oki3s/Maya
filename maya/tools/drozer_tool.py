from __future__ import annotations

import os

import requests

from .registry import register_tool


def _companion_url() -> str:
    return os.environ.get("COMPANION_HTTP_URL", "http://127.0.0.1:9999/command")


def _send(command: str, params: dict, timeout_s: int = 30) -> dict:
    """Send a command to the companion app and return the response."""
    payload = {"id": f"drozer_{command}", "command": command, "params": {k: str(v) for k, v in params.items()}}
    try:
        r = requests.post(_companion_url(), json=payload, timeout=timeout_s)
        if r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return {"status": "ok", "raw": r.text}
    except Exception as exc:
        return {"error": str(exc)}


# ── app.package.* ────────────────────────────────────────────────────


@register_tool(sandbox_execution=True)
def drozer_package_list(filter: str = "", flags: str = "") -> dict:
    """List installed packages on device (drozer: app.package.list).

    Optionally filter by keyword or pass pm flags like '-3' for third-party.
    """
    return _send("package_list", {"filter": filter, "flags": flags})


@register_tool(sandbox_execution=True)
def drozer_package_info(package: str) -> dict:
    """Get detailed package info including APK path, UID, permissions (drozer: app.package.info)."""
    return _send("package_info", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_attack_surface(package: str) -> dict:
    """Enumerate exported activities, receivers, providers, services and debuggable status.

    Drozer module: app.package.attacksurface.
    """
    return _send("attack_surface", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_package_manifest(package: str) -> dict:
    """Dump the AndroidManifest.xml for a package (drozer: app.package.manifest)."""
    return _send("dump_manifest", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_package_permissions(package: str) -> dict:
    """List all permissions used, defined, and granted for a package."""
    return _send("app_permissions", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_native_libs(package: str) -> dict:
    """List native libraries bundled in a package (drozer: app.package.native)."""
    return _send("native_libs", {"package": package})


# ── app.activity.* ───────────────────────────────────────────────────


@register_tool(sandbox_execution=True)
def drozer_activity_info(package: str) -> dict:
    """List activities for a package with export and permission details (drozer: app.activity.info)."""
    return _send("activity_info", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_activity_start(
    package: str = "",
    activity: str = "",
    component: str = "",
    action: str = "",
    data_uri: str = "",
    extras: str = "",
    category: str = "",
    flags: str = "",
) -> dict:
    """Launch an activity with a constructed intent (drozer: app.activity.start).

    Use 'component' as 'pkg/activity' or provide package+activity.
    extras format: 'type:key:value,type:key:value'.
    """
    params = {
        k: v
        for k, v in {
            "package": package,
            "activity": activity,
            "component": component,
            "action": action,
            "data_uri": data_uri,
            "extras": extras,
            "category": category,
            "flags": flags,
        }.items()
        if v
    }
    return _send("activity_start", params)


@register_tool(sandbox_execution=True)
def drozer_find_deeplinks(package: str = "") -> dict:
    """Find browsable activities / deep-link handlers (drozer: scanner.activity.browsable)."""
    return _send("find_deeplinks", {"package": package} if package else {})


# ── app.provider.* ───────────────────────────────────────────────────


@register_tool(sandbox_execution=True)
def drozer_provider_info(package: str) -> dict:
    """List content providers with authorities, permissions, path-permissions (drozer: app.provider.info)."""
    return _send("provider_info", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_provider_query(uri: str, projection: str = "", selection: str = "", sort_order: str = "") -> dict:
    """Query a content:// URI (drozer: app.provider.query). Returns rows from the content provider."""
    params = {"uri": uri}
    if projection:
        params["projection"] = projection
    if selection:
        params["selection"] = selection
    if sort_order:
        params["sort_order"] = sort_order
    return _send("provider_query", params)


@register_tool(sandbox_execution=True)
def drozer_provider_insert(uri: str, bindings: str) -> dict:
    """Insert a row into a content provider (drozer: app.provider.insert). bindings format: 'type:column:value,...'"""
    return _send("provider_insert", {"uri": uri, "bindings": bindings})


@register_tool(sandbox_execution=True)
def drozer_provider_update(uri: str, bindings: str, selection: str = "") -> dict:
    """Update rows in a content provider (drozer: app.provider.update)."""
    params = {"uri": uri, "bindings": bindings}
    if selection:
        params["selection"] = selection
    return _send("provider_update", params)


@register_tool(sandbox_execution=True)
def drozer_provider_delete(uri: str, selection: str = "") -> dict:
    """Delete rows from a content provider (drozer: app.provider.delete)."""
    params = {"uri": uri}
    if selection:
        params["selection"] = selection
    return _send("provider_delete", params)


@register_tool(sandbox_execution=True)
def drozer_provider_read(uri: str) -> dict:
    """Read a file through a file-backed content provider (drozer: app.provider.read)."""
    return _send("provider_read", {"uri": uri})


@register_tool(sandbox_execution=True)
def drozer_find_uris(package: str) -> dict:
    """Brute-force accessible content:// URIs for a package (drozer: scanner.provider.finduris)."""
    return _send("find_uris", {"package": package}, timeout_s=120)


@register_tool(sandbox_execution=True)
def drozer_scan_injection(package: str) -> dict:
    """Test content providers for SQL injection in projection and selection (drozer: scanner.provider.injection)."""
    return _send("scan_injection", {"package": package}, timeout_s=120)


@register_tool(sandbox_execution=True)
def drozer_scan_traversal(package: str) -> dict:
    """Test file-backed content providers for path traversal (drozer: scanner.provider.traversal)."""
    return _send("scan_traversal", {"package": package}, timeout_s=120)


# ── app.broadcast.* ──────────────────────────────────────────────────


@register_tool(sandbox_execution=True)
def drozer_broadcast_info(package: str) -> dict:
    """List broadcast receivers with export and permission details (drozer: app.broadcast.info)."""
    return _send("broadcast_info", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_broadcast_send(
    action: str = "",
    component: str = "",
    package: str = "",
    receiver: str = "",
    extras: str = "",
    data_uri: str = "",
    category: str = "",
) -> dict:
    """Send a broadcast with a constructed intent (drozer: app.broadcast.send). extras format: 'type:key:value,...'"""
    params = {
        k: v
        for k, v in {
            "action": action,
            "component": component,
            "package": package,
            "receiver": receiver,
            "extras": extras,
            "data_uri": data_uri,
            "category": category,
        }.items()
        if v
    }
    return _send("broadcast_send", params)


# ── app.service.* ────────────────────────────────────────────────────


@register_tool(sandbox_execution=True)
def drozer_service_info(package: str) -> dict:
    """List services with export and permission details (drozer: app.service.info)."""
    return _send("service_info", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_service_start(
    package: str = "",
    service: str = "",
    component: str = "",
    action: str = "",
    extras: str = "",
) -> dict:
    """Start a service with a constructed intent (drozer: app.service.start)."""
    params = {
        k: v
        for k, v in {
            "package": package,
            "service": service,
            "component": component,
            "action": action,
            "extras": extras,
        }.items()
        if v
    }
    return _send("service_start", params)


@register_tool(sandbox_execution=True)
def drozer_service_stop(package: str = "", service: str = "", component: str = "") -> dict:
    """Stop a running service (drozer: app.service.stop)."""
    params = {k: v for k, v in {"package": package, "service": service, "component": component}.items() if v}
    return _send("service_stop", params)


# ── Device Info / scanner.* ──────────────────────────────────────────


@register_tool(sandbox_execution=True)
def drozer_device_info() -> dict:
    """Get comprehensive device information: model, OS version, SELinux, kernel, etc."""
    return _send("device_info", {})


@register_tool(sandbox_execution=True)
def drozer_root_check() -> dict:
    """Check device root status — su binary, Magisk, SuperSU, test-keys, etc."""
    return _send("root_check", {})


@register_tool(sandbox_execution=True)
def drozer_scan_full(package: str) -> dict:
    """Run a full vulnerability scan on a package.

    Checks debuggable, backup, permissions, exported components,
    world-readable files, cleartext, etc.
    """
    return _send("full_scan", {"package": package}, timeout_s=120)


@register_tool(sandbox_execution=True)
def drozer_scan_debuggable() -> dict:
    """Find all debuggable applications on the device."""
    return _send("scan_debuggable", {}, timeout_s=120)


@register_tool(sandbox_execution=True)
def drozer_scan_network_security(package: str) -> dict:
    """Check network security config and cleartext traffic policy for a package."""
    return _send("scan_network_security", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_scan_webview(package: str) -> dict:
    """Scan for exposed WebViews with JavaScript enabled in a package."""
    return _send("scan_webview", {"package": package})


@register_tool(sandbox_execution=True)
def drozer_signing_info(package: str) -> dict:
    """Get signing certificate details for a package."""
    return _send("scan_signing", {"package": package})
