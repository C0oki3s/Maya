// Emulator Detection Bypass — spoofs Build props, TelephonyManager, sensors
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  // 1. Spoof Build properties to look like a real device
  var Build = Java.use("android.os.Build");
  Build.FINGERPRINT.value = "google/oriole/oriole:12/SP1A.210812.016.C1/7955498:user/release-keys";
  Build.MODEL.value = "Pixel 6";
  Build.MANUFACTURER.value = "Google";
  Build.BRAND.value = "google";
  Build.DEVICE.value = "oriole";
  Build.PRODUCT.value = "oriole";
  Build.HARDWARE.value = "oriole";
  send({ type: "bypass", target: "Build.properties", status: "spoofed" });

  // 2. Spoof TelephonyManager
  try {
    var TelMgr = Java.use("android.telephony.TelephonyManager");
    TelMgr.getDeviceId.overload().implementation = function () {
      return "358240051111110";
    };
    TelMgr.getSubscriberId.overload().implementation = function () {
      return "310260000000000";
    };
    send({ type: "bypass", target: "TelephonyManager", status: "spoofed" });
  } catch (e) { /* method not available */ }

  // 3. Block common emulator detection checks
  try {
    var SystemProperties = Java.use("android.os.SystemProperties");
    var origGet = SystemProperties.get.overload("java.lang.String", "java.lang.String");
    origGet.implementation = function (key, def) {
      if (key === "ro.hardware.chipname" || key === "ro.kernel.qemu") {
        return def || "";
      }
      return origGet.call(this, key, def);
    };
  } catch (e) { /* SystemProperties not accessible */ }

  send({ type: "emulator_detection_bypassed", status: "all hooks installed" });
});
