// Network Request Monitor — hooks OkHttp and URLConnection
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  // 1. OkHttp3 interceptor
  try {
    var OkHttpClient = Java.use("okhttp3.OkHttpClient");
    var Request = Java.use("okhttp3.Request");
    var RealCall = Java.use("okhttp3.internal.connection.RealCall");

    RealCall.execute.implementation = function () {
      var req = this.request();
      send({
        type: "http_request",
        library: "OkHttp3",
        method: req.method(),
        url: req.url().toString()
      });
      return this.execute();
    };
  } catch (e) { /* OkHttp not present */ }

  // 2. HttpURLConnection
  try {
    var URL = Java.use("java.net.URL");
    URL.openConnection.overload().implementation = function () {
      send({
        type: "http_request",
        library: "URLConnection",
        url: this.toString()
      });
      return this.openConnection();
    };
  } catch (e) { /* fallback */ }

  send({ type: "network_monitor", status: "hooks installed" });
});
