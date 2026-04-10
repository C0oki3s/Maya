---
name: encryption_compliance
description: Encryption at rest/transit verification - AES-256, TLS 1.3, cert pinning, data isolation
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [frida_operations, frida_scripts, ssl_pinning_bypass, insecure_crypto]
applies_to: [dynamic, bypass, static]
platform: [android]
---

# Encryption Compliance Testing Skill

Verifies that the app meets encryption requirements: AES-256 at rest, TLS 1.3+ in transit, certificate pinning, and data containerization.

## Test Cases Covered

| # | Test Case | Script / Tool |
|---|-----------|---------------|
| 1 | Verify AES-256 encryption for data at rest and in transit | `crypto_keys.js` + static analysis |
| 2 | Confirm data is isolated using containerization methods | `data_containerization_check.js` |
| 3 | Verify all communications encrypted using TLS 1.3 or higher | `tls_version_check.js` + `caido_tool` |
| 4 | Validate certificate pinning to prevent MITM attacks | `ssl_pinning_universal.js` + `caido_tool` |

## Workflow

### Phase 1: Encryption at Rest - AES-256 Verification

1. **Static analysis** - find crypto usage in decompiled code:
```
terminal_execute("grep -rn 'AES\|Cipher\|SecretKeySpec\|KeyGenerator\|EncryptedSharedPreferences' /tmp/jadx_out/")
terminal_execute("grep -rn 'AES/CBC\|AES/GCM\|AES/ECB\|DES\|3DES\|Blowfish\|RC4' /tmp/jadx_out/")
```

2. **Runtime crypto key capture**:
```
file_read("~/.maya/frida-scripts/extract/crypto_keys.js")
frida_run_script(package_name="com.target", script=<content>)
```
Then exercise the app (login, load data, etc.) and observe captured keys.

3. **Evaluate findings**:
   - Are keys 256-bit (32 bytes)? -> AES-256 [OK]
   - Are keys 128-bit (16 bytes)? -> AES-128 (may not meet requirement)
   - Is DES/3DES/RC4/Blowfish used? -> Non-compliant
   - Is AES/ECB mode used? -> Weak (no IV, patterns leak)
   - Is AES/GCM or AES/CBC with HMAC used? -> Authenticated encryption [OK]

### Phase 2: Data Containerization Verification

1. **Run containerization check**:
```
file_read("~/.maya/frida-scripts/extract/data_containerization_check.js")
frida_run_script(package_name="com.target", script=<content>)
```

2. **Check for data leaks outside sandbox**:
```
device_shell("ls -la /sdcard/ | grep -i <app_related_names>")
device_shell("find /sdcard/ -newer /data/data/<package_name> -type f 2>/dev/null")
```

3. **Verify SharedPreferences mode** - script reports MODE_WORLD_READABLE/WRITABLE.

4. **Check for EncryptedSharedPreferences** - script detects whether AndroidX Security library is used.

5. **Verify KeyStore usage** - script tracks if AndroidKeyStore is used for secret storage.

### Phase 3: TLS Version Verification

1. **Run TLS version monitor**:
```
file_read("~/.maya/frida-scripts/extract/tls_version_check.js")
frida_run_script(package_name="com.target", script=<content>)
```
Then exercise the app to trigger network calls.

2. **Check network security config** in AndroidManifest:
```
terminal_execute("grep -rn 'cleartextTrafficPermitted\|network_security_config\|usesCleartextTraffic' /tmp/jadx_out/")
terminal_execute("cat /tmp/jadx_out/res/xml/network_security_config.xml 2>/dev/null")
```

3. **Verify with proxy**:
```
caido_start()
caido_set_scope_from_mobile_traffic()
```
Check captured traffic for TLS versions in handshake data.

4. **Evaluate**:
   - TLSv1.3 or TLSv1.2 only -> Compliant [OK]
   - TLSv1.0 or TLSv1.1 enabled -> Non-compliant
   - SSLv3 enabled -> Critical non-compliance
   - Cleartext HTTP detected -> Critical non-compliance

### Phase 4: Certificate Pinning Validation

1. **Attempt SSL pinning bypass**:
```
file_read("~/.maya/frida-scripts/bypass/ssl_pinning_universal.js")
frida_run_script(package_name="com.target", script=<content>)
```

2. **Verify if bypass succeeds** - if traffic is interceptable via proxy after bypass:
   - Bypass succeeded -> Pinning is present but bypassable (report severity based on effort)
   - Bypass failed, no traffic visible -> Strong pinning implementation [OK]
   - No pinning at all, traffic visible without bypass -> No certificate pinning (High severity)

3. **Check pinning implementation in code**:
```
terminal_execute("grep -rn 'CertificatePinner\|TrustManager\|X509TrustManager\|checkServerTrusted\|network_security_config' /tmp/jadx_out/")
```

4. **For Flutter apps**, use the Flutter-specific bypass:
```
file_read("~/.maya/frida-scripts/bypass/ssl_pinning_flutter.js")
frida_run_script(package_name="com.target", script=<content>)
```

## Severity Guidance

| Finding | Severity | Condition |
|---------|----------|-----------|
| No encryption at rest | Critical | Sensitive data stored in plaintext SharedPreferences or SQLite |
| Weak encryption (DES, RC4, AES/ECB) | High | Non-AES-256 or insecure mode used for sensitive data |
| AES-128 instead of AES-256 | Medium | Key length does not meet 256-bit requirement |
| Data written outside sandbox | High | App writes sensitive data to external storage or world-readable locations |
| No EncryptedSharedPreferences | Medium | Plain SharedPreferences used for secrets (tokens, keys) |
| TLS 1.0/1.1 enabled | High | Weak TLS versions accepted by client |
| Cleartext HTTP traffic | Critical | Unencrypted communications detected |
| No certificate pinning | High | Traffic interceptable without any bypass |
| Certificate pinning easily bypassed | Medium | Standard Frida script bypasses pinning |
| Strong certificate pinning | Informational | Resilience note - pinning resists bypass |

## Remediation Guidance

- Use AES-256-GCM for data at rest; use AndroidKeyStore for key storage.
- Use EncryptedSharedPreferences for all sensitive preference data.
- Never write sensitive data to external storage or world-readable locations.
- Set `android:usesCleartextTraffic="false"` in AndroidManifest.xml.
- Configure network_security_config.xml to enforce TLS 1.3 minimum.
- Implement certificate pinning via OkHttp CertificatePinner or network_security_config.
- Use public key pinning (not certificate pinning) for easier rotation.
- Implement pinning failure reporting to detect MITM attempts.
