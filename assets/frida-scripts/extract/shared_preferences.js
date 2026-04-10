// SharedPreferences Monitor — logs all read/write operations
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  var SharedPrefsImpl = Java.use("android.app.SharedPreferencesImpl");

  // Monitor getString
  SharedPrefsImpl.getString.implementation = function (key, defVal) {
    var val = this.getString(key, defVal);
    send({ type: "shared_prefs_read", key: key, value: val, default: defVal });
    return val;
  };

  // Monitor getInt
  SharedPrefsImpl.getInt.implementation = function (key, defVal) {
    var val = this.getInt(key, defVal);
    send({ type: "shared_prefs_read", key: key, value: val, default: defVal });
    return val;
  };

  // Monitor getBoolean
  SharedPrefsImpl.getBoolean.implementation = function (key, defVal) {
    var val = this.getBoolean(key, defVal);
    send({ type: "shared_prefs_read", key: key, value: val, default: defVal });
    return val;
  };

  // Monitor Editor.putString
  var Editor = Java.use("android.app.SharedPreferencesImpl$EditorImpl");
  Editor.putString.implementation = function (key, val) {
    send({ type: "shared_prefs_write", key: key, value: val });
    return this.putString(key, val);
  };

  send({ type: "shared_prefs_monitor", status: "all hooks installed" });
});
