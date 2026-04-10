// Data Containerization & Isolation Check — verifies app sandbox, data protection, isolation
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {

  // 1. Check file permissions on app data directory
  try {
    var Context = Java.use("android.app.ActivityThread").currentApplication().getApplicationContext();
    var appDataDir = Context.getDataDir().getAbsolutePath();
    var filesDir = Context.getFilesDir().getAbsolutePath();
    var cacheDir = Context.getCacheDir().getAbsolutePath();
    var externalFilesDir = null;
    try {
      externalFilesDir = Context.getExternalFilesDir(null).getAbsolutePath();
    } catch (e) { /* no external storage */ }

    send({
      type: "data_containerization",
      target: "app_directories",
      data_dir: appDataDir,
      files_dir: filesDir,
      cache_dir: cacheDir,
      external_files_dir: externalFilesDir,
      status: "enumerated"
    });
  } catch (e) {
    send({ type: "data_containerization", target: "app_directories", error: e.toString() });
  }

  // 2. Monitor file operations to detect data written outside sandbox
  try {
    var FileOutputStream = Java.use("java.io.FileOutputStream");
    FileOutputStream.$init.overload("java.io.File").implementation = function (file) {
      var path = file.getAbsolutePath();
      var isInsideSandbox = path.indexOf("/data/data/") === 0 ||
                            path.indexOf("/data/user/") === 0;
      var isExternalStorage = path.indexOf("/sdcard/") === 0 ||
                              path.indexOf("/storage/emulated/") === 0;

      if (!isInsideSandbox) {
        send({
          type: "data_containerization",
          target: "file_write_outside_sandbox",
          path: path,
          is_external: isExternalStorage,
          compliant: false,
          risk: isExternalStorage ? "data_on_external_storage" : "data_outside_sandbox"
        });
      }
      return this.$init(file);
    };
  } catch (e) { /* overload not available */ }

  // 3. Check SharedPreferences mode (world-readable/writable is insecure)
  try {
    var ContextWrapper = Java.use("android.content.ContextWrapper");
    ContextWrapper.getSharedPreferences.overload("java.lang.String", "int").implementation = function (name, mode) {
      var modeStr = "PRIVATE";
      if (mode === 1) modeStr = "MODE_WORLD_READABLE";
      if (mode === 2) modeStr = "MODE_WORLD_WRITABLE";
      if (mode === 4) modeStr = "MODE_MULTI_PROCESS";

      send({
        type: "data_containerization",
        target: "SharedPreferences",
        name: name,
        mode: modeStr,
        mode_int: mode,
        compliant: mode === 0
      });
      return this.getSharedPreferences(name, mode);
    };
  } catch (e) { /* not hookable */ }

  // 4. Check database file permissions
  try {
    var SQLiteOpenHelper = Java.use("android.database.sqlite.SQLiteOpenHelper");
    SQLiteOpenHelper.getWritableDatabase.overload().implementation = function () {
      var db = this.getWritableDatabase();
      var dbPath = db.getPath();
      send({
        type: "data_containerization",
        target: "SQLiteDatabase",
        path: dbPath,
        compliant: dbPath.indexOf("/data/data/") === 0 || dbPath.indexOf("/data/user/") === 0
      });
      return db;
    };
  } catch (e) { /* not hookable */ }

  // 5. Monitor ContentProvider access — check if data is exposed
  try {
    var ContentResolver = Java.use("android.content.ContentResolver");
    ContentResolver.query.overload(
      "android.net.Uri", "[Ljava.lang.String;", "java.lang.String",
      "[Ljava.lang.String;", "java.lang.String"
    ).implementation = function (uri, projection, selection, selectionArgs, sortOrder) {
      var uriStr = uri.toString();
      send({
        type: "data_containerization",
        target: "ContentProvider.query",
        uri: uriStr,
        status: "access_detected"
      });
      return this.query(uri, projection, selection, selectionArgs, sortOrder);
    };
  } catch (e) { /* overload not available */ }

  // 6. Check for EncryptedSharedPreferences usage (AndroidX Security)
  try {
    var EncryptedPrefs = Java.use("androidx.security.crypto.EncryptedSharedPreferences");
    send({
      type: "data_containerization",
      target: "EncryptedSharedPreferences",
      status: "class_found",
      compliant: true
    });
  } catch (e) {
    send({
      type: "data_containerization",
      target: "EncryptedSharedPreferences",
      status: "not_found",
      compliant: false,
      risk: "no_encrypted_preferences_library"
    });
  }

  // 7. Check for Android Keystore usage for secret storage
  try {
    var KeyStore = Java.use("java.security.KeyStore");
    KeyStore.getInstance.overload("java.lang.String").implementation = function (type) {
      send({
        type: "data_containerization",
        target: "KeyStore",
        keystore_type: type,
        hardware_backed: type === "AndroidKeyStore",
        compliant: type === "AndroidKeyStore"
      });
      return this.getInstance(type);
    };
  } catch (e) { /* not hookable */ }

  send({ type: "data_containerization_monitor", status: "all hooks installed" });
});
