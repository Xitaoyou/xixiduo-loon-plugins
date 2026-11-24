// 夸克网盘 · 单次遍历改写（会员态 / 清晰度 / 门禁 / 并发 / 限速 / 直链 / 广告）
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance
//
// 为什么所有改写挤在一个脚本里：
//   Loon 里同一条响应被前一个脚本 $done 之后，后面的脚本拿到的是改写后的 body，
//   多条规则命中同一 URL 时容易互相打架（早前 speed 抢走 /ad/config 就是这类事故）。
//   合成一个脚本 = 一次 JSON.parse、一次遍历、一次 $done，天然没有顺序问题。
//
// 为什么按 body 特征判断而不是按路径：
//   夸克换版本会改接口名（实测 /vip/info、/account/info、/user/info、/speed、
//   /setting、/ad/list、/banner/list、/transcode 这些路径在服务端就是 404，
//   真正常用的只有 /member、/config、/file/play、/file/download）。
//   所以脚本不看路径，只看 body 里有没有它认得的结构；认不出就 $done({}) 原样放行。
//
// 参数顺序: {fakeVip, maxQuality, openGate, maxConn, clearLimit, grabLink, webhook, blockAds, debugMode}

(function () {
  var KEYS = ["fakeVip", "maxQuality", "openGate", "maxConn", "clearLimit", "grabLink", "webhook", "blockAds", "debugMode"];
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
  // 参数为空时回落到 persistentStore，两边都没有才用默认值。
  // 这样 Loon 里把 input 留空等于「不覆盖」，不会把数字项解析成 NaN。
  function raw(k) {
    var v = k in o ? o[k] : undefined;
    if (v === undefined || v === null || v === "") {
      var s = $persistentStore.read("quark_" + k);
      return (s === null || s === undefined || s === "") ? undefined : s;
    }
    return v;
  }
  function on(k, d) {
    var v = raw(k);
    if (v === undefined) return d;
    return v === true || v === 1 || String(v).toLowerCase() === "true" || String(v) === "1";
  }
  function txt(k, d) {
    var v = raw(k);
    return v === undefined ? d : String(v);
  }

  var FAKE_VIP = on("fakeVip", true);
  var SORT_Q = on("maxQuality", true);
  var GATE = on("openGate", true);
  var CLEAR_LIMIT = on("clearLimit", true);
  var GRAB = on("grabLink", true);
  var BLOCK_ADS = on("blockAds", true);
  var DBG = on("debugMode", false);
  var CONC = parseInt(txt("maxConn", "32"), 10);
  if (!(CONC > 0)) CONC = 32;
  if (CONC > 64) CONC = 64;
  var HOOK = txt("webhook", "").trim();

  if (!$response || !$response.body) { $done({}); return; }
  var obj;
  try { obj = JSON.parse($response.body); } catch (e) { $done({}); return; }
  if (!obj || typeof obj !== "object") { $done({}); return; }

  var URL_ = String(($request && $request.url) || "");
  var PATH = URL_.split("?")[0];

  // ---- 字段名族 ----
  var VIP = {}, GATE_OFF = {}, GATE_ON = {}, LIST = {}, CONC_F = {}, LIMIT_F = {}, LIMIT_SW = {}, URL_F = {};
  ("member_type memberType vip_type vipType vip_level vipLevel member_level memberLevel " +
   "member_grade vip_grade user_type userType is_vip isVip vip svip is_svip isSvip " +
   "is_member isMember is_vip_forever isYearVip is_year_vip vip_status vipStatus " +
   "member_status memberStatus member_exp_at vip_exp_at vipExpire vip_expire expire_at " +
   "expireAt exp_at expAt end_time endTime vip_end_time member_expire_at memberExpireAt")
    .split(" ").forEach(function (k) { VIP[k] = 1; });
  ("need_vip needVip vip_only vipOnly need_pay needPay pay_only payOnly need_buy needBuy " +
   "is_charge isCharge need_member needMember vip_required vipRequired is_trial isTrial " +
   "locked is_lock isLock need_purchase needPurchase")
    .split(" ").forEach(function (k) { GATE_OFF[k] = 1; });
  ("can_play canPlay playable allow_play allowPlay is_play available")
    .split(" ").forEach(function (k) { GATE_ON[k] = 1; });
  ("video_list videoList play_list playList streams stream_list streamList quality_list " +
   "qualityList qualities videos transcode_list")
    .split(" ").forEach(function (k) { LIST[k] = 1; });
  ("thread threads thread_num threadNum max_thread maxThread max_thread_num maxThreadNum " +
   "download_thread downloadThread download_thread_num concurrent concurrency " +
   "max_concurrent maxConcurrent max_conn maxConn max_connection maxConnection " +
   "download_concurrency downloadConcurrency part_thread partThread slice_thread " +
   "sliceThread parallel parallel_num parallelNum")
    .split(" ").forEach(function (k) { CONC_F[k] = 1; });
  ("speed_limit speedLimit limit_speed limitSpeed max_speed maxSpeed down_speed_limit " +
   "downSpeedLimit download_speed_limit downloadSpeedLimit rate_limit rateLimit throttle " +
   "bandwidth_limit bandwidthLimit upload_speed_limit uploadSpeedLimit limit_rate limitRate " +
   "free_speed_limit freeSpeedLimit")
    .split(" ").forEach(function (k) { LIMIT_F[k] = 1; });
  ("is_limit isLimit limited throttled speed_limited speedLimited is_speed_limit " +
   "isSpeedLimit need_limit needLimit rate_limited rateLimited")
    .split(" ").forEach(function (k) { LIMIT_SW[k] = 1; });
  ("download_url downloadUrl downloadURI play_url playUrl m3u8_url m3u8Url video_url " +
   "videoUrl origin_url originUrl file_url fileUrl src url")
    .split(" ").forEach(function (k) { URL_F[k] = 1; });

  var FAR = 4102444800; // 2100-01-01 00:00:00 UTC
  var QMAP = { "4k": 2160, "2k": 1440, "1080p": 1080, "1080": 1080, "720p": 720,
               "720": 720, "540p": 540, "480p": 480, "360p": 360, "240p": 240,
               "\u539f\u753b": 4320, "\u8d85\u6e05": 1080, "\u9ad8\u6e05": 720,
               "\u6807\u6e05": 480, "\u6d41\u7545": 360 };

  // 类型必须按原值走：客户端拿 typeof 判断，数字变字符串会直接解析崩。
  function shape(k, v) {
    var lk = k.toLowerCase();
    if (lk.indexOf("exp") >= 0 || lk.indexOf("end") >= 0) {
      if (typeof v === "number") return FAR;
      if (typeof v === "string") return "2100-01-01 00:00:00";
      return v;
    }
    if (lk.indexOf("level") >= 0 || lk.indexOf("grade") >= 0 || lk.indexOf("status") >= 0) {
      if (typeof v === "number") return 2;
      if (typeof v === "string") return "SVIP";
      if (typeof v === "boolean") return true;
      return v;
    }
    if (typeof v === "boolean") return true;
    if (typeof v === "number") return 1;
    if (typeof v === "string") return "SVIP";
    return v;
  }

  function qScore(it) {
    if (!it || typeof it !== "object") return -1;
    var h = Number(it.height || it.v_height || it.vHeight || 0);
    if (!h && it.quality) {
      var q = String(it.quality).toLowerCase().replace(/[^a-z0-9\u4e00-\u9fa5]/g, "");
      for (var k in QMAP) { if (q.indexOf(k) >= 0) { h = QMAP[k]; break; } }
      if (!h) { var m = q.match(/(\d{3,4})/); if (m) h = Number(m[1]); }
    }
    if (!h && it.resolution) {
      var r = String(it.resolution).match(/(\d{3,4})\s*[xX*]\s*(\d{3,4})/);
      if (r) h = Number(r[2]);
    }
    var br = Number(it.bitrate || it.bit_rate || it.br || 0);
    return h * 100000 + br;
  }

  var st = { vip: 0, gate: 0, sort: 0, conc: 0, limit: 0, ads: 0 };
  var links = [];

  function pushLink(u) {
    if (typeof u !== "string" || u.length < 24 || u.indexOf("http") !== 0) return;
    if (links.indexOf(u) >= 0) return;
    if (!/quark\.cn|alicdn\.com|myqcloud\.com|aliyuncs\.com/.test(u) &&
        !/\.(mp4|m3u8|mkv|mov|webm|flv|pdf|zip|7z|rar)(\?|$)/i.test(u)) return;
    links.push(u);
  }

  // 广告只在确实像广告的接口上清，避免把文件列表的 data 一起清掉。
  var AD_PATH = /(?:\/ad\/|advert|splash|promotion|banner|popup|launch|activity|\/ads)/i.test(PATH);
  var AD_KEYS = {};
  ["ads", "ad_list", "adList", "banners", "banner_list", "splash", "splash_ad",
   "promotion", "popup", "activity_list", "ad_data"].forEach(function (k) { AD_KEYS[k] = 1; });

  function walk(n) {
    if (!n) return;
    var tag = Object.prototype.toString.call(n);
    if (tag === "[object Array]") { for (var i = 0; i < n.length; i++) walk(n[i]); return; }
    if (tag !== "[object Object]") return;
    for (var k in n) {
      if (!Object.prototype.hasOwnProperty.call(n, k)) continue;
      var v = n[k];
      if (v && typeof v === "object") {
        if (SORT_Q && LIST[k] === 1 && tag === "[object Object]" &&
            Object.prototype.toString.call(v) === "[object Array]" && v.length > 1) {
          var before = v.map(qScore).join(",");
          v.sort(function (a, b) { return qScore(b) - qScore(a); });
          if (v.map(qScore).join(",") !== before) st.sort++;
        }
        // 只清真的装着东西的广告容器：空数组空对象原样留着，免得白白改写 body
        if (BLOCK_ADS && AD_KEYS[k] === 1) {
          if (Object.prototype.toString.call(v) === "[object Array]") {
            if (v.length) { n[k] = []; st.ads++; continue; }
          } else if (Object.keys(v).length) { n[k] = {}; st.ads++; continue; }
        }
        walk(v);
        continue;
      }
      if (GRAB && URL_F[k] === 1 && typeof v === "string") pushLink(v);
      if (FAKE_VIP && VIP[k] === 1) {
        var nv = shape(k, v);
        if (nv !== v) { n[k] = nv; st.vip++; }
        continue;
      }
      if (GATE && GATE_OFF[k] === 1 && v !== false && v !== 0) { n[k] = false; st.gate++; continue; }
      if (GATE && GATE_ON[k] === 1 && v !== true && v !== 1) { n[k] = true; st.gate++; continue; }
      // 并发只往上抬，服务端本来就给得更大就别压回去
      if (typeof v === "number" && v > 0 && v < CONC && CONC_F[k] === 1) { n[k] = CONC; st.conc++; continue; }
      if (CLEAR_LIMIT && LIMIT_F[k] === 1 && typeof v === "number" && v !== 0) { n[k] = 0; st.limit++; continue; }
      if (CLEAR_LIMIT && LIMIT_SW[k] === 1 && v !== false && v !== 0) { n[k] = false; st.limit++; continue; }
    }
  }

  walk(obj);

  // 确认是广告接口（路径带 /ad/、splash、banner、popup 之类）时，顶层容器也换成空壳。
  // 放在 walk 之后：先按字段名清掉能认出来的，再把剩下的整块收口。
  if (BLOCK_ADS && AD_PATH && obj && typeof obj === "object") {
    ["data", "result", "list", "items"].forEach(function (k) {
      if (!Object.prototype.hasOwnProperty.call(obj, k)) return;
      var v = obj[k];
      if (Object.prototype.toString.call(v) === "[object Array]") {
        if (v.length) { obj[k] = []; st.ads++; }
      } else if (v && typeof v === "object" && Object.keys(v).length) { obj[k] = {}; st.ads++; }
    });
  }

  var changed = (st.vip + st.gate + st.sort + st.conc + st.limit + st.ads) > 0;

  if (GRAB && links.length) {
    var all = [];
    try { all = JSON.parse($persistentStore.read("quark_links") || "[]"); } catch (e) { all = []; }
    for (var li = 0; li < links.length; li++) all.unshift({ t: Date.now(), u: links[li] });
    var seen = {}, keep = [];
    for (var lj = 0; lj < all.length && keep.length < 40; lj++) {
      if (!all[lj] || !all[lj].u || seen[all[lj].u]) continue;
      seen[all[lj].u] = 1;
      keep.push(all[lj]);
    }
    $persistentStore.write(JSON.stringify(keep), "quark_links");
    $notification.post("Quark直链", "抓到 " + links.length + " 条 · 共 " + keep.length + " 条在本地",
      links[0].substring(0, 60) + "...");
    if (HOOK.indexOf("http") === 0) {
      $httpClient.post({
        url: HOOK,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api: PATH, links: links })
      }, function (err) {
        if (DBG) $notification.post("Quark直链", "webhook", err ? String(err) : "已推送");
      });
    }
  }

  if (!changed) { $done({}); return; }

  if (DBG) {
    var bits = [];
    if (st.vip) bits.push("会员字段 " + st.vip);
    if (st.gate) bits.push("门禁位 " + st.gate);
    if (st.sort) bits.push("清晰度排序 " + st.sort);
    if (st.conc) bits.push("并发→" + CONC + " ×" + st.conc);
    if (st.limit) bits.push("限速清零 " + st.limit);
    if (st.ads) bits.push("广告位 " + st.ads);
    $notification.post("Quark增强", bits.join(" · "), PATH.replace(/^https?:\/\//, "").substring(0, 80));
  }
  $done({ body: JSON.stringify(obj) });
})();
