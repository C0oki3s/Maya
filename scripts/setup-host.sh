#!/bin/bash
set -euo pipefail

echo "[*] Starting ADB server..."
adb start-server

echo "[*] Checking connected devices..."
adb devices -l

echo "[*] Setting up forwards..."
adb forward tcp:27042 tcp:27042 || true
adb forward tcp:9999 tcp:9999 || true
adb reverse tcp:8080 tcp:8080 || true

echo "[*] Attempting to start frida-server..."
adb shell "su -c '/data/local/tmp/frida-server -D &'" || true

echo "[*] Host setup complete."
