---
name: adb_operations
description: Device bridge and ADB operational workflow for Android testing
category: tools
version: "1.0"
last_updated: "2026-03-26"
applies_to: [root, static, dynamic, api, exploit]
---

# ADB Operations Guide

## Prerequisites

### 1. Device Connection Check

Before any device operation:
1. `device_list` -> should show at least one connected device
2. If no device: check USB cable, enable USB debugging in Developer Options
3. Multiple devices: specify target with `device_id` parameter

### 2. Root Access Check

Many operations require root:
```
device_shell("su -c id")
```
-> Should show `uid=0(root)`. If not, root the device or use Magisk.

## Common Operations

### App Management

| Task | Command |
|------|---------|
| List installed packages | `device_shell("pm list packages -3")` |
| Get app info | `device_get_app_info(package_name="<pkg>")` |
| Get APK path | `device_shell("pm path <pkg>")` |
| Pull APK from device | `device_pull(remote="/data/app/<pkg>/base.apk", local="/tmp/target.apk")` |
| Install APK | `device_shell("pm install /tmp/modified.apk")` |
| Force stop app | `device_shell("am force-stop <pkg>")` |
| Clear app data | `device_shell("pm clear <pkg>")` |
| Launch app | `device_shell("monkey -p <pkg> -c android.intent.category.LAUNCHER 1")` |

### Filesystem Operations

| Task | Command |
|------|---------|
| List app files | `device_shell("su -c ls -la /data/data/<pkg>/")` |
| Read SharedPrefs | `device_shell("su -c cat /data/data/<pkg>/shared_prefs/<file>.xml")` |
| Pull database | `device_pull(remote="/data/data/<pkg>/databases/<db>", local="/tmp/<db>")` |
| Check file permissions | `device_shell("su -c ls -la /data/data/<pkg>/files/")` |
| Search for files | `device_shell("su -c find /data/data/<pkg>/ -name '*.db' -o -name '*.xml' -o -name '*.json'")` |

### Network & Proxy

| Task | Command |
|------|---------|
| Set HTTP proxy | `device_shell("settings put global http_proxy <host>:8080")` |
| Remove proxy | `device_shell("settings put global http_proxy :0")` |
| Check current proxy | `device_shell("settings get global http_proxy")` |
| Check Wi-Fi IP | `device_shell("ip addr show wlan0")` |

### Logging

| Task | Command |
|------|---------|
| Monitor app logs | `device_shell("logcat --pid=$(pidof <pkg>) -d -t 100")` |
| Search for crashes | `device_shell("logcat -d -t 200 | grep -i 'fatal\|crash\|exception'")` |
| Clear logcat buffer | `device_shell("logcat -c")` |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "device unauthorized" | Re-plug USB, tap "Allow" on device trust dialog |
| "no devices found" | Enable USB debugging, try `adb kill-server` then reconnect |
| Permission denied on /data/ | Need root: `su -c <command>` |
| App data empty after pull | App uses encryption or stores in non-standard location |