// TLS Version Verification — hooks SSLSocket, SSLEngine, SSLContext to check TLS versions
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {

  // 1. Hook SSLSocket.getSession to capture negotiated TLS version
  try {
    var SSLSocket = Java.use("javax.net.ssl.SSLSocket");
    SSLSocket.startHandshake.implementation = function () {
      this.startHandshake();
      var session = this.getSession();
      var protocol = session.getProtocol();
      var cipherSuite = session.getCipherSuite();
      var peerHost = this.getSession().getPeerHost();

      send({
        type: "tls_version",
        target: "SSLSocket",
        protocol: protocol,
        cipher_suite: cipherSuite,
        peer_host: peerHost,
        compliant: protocol === "TLSv1.3" || protocol === "TLSv1.2"
      });
    };
  } catch (e) {
    send({ type: "tls_version", target: "SSLSocket", error: e.toString() });
  }

  // 2. Hook SSLContext.getInstance to detect which TLS versions are requested
  try {
    var SSLContext = Java.use("javax.net.ssl.SSLContext");
    SSLContext.getInstance.overload("java.lang.String").implementation = function (protocol) {
      send({
        type: "tls_version",
        target: "SSLContext.getInstance",
        requested_protocol: protocol,
        compliant: protocol === "TLSv1.3" || protocol === "TLSv1.2" || protocol === "TLS"
      });
      return this.getInstance(protocol);
    };
  } catch (e) { /* overload not available */ }

  // 3. Hook SSLEngine to capture TLS version on engine-based connections
  try {
    var SSLEngine = Java.use("javax.net.ssl.SSLEngine");
    SSLEngine.setEnabledProtocols.implementation = function (protocols) {
      var protoList = [];
      for (var i = 0; i < protocols.length; i++) {
        protoList.push(protocols[i]);
      }

      var hasWeakProtocol = false;
      for (var j = 0; j < protoList.length; j++) {
        if (protoList[j] === "TLSv1" || protoList[j] === "TLSv1.1" || protoList[j] === "SSLv3") {
          hasWeakProtocol = true;
        }
      }

      send({
        type: "tls_version",
        target: "SSLEngine.setEnabledProtocols",
        enabled_protocols: protoList,
        has_weak_protocol: hasWeakProtocol,
        compliant: !hasWeakProtocol
      });
      return this.setEnabledProtocols(protocols);
    };
  } catch (e) { /* SSLEngine not used */ }

  // 4. Hook OkHttp ConnectionSpec for protocol enforcement
  try {
    var ConnectionSpec = Java.use("okhttp3.ConnectionSpec");
    var tlsVersions = ConnectionSpec.tlsVersions.value;
    if (tlsVersions) {
      var versions = [];
      for (var k = 0; k < tlsVersions.length; k++) {
        versions.push(tlsVersions[k].toString());
      }
      send({
        type: "tls_version",
        target: "OkHttp.ConnectionSpec",
        configured_tls_versions: versions
      });
    }
  } catch (e) { /* OkHttp not present */ }

  // 5. Hook HttpsURLConnection to check default SSL factory
  try {
    var HttpsURLConnection = Java.use("javax.net.ssl.HttpsURLConnection");
    HttpsURLConnection.connect.implementation = function () {
      this.connect();
      var cipherSuite = this.getCipherSuite();
      send({
        type: "tls_version",
        target: "HttpsURLConnection",
        cipher_suite: cipherSuite
      });
    };
  } catch (e) { /* not used */ }

  // 6. Detect cleartext / HTTP traffic (non-encrypted)
  try {
    var URL = Java.use("java.net.URL");
    URL.openConnection.overload().implementation = function () {
      var conn = this.openConnection();
      var urlStr = this.toString();
      if (urlStr.indexOf("http://") === 0) {
        send({
          type: "tls_version",
          target: "CleartextTraffic",
          url: urlStr,
          compliant: false,
          risk: "cleartext_http_detected"
        });
      }
      return conn;
    };
  } catch (e) { /* URL not hookable */ }

  send({ type: "tls_version_monitor", status: "all hooks installed" });
});
