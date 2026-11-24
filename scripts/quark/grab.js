// 夸克网盘 · 直链抓取
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 不改响应，只把直链存进 persistentStore 并发通知。配了 webhook 就顺手 POST 出去。
// 抓到的直链受体积和签名限制：免登录 /file/share/download 超过约 50 MB 会 23018；
// 直链还绑同会话 Cookie，换个客户端直接 412。详见 docs/QuarkEnhance.md。
//
// 参数顺序: {grabLink, webhook, debugMode}

(function () {
  var KEYS = ["grabLink", "webhook", "debugMode"];
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
  function val(k, d) {
    var v = k in o ? o[k] : $persistentStore.read("quark_" + k);
    return (v === null || v === undefined || v === "") ? d : v;
  }
  function on(k, d) {
    var v = val(k, null);
    if (v === null) return d;
    return v === true || v === 1 || String(v).toLowerCase() === "true" || String(v) === "1";
  }

  var DBG = on("debugMode", false);
  if (!on("grabLink", true)) { $done({}); return; }

  var HOOK = String(val("webhook", "")).trim();
  var MAXKEEP = 40;

  var URL_FIELDS = {};
  ["download_url", "downloadUrl", "downloadURI", "play_url", "playUrl", "m3u8_url",
   "m3u8Url", "video_url", "videoUrl", "origin_url", "originUrl", "file_url", "fileUrl",
   "src", "url"
  ].forEach(function (k) { URL_FIELDS[k] = 1; });

  var found = [];
  function push(u) {
    if (typeof u !== "string" || u.length < 16) return;
    if (u.indexOf("http") !== 0) return;
    if (found.indexOf(u) >= 0) return;
    // 只留真正指向媒体/文件的，别把埋点上报的 url 也收进来
    if (!/quark\.cn|alicdn\.com|myqcloud\.com|aliyuncs\.com/.test(u) &&
        !/\.(mp4|m3u8|mkv|mov|webm|flv|pdf|zip|7z|rar)(\?|$)/i.test(u)) return;
    found.push(u);
  }

  function walk(n) {
    if (!n) return;
    var tag = Object.prototype.toString.call(n);
    if (tag === "[object Array]") { for (var i = 0; i < n.length; i++) walk(n[i]); return; }
    if (tag !== "[object Object]") return;
    for (var k in n) {
      if (!Object.prototype.hasOwnProperty.call(n, k)) continue;
      var v = n[k];
      if (v && typeof v === "object") { walk(v); continue; }
      if (URL_FIELDS[k] === 1 && typeof v === "string") push(v);
    }
  }

  if (!$response || !$response.body) { $done({}); return; }
  var obj;
  try { obj = JSON.parse($response.body); } catch (e) { $done({}); return; }
  walk(obj);
  if (!found.length) { $done({}); return; }

  var all = [];
  try { all = JSON.parse($persistentStore.read("quark_links") || "[]"); } catch (e) { all = []; }
  for (var i = 0; i < found.length; i++) all.unshift({ t: Date.now(), u: found[i] });
  var seen = {}, keep = [];
  for (var j = 0; j < all.length && keep.length < MAXKEEP; j++) {
    if (!all[j] || !all[j].u || seen[all[j].u]) continue;
    seen[all[j].u] = 1;
    keep.push(all[j]);
  }
  $persistentStore.write(JSON.stringify(keep), "quark_links");

  $notification.post("Quark直链", "抓到 " + found.length + " 条 · " +
    found[0].replace(/^https?:\/\//, "").split("/")[0],
    found[0].substring(0, 60) + "...（跑 dump.js 看全部）");

  if (HOOK.indexOf("http") === 0) {
    $httpClient.post({
      url: HOOK,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api: String(($request && $request.url) || "").replace(/\?.*$/, ""), links: found })
    }, function (err) {
      if (DBG) $notification.post("Quark直链", "webhook", err ? String(err) : "已推送");
    });
  }

  $done({});
})();
