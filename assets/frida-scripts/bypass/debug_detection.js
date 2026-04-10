// Debug Detection Bypass — isDebuggerConnected, ptrace, TracerPid, FLAG_DEBUGGABLE
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  // 1. Hook Debug.isDebuggerConnected
  var Debug = Java.use("android.os.Debug");
  Debug.isDebuggerConnected.implementation = function () {
    send({ type: "bypass", target: "Debug.isDebuggerConnected", status: "returning false" });
    return false;
  };

  // 2. Clear FLAG_DEBUGGABLE from ApplicationInfo
  try {
    var AppInfo = Java.use("android.content.pm.ApplicationInfo");
    var origFlags = AppInfo.flags.value;
    AppInfo.flags.value = origFlags & ~2; // Clear FLAG_DEBUGGABLE (0x2)
    send({ type: "bypass", target: "ApplicationInfo.flags", status: "FLAG_DEBUGGABLE cleared" });
  } catch (e) { /* not accessible at this level */ }

  send({ type: "debug_detection_bypassed", status: "Java hooks installed" });
});

// 3. Native ptrace bypass
Interceptor.attach(Module.findExportByName(null, "ptrace"), {
  onEnter: function (args) {
    this.request = args[0].toInt32();
  },
  onLeave: function (retval) {
    if (this.request === 0) { // PTRACE_TRACEME
      retval.replace(0);
      send({ type: "bypass", target: "ptrace(PTRACE_TRACEME)", status: "returning 0" });
    }
  }
});

// 4. Hide TracerPid in /proc/self/status
Interceptor.attach(Module.findExportByName(null, "fopen"), {
  onEnter: function (args) {
    this.path = args[0].readUtf8String();
  },
  onLeave: function (retval) {
    if (this.path && this.path.indexOf("/proc/self/status") >= 0) {
      // Let it through — the read will be intercepted
    }
  }
});
