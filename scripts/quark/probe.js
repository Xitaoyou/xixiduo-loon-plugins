// 夸克网盘 · 接口探测（排障用）
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 记「方法 + 域名 + path」进 quark_paths，第一次见到的路径发通知。
// 夸克改版本后主插件静默失效时，用它把插件里的正则补准。平时建议关闭。
//
// 参数顺序: {probe, debugMode}

(function () {
  var KEYS = ["probe", "debugMode"];
  var o = {};
  var arg = typeof $argument === "undefined" ? null : $argument;
  if (Array.isArray(arg)) {
    arg.forEach(function (v, i) { if (KEYS[i]) o[KEYS[i]] = v; });
  } else if (arg && typeof arg === "object") {
    o = arg;
  } else if (typeof arg === "string") {
    try {
      var p = JSON.parse(arg);
      if (Array.isArray(p)) p.forEach(function (v, i) { if (KEYS[i]) o[KEYS[i]] = v; });
      else if (p && typeof p === "object") o = p;
    } catch (e) {}
  }
  function on(k, d) {
    var v = k in o ? o[k] : $persistentStore.read("quark_" + k);
    if (v === null || v === undefined || v === "") return d;
    return v === true || v === 1 || String(v).toLowerCase() === "true" || String(v) === "1";
  }

  if (on("probe", true)) {
    try {
      var raw = String(($request && $request.url) || "");
      var u = raw.split("?")[0];
      var rest = u.replace(/^https?:\/\//, "");
      var host = rest.split("/")[0];
      var path = "/" + rest.split("/").slice(1).join("/");
      var key = (($request && $request.method) || "GET") + " " + host + path;
      var seen = {};
      try { seen = JSON.parse($persistentStore.read("quark_paths") || "{}"); } catch (e) { seen = {}; }
      if (!seen[key]) {
        seen[key] = Date.now();
        $persistentStore.write(JSON.stringify(seen), "quark_paths");
        $notification.post("Quark探测 · 新路径", key.substring(0, 70),
          "已记录 " + Object.keys(seen).length + " 条");
      }
    } catch (e) {}
  }
  $done({});
})();
