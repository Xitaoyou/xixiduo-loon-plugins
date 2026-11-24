// 夸克网盘 · 并发与限速字段改写
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 改的是「客户端允许开多少」，不是「CDN 允许跑多快」。后者在服务端签名里，改不动。
// 桌面版实测：同一条线 32 连接 47.7 MB/s，64 连接 1.7，128 连接 0。
//
// 参数顺序: {maxConn, clearLimit, debugMode}

(function () {
  var KEYS = ["maxConn", "clearLimit", "debugMode"];
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
  var LIMIT_ON = on("clearLimit", true);
  var CONC = parseInt(("maxConn" in o ? o.maxConn : $persistentStore.read("quark_maxConn")) || "32", 10);
  if (!(CONC > 0)) CONC = 32;
  if (CONC > 64) CONC = 64;

  var CONC_FIELDS = {};
  ["thread", "threads", "thread_num", "threadNum", "max_thread", "maxThread",
   "max_thread_num", "maxThreadNum", "download_thread", "downloadThread",
   "download_thread_num", "concurrent", "concurrency", "max_concurrent",
   "maxConcurrent", "max_conn", "maxConn", "max_connection", "maxConnection",
   "download_concurrency", "downloadConcurrency", "part_thread", "partThread",
   "slice_thread", "sliceThread", "parallel", "parallel_num", "parallelNum"
  ].forEach(function (k) { CONC_FIELDS[k] = 1; });

  var LIMIT_FIELDS = {};
  ["speed_limit", "speedLimit", "limit_speed", "limitSpeed", "max_speed", "maxSpeed",
   "down_speed_limit", "downSpeedLimit", "download_speed_limit", "downloadSpeedLimit",
   "rate_limit", "rateLimit", "throttle", "bandwidth_limit", "bandwidthLimit",
   "upload_speed_limit", "uploadSpeedLimit", "limit_rate", "limitRate",
   "free_speed_limit", "freeSpeedLimit"
  ].forEach(function (k) { LIMIT_FIELDS[k] = 1; });

  var LIMIT_SWITCH = {};
  ["is_limit", "isLimit", "limited", "throttled", "speed_limited", "speedLimited",
   "is_speed_limit", "isSpeedLimit", "need_limit", "needLimit",
   "rate_limited", "rateLimited"
  ].forEach(function (k) { LIMIT_SWITCH[k] = 1; });

  var bumped = 0, cleared = 0, opened = 0;
  function walk(n) {
    if (!n) return;
    var tag = Object.prototype.toString.call(n);
    if (tag === "[object Array]") { for (var i = 0; i < n.length; i++) walk(n[i]); return; }
    if (tag !== "[object Object]") return;
    for (var k in n) {
      if (!Object.prototype.hasOwnProperty.call(n, k)) continue;
      var v = n[k];
      if (v && typeof v === "object") { walk(v); continue; }
      // 只往上抬：服务端本来就给了更大的并发就别压回去
      if (CONC_FIELDS[k] === 1 && typeof v === "number" && v > 0 && v < CONC) { n[k] = CONC; bumped++; continue; }
      if (!LIMIT_ON) continue;
      if (LIMIT_FIELDS[k] === 1 && typeof v === "number" && v !== 0) { n[k] = 0; cleared++; continue; }
      if (LIMIT_SWITCH[k] === 1 && v !== false && v !== 0) { n[k] = false; opened++; continue; }
    }
  }

  if (!$response || !$response.body) { $done({}); return; }
  var obj;
  try { obj = JSON.parse($response.body); } catch (e) { $done({}); return; }
  walk(obj);
  if (!bumped && !cleared && !opened) { $done({}); return; }
  if (DBG) {
    $notification.post("Quark并发改写", "并发→" + CONC + " ×" + bumped + " · 限速清零 ×" + cleared + " · 开关 ×" + opened,
      String(($request && $request.url) || "").replace(/\?.*$/, "").substring(0, 90));
  }
  $done({ body: JSON.stringify(obj) });
})();
