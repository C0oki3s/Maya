// SSL Pinning Universal Bypass — TrustManager + OkHttp + WebView
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  // 1. TrustManager bypass
  var TrustManager = Java.use("javax.net.ssl.X509TrustManager");
  var SSLContext = Java.use("javax.net.ssl.SSLContext");

  var EmptyTrustManager = Java.registerClass({
    name: "com.mobsec.EmptyTrustManager",
    implements: [TrustManager],
    methods: {
      checkClientTrusted: function (chain, authType) {},
      checkServerTrusted: function (chain, authType) {},
      getAcceptedIssuers: function () { return []; }
    }
  });

  var ctx = SSLContext.getInstance("TLS");
  ctx.init(null, [EmptyTrustManager.$new()], null);
  SSLContext.setDefault(ctx);
  send({ type: "bypass", target: "TrustManager", status: "bypassed" });

  // 2. OkHttp CertificatePinner bypass
  try {
    var CertPinner = Java.use("okhttp3.CertificatePinner");
    CertPinner.check.overload("java.lang.String", "java.util.List").implementation = function () {
      send({ type: "bypass", target: "OkHttp3.CertificatePinner", status: "bypassed" });
    };
  } catch (e) { /* OkHttp not present */ }

  // 3. WebView SSL error bypass
  try {
    var WebViewClient = Java.use("android.webkit.WebViewClient");
    WebViewClient.onReceivedSslError.implementation = function (view, handler, error) {
      handler.proceed();
      send({ type: "bypass", target: "WebView.onReceivedSslError", status: "bypassed" });
    };
  } catch (e) { /* WebView not used */ }

  send({ type: "ssl_pinning_bypassed", status: "all hooks installed" });
});
