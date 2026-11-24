// 夸克网盘 · 播放清晰度择优 + 门禁字段翻越 + 直链抓取
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 只在服务端已经下发的流里挑最高清排到第一位。没下发的清晰度脚本造不出来。
// 播放接口顺带把直链抽出来（Loon 同一条 URL 只会跑第一条命中的复写脚本，
// 所以抓链必须长在这个脚本里，不能另开一条抢同一个 URL）。
//
// 参数顺序: {maxQuality, openGate, grabLink, webhook, debugMode}

(function () {
  var KEYS = ["maxQuality", "openGate", "grabLink", "webhook", "debugMode"];
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
  var SORT_ON = on("maxQuality", true);
  var GATE_ON = on("openGate", true);
  var GRAB_ON = on("grabLink", true);
  var HOOK = String(val("webhook", "")).trim();

  var LISTS = {};
  ["video_list", "videoList", "play_list", "playList", "streams", "stream_list",
   "streamList", "quality_list", "qualityList", "qualities", "videos", "transcode_list"
  ].forEach(function (k) { LISTS[k] = 1; });

  var GATE_OFF = {};
  ["need_vip", "needVip", "vip_only", "vipOnly", "need_pay", "needPay", "pay_only",
   "payOnly", "need_buy", "needBuy", "is_charge", "isCharge", "need_member",
   "needMember", "vip_required", "vipRequired", "is_trial", "isTrial", "locked",
   "is_lock", "isLock", "need_purchase", "needPurchase"
  ].forEach(function (k) { GATE_OFF[k] = 1; });

  var GATE_ON_KEYS = {};
  ["can_play", "canPlay", "playable", "allow_play", "allowPlay", "is_play", "available"
  ].forEach(function (k) { GATE_ON_KEYS[k] = 1; });

  var URL_FIELDS = {};
  ["download_url", "downloadUrl", "downloadURI", "play_url", "playUrl", "m3u8_url",
   "m3u8Url", "video_url", "videoUrl", "origin_url", "originUrl", "file_url", "fileUrl",
   "src", "url"
  ].forEach(function (k) { URL_FIELDS[k] = 1; });

  var QMAP = { "4k": 2160, "2k": 1440, "1080p": 1080, "1080": 1080, "720p": 720,
               "720": 720, "540p": 540, "480p": 480, "360p": 360, "240p": 240,
               "原画": 4320, "超清": 1080, "高清": 720, "标清": 480, "流畅": 360 };

  // 高度优先、码率次之。高度拿不到就依次退到 quality 文案、resolution 的第二个数。
  function score(it) {
    if (!it || typeof it !== "object") return -1;
    var h = Number(it.height || it.v_height || it.vHeight || 0);
    if (!h && it.quality) {
      var q = String(it.quality).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "");
      for (var k in QMAP) if (q.indexOf(k) >= 0) { h = QMAP[k]; break; }
      if (!h) { var m = q.match(/(\d{3,4})/); if (m) h = Number(m[1]); }
    }
    if (!h && it.resolution) {
      var r = String(it.resolution).match(/(\d{3,4})\s*[xX*]\s*(\d{3,4})/);
      if (r) h = Number(r[2]);
    }
    var br = Number(it.bitrate || it.bit_rate || it.br || 0);
    return h * 100000 + br;
  }

  // 只留真正指向媒体/文件的，别把埋点上报的 url 也收进来
  function keepUrl(u) {
    if (typeof u !== "string" || u.length < 16) return false;
    if (u.indexOf("http") !== 0) return false;
    if (/quark\.cn|alicdn\.com|myqcloud\.com|aliyuncs\.com/.test(u)) return true;
    return /\.(mp4|m3u8|mkv|mov|webm|flv|ts)(\?|$)/i.test(u);
  }

  var sorted = 0, gates = 0, found = [];

  function push(u) {
    if (!keepUrl(u)) return;
    if (found.indexOf(u) >= 0) return;
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
      if (SORT_ON && LISTS[k] === 1 && Object.prototype.toString.call(v) === "[object Array]" && v.length > 1) {
        var before = v.map(score).join(",");
        v.sort(function (a, b) { return score(b) - score(a); });
        if (v.map(score).join(",") !== before) sorted++;
        for (var j = 0; j < v.length; j++) walk(v[j]);
        continue;
      }
      if (v && typeof v === "object") { walk(v); continue; }
      if (GRAB_ON && URL_FIELDS[k] === 1 && typeof v === "string") push(v);
      if (GATE_ON && GATE_OFF[k] === 1 && v !== false && v !== 0) { n[k] = false; gates++; continue; }
      if (GATE_ON && GATE_ON_KEYS[k] === 1 && v !== true && v !== 1) { n[k] = true; gates++; continue; }
    }
  }

  function saveLinks(list) {
    var all = [];
    try { all = JSON.parse($persistentStore.read("quark_links") || "[]"); } catch (e) { all = []; }
    for (var i = 0; i < list.length; i++) all.unshift({ t: Date.now(), u: list[i] });
    var seen = {}, keep = [];
    for (var j = 0; j < all.length && keep.length < 40; j++) {
      if (!all[j] || !all[j].u || seen[all[j].u]) continue;
      seen[all[j].u] = 1;
      keep.push(all[j]);
    }
    $persistentStore.write(JSON.stringify(keep), "quark_links");
    return keep;
  }

  if (!$response || !$response.body) { $done({}); return; }
  var obj;
  try { obj = JSON.parse($response.body); } catch (e) { $done({}); return; }
  walk(obj);

  if (GRAB_ON && found.length) {
    saveLinks(found);
    $notification.post("Quark直链", "抓到 " + found.length + " 条 · " +
      found[0].replace(/^https?:\/\//, "").split("/")[0],
      found[0].substring(0, 60) + "...");
    if (HOOK.indexOf("http") === 0) {
      $httpClient.post({
        url: HOOK,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api: String(($request && $request.url) || "").replace(/\?.*$/, ""), links: found })
      }, function (err) {
        if (DBG) $notification.post("Quark直链", "webhook", err ? String(err) : "已推送");
      });
    }
  }

  if (!sorted && !gates) {
    // 没改 body 就别回写，避免把原响应重新序列化后丢掉未知字段
    $done(found.length && GRAB_ON ? {} : {});
    return;
  }
  if (DBG) {
    $notification.post("Quark播放择优", "排序 " + sorted + " 组 · 门禁位 " + gates + " 个 · 直链 " + found.length,
      String(($request && $request.url) || "").replace(/\?.*$/, "").substring(0, 90));
  }
  $done({ body: JSON.stringify(obj) });
})();
