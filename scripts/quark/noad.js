// 夸克网盘 · 广告位清空
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 把广告接口的 data 换成空壳、code 保留。整包 REJECT 会让某些版本卡在 loading。
//
// 参数顺序: {blockAds, debugMode}

(function () {
  var KEYS = ["blockAds", "debugMode"];
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

  var DBG = on("debugMode", false);
  if (!on("blockAds", true)) { $done({}); return; }
  if (!$response || !$response.body) { $done({}); return; }

  var obj;
  try { obj = JSON.parse($response.body); } catch (e) { $done({}); return; }
  if (!obj || typeof obj !== "object") { $done({}); return; }

  var killed = [];
  ["data", "result", "ads", "list", "items", "banners", "splash"].forEach(function (k) {
    if (!Object.prototype.hasOwnProperty.call(obj, k)) return;
    var v = obj[k];
    if (Object.prototype.toString.call(v) === "[object Array]") { obj[k] = []; killed.push(k); }
    else if (v && typeof v === "object") { obj[k] = {}; killed.push(k); }
  });
  if (!killed.length) { $done({}); return; }
  if (DBG) $notification.post("Quark去广告", "清空 " + killed.join("/"),
    String(($request && $request.url) || "").substring(0, 80));
  $done({ body: JSON.stringify(obj) });
})();
