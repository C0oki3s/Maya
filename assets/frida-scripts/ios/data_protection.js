// iOS Data Protection Class Monitor
// Monitors file operations to check NSFileProtection levels
// Usage: frida_run_script(package_name="<bundle_id>", script_code=<this file>)

if (ObjC.available) {
  var NSFileManager = ObjC.classes.NSFileManager;

  Interceptor.attach(
    NSFileManager["- createFileAtPath:contents:attributes:"].implementation,
    {
      onEnter: function (args) {
        var path = ObjC.Object(args[2]).toString();
        var attrs = args[4] ? ObjC.Object(args[4]) : null;
        var protection = "none";
        if (attrs) {
          var protAttr = attrs.objectForKey_("NSFileProtectionKey");
          if (protAttr) protection = protAttr.toString();
        }
        send({
          type: "ios_file_created",
          path: path,
          protection: protection
        });
      }
    }
  );

  send({ type: "ios_data_protection_monitor", status: "hooks installed" });
} else {
  send({ type: "error", message: "ObjC runtime not available" });
}
