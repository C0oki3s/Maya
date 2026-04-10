// SSL Pinning Bypass for Flutter/Dart apps (BoringSSL)
// Usage: frida_run_script(package_name="<flutter_app>", script_code=<this file>)

var isPatched = false;

function patchBoringSSL() {
  var m = Process.findModuleByName("libflutter.so");
  if (!m) return false;

  // Search for ssl_verify_peer_cert pattern
  var patterns = [
    "FF 03 01 D1 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9",
    "2D E9 F0 4F 85 B0 04 46 90 F8",
  ];

  for (var i = 0; i < patterns.length; i++) {
    Memory.scan(m.base, m.size, patterns[i], {
      onMatch: function (address) {
        Interceptor.attach(address, {
          onLeave: function (retval) {
            retval.replace(0x0);
          }
        });
        send({ type: "bypass", target: "BoringSSL.ssl_verify_peer_cert", status: "patched_at_" + address });
        isPatched = true;
      },
      onComplete: function () {}
    });
    if (isPatched) break;
  }
  return isPatched;
}

setTimeout(function () {
  if (!patchBoringSSL()) {
    send({ type: "warning", message: "Could not find BoringSSL pattern in libflutter.so — try updating patterns for this Flutter version" });
  }
}, 1000);
