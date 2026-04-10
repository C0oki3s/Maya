# iOS Companion App

This folder contains the iOS-side command scaffold for the Maya companion runtime.

Supported command names in the current scaffold:

- `get_status`
- `collect_logs`
- `inspect_filesystem`
- `dump_app_data`
- `dump_keychain`
- `launch_app`
- `configure_proxy`
- `clear_proxy`
- `screenshot`

Expected transport:

- WebSocket or HTTP listener on port `9999`
- JSON request/response structure aligned with the Android companion scaffold

The Swift file remains a scaffold rather than a deployable jailbreak service, but it now documents and models the expected command surface for Python-side integration.
