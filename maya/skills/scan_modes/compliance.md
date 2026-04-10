---
name: compliance
description: Security compliance scan - device integrity, encryption, RASP, and data isolation
category: scan_modes
applies_to: [root]
platform: [android]
---

# Compliance Scan Mode

## Goal

Automated verification of enterprise security compliance requirements: device integrity, runtime protections, encryption standards, and data isolation. Covers OWASP MASVS L2 and enterprise policy requirements.

## Test Matrix

| # | Test Case | Category | Automation |
|---|-----------|----------|------------|
| 1 | Verify secure boot enforcement on trusted devices | Device Integrity | `secure_boot_check.js` + `device_shell` |
| 2 | Detect and prevent virtualization/emulator execution | Emulator Detection | `emulator_detection.js` bypass test |
| 3 | Check code obfuscation, RASP, and anti-debugging | Code Protection | `rasp_detection.js` + `debug_detection.js` |
| 4 | Check for code tampering resistance | Code Protection | `integrity_check.js` |
| 5 | Enforce non-rooted/non-jailbroken device usage | Root Detection | `root_detection_universal.js` bypass test |
| 6 | Verify AES-256 encryption for data at rest and in transit | Encryption | `crypto_keys.js` + static analysis |
| 7 | Confirm data isolation using containerization | Data Isolation | `data_containerization_check.js` |
| 8 | Verify TLS 1.3 or higher for all communications | Transport Security | `tls_version_check.js` + `caido_tool` |
| 9 | Validate certificate pinning against MITM attacks | Transport Security | `ssl_pinning_universal.js` + `caido_tool` |

## Agent Allocation

Spawn 3 specialized sub-agents:

1. **Device Integrity Tester** - skills: `device_integrity_testing, bypass_techniques, frida_operations`
   - Tests: #1 (secure boot), #2 (emulator detection), #5 (root detection)
   - Approach: First test WITHOUT bypass to check if protections exist, then test WITH bypass to assess strength

2. **Code Protection Analyzer** - skills: `binary_protections, code_tampering, bypass_techniques, frida_operations`
   - Tests: #3 (obfuscation/RASP/anti-debug), #4 (code tampering)
   - Approach: Static analysis for protection detection + dynamic bypass attempts

3. **Encryption Compliance Tester** - skills: `encryption_compliance, ssl_pinning_bypass, insecure_crypto, frida_operations, caido_operations`
   - Tests: #6 (AES-256), #7 (data isolation), #8 (TLS 1.3), #9 (cert pinning)
   - Approach: Runtime crypto monitoring + traffic analysis + data storage audit

## Automation Flow

The `run_compliance_scan` tool orchestrates all 9 test cases:

```
run_compliance_scan(package_name="com.target", test_cases="all")
```

Or run specific categories:
```
run_compliance_scan(package_name="com.target", test_cases="device_integrity")
run_compliance_scan(package_name="com.target", test_cases="encryption")
run_compliance_scan(package_name="com.target", test_cases="code_protection")
```

## Exit Criteria

- All 9 test cases executed with pass/fail/partial status
- Each failing test has evidence (Frida output, traffic capture, screenshot)
- Compliance summary table generated with overall score
- Remediation priorities ordered by severity
- Report includes OWASP MASVS mapping for each finding

## Report Format

The final compliance report includes:

1. **Executive Summary** - Overall compliance score (X/9 passed)
2. **Device Integrity** - Secure boot, root detection, emulator detection results
3. **Code Protection** - RASP, obfuscation, anti-debug, anti-tamper assessment
4. **Encryption Standards** - AES-256 verification, key management audit
5. **Transport Security** - TLS version compliance, certificate pinning status
6. **Data Isolation** - Sandbox enforcement, storage permissions, containerization
7. **Remediation Roadmap** - Prioritized fixes by severity and implementation effort
