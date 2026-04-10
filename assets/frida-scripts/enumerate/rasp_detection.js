// RASP Detection & Code Protection Assessment
// Detects: obfuscation indicators, RASP libraries, anti-instrumentation, hooking detection
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {

  var raspIndicators = [];

  // 1. Detect known RASP / protection libraries by class enumeration
  var raspLibraries = {
    "com.guardsquare.dexguard": "DexGuard (GuardSquare)",
    "com.guardsquare.ixguard": "iXGuard (GuardSquare)",
    "proguard.": "ProGuard",
    "com.arxan": "Arxan/Digital.ai",
    "com.verimatrix": "Verimatrix",
    "com.promon": "Promon SHIELD",
    "com.licel.dexprotector": "DexProtector",
    "com.app.sealing": "AppSealing",
    "com.tencent.bugly": "Tencent Bugly (packer)",
    "com.secneo": "Bangcle/SecNeo",
    "com.baidu.protect": "Baidu Protector",
    "com.qihoo.util": "Qihoo 360 Protector",
    "com.pairip": "PairIP (Google Play Integrity)",
    "com.scottyab.rootbeer": "RootBeer (root detection)",
    "org.freerasp": "FreeRASP (Talsec)",
    "com.appdome": "Appdome",
    "com.zimperium": "Zimperium zIAP"
  };

  Java.enumerateLoadedClasses({
    onMatch: function (className) {
      for (var prefix in raspLibraries) {
        if (className.indexOf(prefix) === 0) {
          var indicator = {
            type: "rasp_detection",
            library: raspLibraries[prefix],
            class: className,
            status: "detected"
          };
          raspIndicators.push(indicator);
          send(indicator);
          break;
        }
      }
    },
    onComplete: function () {
      send({
        type: "rasp_detection",
        target: "class_enumeration",
        total_rasp_libraries_found: raspIndicators.length,
        status: "complete"
      });
    }
  });

  // 2. Detect Frida detection mechanisms
  var fridaDetectionMethods = [];

  // Check for common Frida detection: port scanning
  try {
    var ServerSocket = Java.use("java.net.ServerSocket");
    ServerSocket.$init.overload("int").implementation = function (port) {
      if (port === 27042 || port === 27043) {
        fridaDetectionMethods.push("port_scan_" + port);
        send({
          type: "rasp_detection",
          target: "frida_detection",
          method: "port_scanning",
          port: port
        });
      }
      return this.$init(port);
    };
  } catch (e) { /* not hookable */ }

  // 3. Detect anti-hooking: check for inline hook detection
  try {
    var Runtime = Java.use("java.lang.Runtime");
    var origExec = Runtime.exec.overload("[Ljava.lang.String;");
    origExec.implementation = function (cmdArray) {
      var cmd = cmdArray.join(" ");
      if (cmd.indexOf("frida") >= 0 || cmd.indexOf("xposed") >= 0 ||
          cmd.indexOf("substrate") >= 0 || cmd.indexOf("magisk") >= 0) {
        send({
          type: "rasp_detection",
          target: "anti_instrumentation",
          method: "process_check",
          command: cmd,
          status: "detected"
        });
      }
      return origExec.call(this, cmdArray);
    };
  } catch (e) { /* overload not found */ }

  // 4. Detect code obfuscation level by analyzing class/method naming
  var obfuscationScore = 0;
  var singleCharClasses = 0;
  var totalClasses = 0;

  Java.enumerateLoadedClasses({
    onMatch: function (className) {
      // Only check app classes (skip Android framework / java.*)
      if (className.indexOf("java.") === 0 || className.indexOf("android.") === 0 ||
          className.indexOf("androidx.") === 0 || className.indexOf("com.google.") === 0) {
        return;
      }
      totalClasses++;
      var parts = className.split(".");
      var simpleName = parts[parts.length - 1];
      if (simpleName.length <= 2) {
        singleCharClasses++;
      }
    },
    onComplete: function () {
      if (totalClasses > 0) {
        obfuscationScore = Math.round((singleCharClasses / totalClasses) * 100);
      }
      send({
        type: "rasp_detection",
        target: "obfuscation_analysis",
        total_app_classes: totalClasses,
        short_name_classes: singleCharClasses,
        obfuscation_percentage: obfuscationScore,
        obfuscation_level: obfuscationScore > 60 ? "high" :
                          obfuscationScore > 30 ? "medium" : "low"
      });
    }
  });

  // 5. Detect anti-debug at native level
  try {
    var fopen = Module.findExportByName(null, "fopen");
    if (fopen) {
      Interceptor.attach(fopen, {
        onEnter: function (args) {
          var path = args[0].readUtf8String();
          if (path && (path.indexOf("/proc/self/maps") >= 0 ||
                       path.indexOf("/proc/self/status") >= 0 ||
                       path.indexOf("/proc/self/task") >= 0)) {
            send({
              type: "rasp_detection",
              target: "anti_debug_native",
              method: "proc_inspection",
              path: path,
              status: "detected"
            });
          }
        },
        onLeave: function (retval) {}
      });
    }
  } catch (e) { /* native hooks not available */ }

  // 6. Detect string encryption (look for decryption methods being called frequently)
  try {
    var String = Java.use("java.lang.String");
    var decryptionCallCount = 0;
    String.$init.overload("[B", "java.lang.String").implementation = function (bytes, charset) {
      var result = this.$init(bytes, charset);
      decryptionCallCount++;
      if (decryptionCallCount % 100 === 0) {
        send({
          type: "rasp_detection",
          target: "string_encryption",
          decoded_count: decryptionCallCount,
          status: "possible_string_decryption"
        });
      }
      return result;
    };
  } catch (e) { /* not hookable */ }

  send({ type: "rasp_detection_complete", status: "all checks installed" });
});
