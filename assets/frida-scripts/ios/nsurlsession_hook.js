// iOS NSURLSession Hook — capture HTTP requests/responses
// Usage: frida_run_script(package_name="<bundle_id>", script_code=<this file>)

if (ObjC.available) {
  var NSURLSession = ObjC.classes.NSURLSession;

  Interceptor.attach(
    ObjC.classes.NSURLSession["- dataTaskWithRequest:completionHandler:"].implementation,
    {
      onEnter: function (args) {
        var request = ObjC.Object(args[2]);
        send({
          type: "ios_http_request",
          url: request.URL().absoluteString().toString(),
          method: request.HTTPMethod().toString(),
          headers: request.allHTTPHeaderFields()
            ? request.allHTTPHeaderFields().toString()
            : "none"
        });
      }
    }
  );

  send({ type: "ios_nsurlsession_monitor", status: "hooks installed" });
} else {
  send({ type: "error", message: "ObjC runtime not available" });
}
