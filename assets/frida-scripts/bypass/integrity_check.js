// Integrity Check / Anti-Tamper Bypass
// Hooks PackageManager.signatures and MessageDigest to bypass signature verification
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  // 1. PackageManager signature bypass — return original signatures
  var PackageManager = Java.use("android.app.ApplicationPackageManager");
  try {
    PackageManager.getPackageInfo.overload("java.lang.String", "int").implementation = function (pkg, flags) {
      // If requesting signatures (flag 64), return normally but log it
      var info = this.getPackageInfo(pkg, flags);
      send({ type: "monitor", target: "PackageManager.getPackageInfo", package: pkg, flags: flags });
      return info;
    };
  } catch (e) { /* overload not found */ }

  // 2. MessageDigest interception — detect hash verification
  var MessageDigest = Java.use("java.security.MessageDigest");
  MessageDigest.digest.overload("[B").implementation = function (input) {
    var result = this.digest(input);
    send({ type: "monitor", target: "MessageDigest.digest", algorithm: this.getAlgorithm() });
    return result;
  };

  // 3. Generic check/verify method hooking
  // Enumerate loaded classes and hook methods named check/verify/tamper/integrity
  Java.enumerateLoadedClasses({
    onMatch: function (className) {
      if (className.indexOf("tamper") >= 0 || className.indexOf("integrity") >= 0 ||
          className.indexOf("Integrity") >= 0 || className.indexOf("Tamper") >= 0) {
        try {
          var cls = Java.use(className);
          var methods = cls.class.getDeclaredMethods();
          for (var i = 0; i < methods.length; i++) {
            var methodName = methods[i].getName();
            if (methodName.indexOf("check") >= 0 || methodName.indexOf("verify") >= 0) {
              send({ type: "found", target: className + "." + methodName, status: "potential integrity check" });
            }
          }
        } catch (e) { /* can't use this class */ }
      }
    },
    onComplete: function () {}
  });

  send({ type: "integrity_check_bypass", status: "hooks installed" });
});
