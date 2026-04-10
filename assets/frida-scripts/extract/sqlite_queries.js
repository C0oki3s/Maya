// SQLite Query Monitor — intercepts all database operations
// Usage: frida_run_script(package_name="<pkg>", script_code=<this file>)

Java.perform(function () {
  var SQLiteDatabase = Java.use("android.database.sqlite.SQLiteDatabase");

  SQLiteDatabase.rawQuery.overload("java.lang.String", "[Ljava.lang.String;").implementation = function (sql, args) {
    send({
      type: "sqlite_query",
      operation: "rawQuery",
      sql: sql,
      args: args ? args.toString() : null
    });
    return this.rawQuery(sql, args);
  };

  SQLiteDatabase.execSQL.overload("java.lang.String").implementation = function (sql) {
    send({ type: "sqlite_query", operation: "execSQL", sql: sql });
    return this.execSQL(sql);
  };

  SQLiteDatabase.insert.implementation = function (table, nullCol, values) {
    send({ type: "sqlite_query", operation: "insert", table: table, values: values ? values.toString() : null });
    return this.insert(table, nullCol, values);
  };

  send({ type: "sqlite_monitor", status: "hooks installed" });
});
