// Universal Root Detection Bypass
// Covers: File.exists, Runtime.exec, Build.TAGS, RootBeer
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  var rootPaths = [
    "/system/app/Superuser.apk", "/sbin/su", "/system/bin/su",
    "/system/xbin/su", "/data/local/xbin/su", "/data/local/bin/su",
    "/system/sd/xbin/su", "/system/bin/failsafe/su", "/data/local/su",
    "/su/bin/su", "/data/adb/magisk", "/sbin/magisk"
  ];

  // 1. Hook File.exists to hide root indicators
  var File = Java.use("java.io.File");
  File.exists.implementation = function () {
    var path = this.getAbsolutePath();
    for (var i = 0; i < rootPaths.length; i++) {
      if (path === rootPaths[i]) {
        send({ type: "bypass", target: "File.exists", path: path });
        return false;
      }
    }
    return this.exists();
  };

  // 2. Hook Runtime.exec to block su/which checks
  var Runtime = Java.use("java.lang.Runtime");
  Runtime.exec.overload("java.lang.String").implementation = function (cmd) {
    if (cmd.indexOf("su") >= 0 || cmd.indexOf("which") >= 0) {
      send({ type: "bypass", target: "Runtime.exec", cmd: cmd });
      throw Java.use("java.io.IOException").$new("blocked");
    }
    return this.exec(cmd);
  };

  // 3. Spoof Build.TAGS
  var Build = Java.use("android.os.Build");
  Build.TAGS.value = "release-keys";
  send({ type: "bypass", target: "Build.TAGS", status: "spoofed" });

  // 4. RootBeer bypass (if present)
  try {
    var RootBeer = Java.use("com.scottyab.rootbeer.RootBeer");
    RootBeer.isRooted.implementation = function () { return false; };
    RootBeer.isRootedWithoutBusyBoxCheck.implementation = function () { return false; };
    send({ type: "bypass", target: "RootBeer", status: "bypassed" });
  } catch (e) { /* RootBeer not present */ }

  send({ type: "root_detection_bypassed", status: "all hooks installed" });
});
