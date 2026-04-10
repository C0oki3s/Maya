# Android Companion App

On-device Android companion service for Maya. It exposes `/health`, `/commands`, and `/command` on port `9999` and dispatches requests through `CommandRouter` modules.

## Runtime

- Foreground Android service: `com.mobsec.companion.CompanionService`
- Embedded HTTP server (no Ktor/Netty runtime dependency)
- JSON protocol compatible with `maya/tools/device_bridge.py`

## Build APKs

**Requires:** [Docker Desktop](https://docs.docker.com/get-docker/) — no local Java, Android SDK, or Gradle needed.

```bash
# Linux / Mac (from repo root)
cd companion_app/android
./build_companion_apk.sh

# Windows PowerShell (from repo root)
cd companion_app\android
.\build_companion_apk.ps1
```

Direct Docker command (run from repo root):

```bash
DOCKER_BUILDKIT=1 docker build \
  -f containers/Dockerfile.apk-builder \
  --target apk-output \
  --output "type=local,dest=assets/android/apk" \
  .
```

Generated artifacts are copied to:

- `assets/android/apk/maya-companion-debug.apk`
- `assets/android/apk/maya-companion-release-unsigned.apk`

## Sign APKs

Default signing with uber-apk-signer (runs automatically as part of `build_companion_apk.sh/ps1`).

Optional custom keystore signing inside Docker:

```bash
cd companion_app/android
./gradlew.bat signReleaseApkWithUber
# Linux/Mac: ./gradlew signReleaseApkWithUber
```

Output:

- `assets/android/apk/maya-companion-release-signed-uber.apk`

Optional custom keystore signing:

```bash
# Linux / Mac
./build_companion_apk.sh --sign-mode keystore \
  --keystore /path/to/release.jks \
  --alias    maya_release \
  --store-pass YOUR_STORE_PASSWORD \
  --key-pass  YOUR_KEY_PASSWORD

# Windows PowerShell
.\build_companion_apk.ps1 -SignMode keystore `
  -KeystorePath C:\keys\release.jks `
  -KeyAlias maya_release `
  -StorePass YOUR_STORE_PASSWORD `
  -KeyPass YOUR_KEY_PASSWORD
```

Output:

- `assets/android/apk/maya-companion-release-signed-keystore.apk`

## Install and run

```bash
adb install -r assets/android/apk/maya-companion-release-signed-uber.apk
adb shell am start-foreground-service -n com.mobsec.companion/.CompanionService
adb forward tcp:9999 tcp:9999
curl http://127.0.0.1:9999/health
```

## Troubleshooting

- `docker: command not found`: install Docker Desktop.
- `Missing Dockerfile: .../Dockerfile.apk-builder`: restore `containers/Dockerfile.apk-builder` from repo.
- `Missing signer asset: .../uber-apk-signer-1.3.0.jar`: restore `assets/signer/uber-apk-signer-1.3.0.jar`.
- `ERROR: Missing --build-arg KEYSTORE_BASE64`: pass all required keystore args.
- `Keystore file not found`: fix `--keystore` / `-KeystorePath`.
- `adb: device not found`: connect/authorize a device and run `adb devices`.
