// Crypto Key Extraction — hooks Cipher, SecretKeySpec, Mac
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  // 1. Cipher operations
  var Cipher = Java.use("javax.crypto.Cipher");
  Cipher.init.overload("int", "java.security.Key").implementation = function (mode, key) {
    var algo = this.getAlgorithm();
    var keyBytes = key.getEncoded();
    send({
      type: "crypto_key",
      algorithm: algo,
      mode: mode === 1 ? "ENCRYPT" : "DECRYPT",
      key_hex: bytesToHex(keyBytes),
      key_length: keyBytes.length * 8
    });
    return this.init(mode, key);
  };

  // 2. SecretKeySpec creation
  var SecretKeySpec = Java.use("javax.crypto.spec.SecretKeySpec");
  SecretKeySpec.$init.overload("[B", "java.lang.String").implementation = function (key, algo) {
    send({
      type: "secret_key_created",
      algorithm: algo,
      key_hex: bytesToHex(key),
      key_length: key.length * 8
    });
    return this.$init(key, algo);
  };

  // 3. Mac operations (HMAC etc.)
  var Mac = Java.use("javax.crypto.Mac");
  Mac.init.overload("java.security.Key").implementation = function (key) {
    send({
      type: "mac_key",
      algorithm: this.getAlgorithm(),
      key_hex: bytesToHex(key.getEncoded())
    });
    return this.init(key);
  };

  function bytesToHex(bytes) {
    var hex = "";
    for (var i = 0; i < bytes.length; i++) {
      var b = (bytes[i] & 0xff).toString(16);
      hex += b.length === 1 ? "0" + b : b;
    }
    return hex;
  }

  send({ type: "crypto_keys_monitor", status: "all hooks installed" });
});
