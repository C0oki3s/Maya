# Companion App

Maya uses an on-device companion service to perform runtime operations that must execute directly on the target device — things like inspecting running apps, dumping keystores, capturing screenshots, and interacting with Android components or iOS system APIs.

---

## Overview

| | Android | iOS |
|---|---------|-----|
| **Language** | Kotlin | Swift |
| **Framework** | Android foreground service + embedded HTTP server | Native Foundation |
| **Port** | `9999` | `9999` |
| **Protocol** | JSON over HTTP | JSON over HTTP/WebSocket |
| **Status** | Functional (16+ modules) | Scaffold (9 commands) |

The companion runs as a local HTTP server on the device. Maya's `device_bridge` tools communicate with it over ADB port forwarding (`adb forward tcp:9999 tcp:9999`), so the agent in Docker sends HTTP requests to `localhost:9999` which routes through to the device.

---

## Android Companion

### Architecture

```
Maya Agent (Docker sandbox)
  │
  ├─ HTTP request → localhost:9999 (forwarded via ADB)
  │
  └─► Android Device
       └─► CompanionService (APK foreground service)
            └─► Embedded HTTP server
                 └─► CommandRouter
                      ├── AppManager
                      ├── PackageAnalyzer
                      ├── ActivityInspector
                      ├── ContentProviderInspector
                      ├── BroadcastInspector
                      ├── ServiceInspector
                      ├── DeviceInfo
                      ├── VulnerabilityScanner
                      ├── FridaGadgetInjector
                      ├── TrafficCapture
                      ├── FilesystemInspector
                      ├── LogCollector
                      ├── ExploitRunner
                      └── ScreenshotCapture
```

### Modules

| Module | Commands | Description |
|--------|----------|-------------|
| **AppManager** | `list_apps`, `get_app_info`, `launch_app`, `force_stop` | Package management and app lifecycle |
| **PackageAnalyzer** | `analyze_manifest`, `list_permissions`, `list_components` | Static analysis of installed packages |
| **ActivityInspector** | `list_activities`, `start_activity`, `get_current_activity` | Activity enumeration and launching |
| **ContentProviderInspector** | `list_providers`, `query_provider`, `check_exported` | Content provider security testing |
| **BroadcastInspector** | `list_receivers`, `send_broadcast`, `monitor_intents` | Broadcast receiver testing |
| **ServiceInspector** | `list_services`, `start_service`, `bind_service` | Service enumeration and testing |
| **DeviceInfo** | `get_device_info`, `get_build_props`, `check_root` | Device metadata and root detection |
| **VulnerabilityScanner** | `scan_app`, `check_debuggable`, `check_backup` | Quick on-device vulnerability checks |
| **FridaGadgetInjector** | `inject_gadget`, `check_frida`, `start_frida_server` | Frida setup and gadget injection |
| **TrafficCapture** | `start_capture`, `stop_capture`, `get_capture` | Network traffic interception |
| **FilesystemInspector** | `list_files`, `read_file`, `check_permissions` | App sandbox filesystem inspection |
| **LogCollector** | `collect_logcat`, `filter_logs`, `clear_logs` | Logcat collection and filtering |
| **ExploitRunner** | `run_exploit`, `check_vuln`, `attempt_bypass` | Exploit execution primitives |
| **ScreenshotCapture** | `take_screenshot`, `record_screen` | Visual evidence capture |

### Request / Response Format

```json
// Request
{
  "id": "req-001",
  "command": "list_apps",
  "params": {
    "filter": "third_party"
  }
}

// Response
{
  "id": "req-001",
  "status": "ok",
  "data": {
    "apps": ["com.example.app", "com.target.bank"]
  }
}
```

### Deployment (APK-Only)

All Android companion artifacts are produced in `assets/android/apk/`.

**Prerequisites:** [Docker Desktop](https://docs.docker.com/get-docker/) — no local Java, Android SDK, or Gradle needed.

```bash
# From repo root — build + uber-sign inside Docker in one command
cd companion_app/android
./build_companion_apk.sh           # Linux / Mac
.\build_companion_apk.ps1          # Windows PowerShell
```

Direct Docker command (equivalent, run from repo root):

```bash
DOCKER_BUILDKIT=1 docker build \
  -f containers/Dockerfile.apk-builder \
  --target apk-output \
  --output "type=local,dest=assets/android/apk" \
  .
```

Output files written to `assets/android/apk/`:

- `maya-companion-debug.apk`
- `maya-companion-release-unsigned.apk`
- `maya-companion-release-signed-uber.apk`

Optional custom-keystore signing inside Docker:

```bash
# Linux / Mac
./build_companion_apk.sh --sign-mode keystore \
  --keystore /path/to/release.jks \
  --alias    maya_release \
  --store-pass "storePass" \
  --key-pass  "keyPass"

# Windows PowerShell
.\build_companion_apk.ps1 -SignMode keystore `
  -KeystorePath C:\keys\release.jks `
  -KeyAlias maya_release `
  -StorePass storePass `
  -KeyPass keyPass
```

Output: `assets/android/apk/maya-companion-release-signed-keystore.apk`

Install and start the companion service:

```bash
# Install signed APK
adb install -r assets/android/apk/maya-companion-release-signed-uber.apk

# Start foreground service
adb shell am start-foreground-service -n com.mobsec.companion/.CompanionService

# Forward companion port
adb forward tcp:9999 tcp:9999

# Verify health endpoint
curl http://127.0.0.1:9999/health
```

### Missing Dependency Errors (and fixes)

| Error | Meaning | Fix |
|---|---|---|
| `docker: command not found` | Docker is not installed | Install Docker Desktop from https://docs.docker.com/get-docker/ |
| `Missing Dockerfile: .../Dockerfile.apk-builder` | containers/Dockerfile.apk-builder is missing | Restore from repo |
| `Missing signer asset: .../uber-apk-signer-1.3.0.jar` | Signing asset is missing | Restore `assets/signer/uber-apk-signer-1.3.0.jar` |
| `ERROR: Missing --build-arg KEYSTORE_BASE64` | Keystore args not supplied for keystore mode | Pass all `--build-arg` / `-KeystorePath` etc. |
| `Keystore not found: ...` | Wrong keystore path | Correct the `--keystore` / `-KeystorePath` value |
| `adb: device not found` | No connected/authorized Android device | Connect device and run `adb devices` |


---

## iOS Companion

### Current Status

The iOS companion is a **scaffold** — it defines the command interface and returns guidance responses, but does not yet execute real operations. Full implementation is on the [roadmap](ROADMAP.md).

### Supported Commands

| Command | Description | Status |
|---------|-------------|--------|
| `get_status` | Check companion health | Scaffold |
| `collect_logs` | Collect device logs | Scaffold |
| `inspect_filesystem` | Browse app sandbox | Scaffold |
| `dump_app_data` | Export app data | Scaffold |
| `dump_keychain` | Dump iOS keychain entries | Scaffold |
| `launch_app` | Launch target app | Scaffold |
| `configure_proxy` | Configure network proxy | Scaffold |
| `clear_proxy` | Remove proxy settings | Scaffold |
| `screenshot` | Capture device screen | Scaffold |

### Architecture

The iOS companion is designed for **jailbroken devices** and communicates via the same JSON protocol as Android:

```swift
// CompanionServer.swift
enum CompanionCommand: String, Codable {
    case getStatus = "get_status"
    case collectLogs = "collect_logs"
    case inspectFilesystem = "inspect_filesystem"
    case dumpAppData = "dump_app_data"
    case dumpKeychain = "dump_keychain"
    // ...
}
```

### Future iOS Modules (Planned)

- Keychain dumper (using keychain-dumper or custom Objective-C bridge)
- Filesystem inspector (jailbreak helper reads app sandboxes)
- App data export (IPA extraction, plist dumping)
- NSURLSession traffic hooking
- Data protection class enumeration
- Entitlements extraction

---

## How Maya Uses the Companion

The `device_bridge` tool module in Maya communicates with the companion:

1. **Agent decides** to inspect an app's content providers (based on skills knowledge)
2. **Agent calls** `device_bridge` tool with the appropriate command
3. **Tool sends** HTTP request to `localhost:9999` (port-forwarded to device)
4. **Companion executes** the command on-device and returns JSON
5. **Agent observes** the result and plans the next step

The companion eliminates the need for complex ADB command chaining — operations that would require multiple shell commands are exposed as single HTTP endpoints.

---

## Drozer Equivalence

The Android companion replaces Drozer for most use cases:

| Drozer Command | Companion Equivalent |
|----------------|---------------------|
| `run app.package.list` | `list_apps` |
| `run app.package.info -a <pkg>` | `get_app_info {package: "<pkg>"}` |
| `run app.activity.info -a <pkg>` | `list_activities {package: "<pkg>"}` |
| `run app.provider.info -a <pkg>` | `list_providers {package: "<pkg>"}` |
| `run app.broadcast.info -a <pkg>` | `list_receivers {package: "<pkg>"}` |
| `run app.service.info -a <pkg>` | `list_services {package: "<pkg>"}` |
| `run scanner.provider.injection` | `query_provider {uri: "content://..."}` |
| `run scanner.activity.browsable` | `list_activities {filter: "browsable"}` |
