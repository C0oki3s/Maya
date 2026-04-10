---
name: app_reconnaissance
description: Pre-test intelligence gathering - framework detection heuristics and SDK fingerprinting
category: tools
version: "1.0"
last_updated: "2026-03-26"
applies_to: [static, recon]
---

# App Reconnaissance Guide

## Purpose

Before testing, gather intelligence to select the right tools and techniques. This avoids wasting iterations on techniques that don't apply.

## Step 1: Framework Detection

After decompiling, detect the framework with `terminal_execute` and `search_decompiled_code`. Knowing the framework changes everything:

| Framework | Key Implications |
|-----------|-----------------|
| **Flutter** | Uses `ssl_pinning_flutter` script, traffic won't show in standard proxy without bypass, Dart code in `libapp.so` |
| **React Native** | JavaScript bundle in `assets/`, check `index.android.bundle` for hardcoded secrets, use Hermes debugger |
| **Xamarin** | .NET assemblies in `assemblies/`, use dnSpy/ILSpy, different SSL stack |
| **Cordova/Ionic** | Web app in `assets/www/`, test like a web app + native bridge |
| **Unity** | Game engine, `libil2cpp.so` for IL2CPP builds, `Assembly-CSharp.dll` for Mono |
| **Native (Java/Kotlin)** | Standard Android testing approach |
| **KMP (Kotlin Multiplatform)** | Shared Kotlin code, platform-specific entry points |

## Step 2: SDK Fingerprinting

Search decompiled code for third-party SDK signatures using `search_decompiled_code` or `terminal_execute` with grep:

- **Analytics**: Firebase, Mixpanel, Amplitude - check for PII leakage
- **Payment**: Stripe, Braintree - check for insecure token handling
- **Auth**: Auth0, Firebase Auth, Okta - check for token storage
- **Ad Networks**: AdMob, Facebook Ads - check for tracking data exposure
- **Crash Reporting**: Crashlytics, Sentry - check for sensitive data in crash reports

## Step 3: Protection Detection

Detect security measures by searching for known protection library signatures in decompiled code and native binaries:

- **Obfuscation** (ProGuard/R8/DexGuard): Affects readability but not functionality
- **Root Detection**: Need bypass before dynamic testing
- **SSL Pinning**: Need bypass before traffic interception
- **Anti-Tamper**: May prevent repackaging - use runtime-only approaches
- **Certificate Transparency**: May log bypass attempts

## Decision Matrix

Based on recon results, choose your approach:

| Recon Result | Action |
|-------------|--------|
| Flutter + SSL pinning | Use `ssl_pinning_flutter` Frida module |
| Native + root detection + SSL pin | Compose `root_detection_universal + ssl_pinning_universal` |
| React Native | Check JS bundle for secrets FIRST, then dynamic test |
| Cordova | Inspect `assets/www/` for API keys, XSS in WebView |
| Heavy obfuscation | Use `deobfuscate_map` if mapping file available |
| No protections | Proceed directly to testing - app is likely less mature |
