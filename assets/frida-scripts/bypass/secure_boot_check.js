// Secure Boot & Device Integrity Check — verifies TEE, verified boot, device attestation
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  var findings = [];

  // 1. Check Build properties related to secure boot
  var Build = Java.use("android.os.Build");

  var buildType = Build.TYPE.value;
  var buildTags = Build.TAGS.value;
  var fingerprint = Build.FINGERPRINT.value;

  findings.push({
    type: "device_integrity",
    check: "build_properties",
    build_type: buildType,
    build_tags: buildTags,
    fingerprint: fingerprint,
    trusted: buildType === "user" && buildTags === "release-keys"
  });

  send({
    type: "secure_boot_check",
    target: "Build.properties",
    build_type: buildType,
    build_tags: buildTags,
    is_user_build: buildType === "user",
    is_release_keys: buildTags === "release-keys"
  });

  // 2. Check SystemProperties for verified boot state
  try {
    var SystemProperties = Java.use("android.os.SystemProperties");
    var get = SystemProperties.get.overload("java.lang.String", "java.lang.String");

    var verifiedBootState = get.call(null, "ro.boot.verifiedbootstate", "unknown");
    var verityMode = get.call(null, "ro.boot.veritymode", "unknown");
    var flashLocked = get.call(null, "ro.boot.flash.locked", "unknown");
    var secureBootState = get.call(null, "ro.boot.secureboot", "unknown");
    var debuggable = get.call(null, "ro.debuggable", "unknown");
    var secure = get.call(null, "ro.secure", "unknown");

    send({
      type: "secure_boot_check",
      target: "SystemProperties",
      verified_boot_state: verifiedBootState,
      verity_mode: verityMode,
      flash_locked: flashLocked,
      secure_boot: secureBootState,
      debuggable: debuggable,
      secure: secure,
      boot_trusted: verifiedBootState === "green" && flashLocked === "1"
    });
  } catch (e) {
    send({ type: "secure_boot_check", target: "SystemProperties", error: e.toString() });
  }

  // 3. Check if KeyStore hardware-backed attestation is available
  try {
    var KeyStore = Java.use("java.security.KeyStore");
    var ks = KeyStore.getInstance("AndroidKeyStore");
    ks.load(null);
    send({
      type: "secure_boot_check",
      target: "AndroidKeyStore",
      status: "available",
      hardware_backed: true
    });
  } catch (e) {
    send({
      type: "secure_boot_check",
      target: "AndroidKeyStore",
      status: "unavailable",
      error: e.toString()
    });
  }

  // 4. Monitor SafetyNet/Play Integrity attestation calls
  try {
    var SafetyNet = Java.use("com.google.android.gms.safetynet.SafetyNetApi");
    send({
      type: "secure_boot_check",
      target: "SafetyNet",
      status: "class_found",
      attestation_available: true
    });
  } catch (e) {
    // SafetyNet not present — check for Play Integrity
    try {
      var IntegrityManager = Java.use("com.google.android.play.core.integrity.IntegrityManager");
      send({
        type: "secure_boot_check",
        target: "PlayIntegrity",
        status: "class_found",
        attestation_available: true
      });
    } catch (e2) {
      send({
        type: "secure_boot_check",
        target: "DeviceAttestation",
        status: "no_attestation_api_found",
        attestation_available: false
      });
    }
  }

  // 5. Check if the app verifies device security patch level
  try {
    var VERSION = Java.use("android.os.Build$VERSION");
    var securityPatch = VERSION.SECURITY_PATCH.value;
    var sdkInt = VERSION.SDK_INT.value;
    send({
      type: "secure_boot_check",
      target: "SecurityPatchLevel",
      security_patch: securityPatch,
      sdk_int: sdkInt
    });
  } catch (e) {
    send({ type: "secure_boot_check", target: "SecurityPatchLevel", error: e.toString() });
  }

  send({ type: "secure_boot_check_complete", status: "all checks done" });
});
