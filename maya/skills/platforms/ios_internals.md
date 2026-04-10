---
name: ios_internals
description: iOS platform internals, entitlements, keychain, and container analysis guidance
category: platforms
version: "1.0"
last_updated: "2026-03-26"
applies_to: [static, dynamic, exploit]
platform: [ios]
---

# iOS Internals Skill

## App Container Layout

| Path | Contains | Security Risk |
|------|----------|---------------|
| `<AppHome>/Documents/` | User data, databases | Sensitive PII, credentials |
| `<AppHome>/Library/Preferences/` | NSUserDefaults plist files | Tokens, settings in plaintext |
| `<AppHome>/Library/Caches/` | URLCache, image cache | Cached API responses, tokens |
| `<AppHome>/tmp/` | Temporary files | May contain session data |
| `<AppHome>/Library/Application Support/` | Core Data stores | Full database access |

## Keychain

- iOS Keychain is the intended secure storage for credentials
- Check keychain access group scoping - shared groups allow cross-app access
- Dump keychain: `objection_run_command("ios keychain dump")`
- Look for: tokens, passwords, API keys stored with weak protection classes

### Data Protection Classes

| Class | When Accessible | Risk if Used |
|-------|----------------|--------------|
| `kSecAttrAccessibleAlways` | Always, even when locked | HIGH - data accessible on locked device |
| `kSecAttrAccessibleAfterFirstUnlock` | After first unlock | MEDIUM - persists across locks |
| `kSecAttrAccessibleWhenUnlocked` | Only when unlocked | LOW - recommended |
| `kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly` | Passcode set + unlocked | Strongest protection |

## Entitlements

- Check binary entitlements: `terminal_execute("ldid -e <binary_path>")`
- Or: `terminal_execute("codesign -d --entitlements - <app_path>")`
- Key entitlements to look for:
  - `com.apple.developer.associated-domains` -> Universal Links (deeplink hijacking)
  - `keychain-access-groups` -> shared keychain access
  - `aps-environment` -> push notification access
  - `com.apple.security.application-groups` -> shared container access

## App Transport Security (ATS)

- Check `Info.plist` for `NSAppTransportSecurity` key
- `NSAllowsArbitraryLoads: true` -> **HIGH**: All HTTP traffic allowed
- `NSExceptionDomains` with `NSExceptionAllowsInsecureHTTPLoads` -> per-domain bypass
- `NSAllowsLocalNetworking: true` -> local HTTP allowed (lower risk)

## URL Schemes

- Defined in `Info.plist` under `CFBundleURLTypes`
- Custom URL schemes can be hijacked by malicious apps
- Universal Links (associated domains) are more secure but still worth testing
- Test: `device_shell("uiopen 'customscheme://action?param=value'")`

## Binary Protections

- PIE (Position Independent Executable): required for App Store
- ARC (Automatic Reference Counting): prevents use-after-free class bugs
- Stack canaries: check with `otool -Iv <binary> | grep stack_chk`
- Encryption: App Store apps are encrypted, must decrypt before analysis