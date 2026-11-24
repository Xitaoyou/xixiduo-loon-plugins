// 夸克网盘 · 会员态伪装（只改客户端读到的字段）
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 服务端按真实账号发权益。本脚本只改 App 读到的 JSON，不会让服务端认为你是会员，
// 也不会解锁需要服务端签名的能力（离线缓存、超大文件直链等）。
//
// 参数顺序: {fakeVip, debugMode}

(function () {
  var KEYS = ["fakeVip", "debugMode"];
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
  var ON = on("fakeVip", true);
  var FAR = 4102444800; // 2100-01-01 00:00:00 UTC

  var FIELDS = {};
  [
    "member_type", "memberType", "vip_type", "vipType", "vip_level", "vipLevel",
    "member_level", "memberLevel", "member_grade", "vip_grade", "user_type", "userType",
    "is_vip", "isVip", "vip", "svip", "is_svip", "isSvip", "is_member", "isMember",
    "is_vip_forever", "isYearVip", "is_year_vip", "vip_status", "vipStatus",
    "member_status", "memberStatus", "member_exp_at", "vip_exp_at", "vipExpire",
    "vip_expire", "expire_at", "expireAt", "exp_at", "expAt", "end_time", "endTime",
    "vip_end_time", "member_expire_at", "memberExpireAt"
  ].forEach(function (k) { FIELDS[k] = 1; });

  // 客户端到处用 typeof 判类型：原值是数字就还数字、字符串就还字符串。
  // 类型改错会让解析直接抛异常，整个页面白掉。
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

  var hit = 0;
  function walk(n) {
    if (!n) return;
    var tag = Object.prototype.toString.call(n);
    if (tag === "[object Array]") { for (var i = 0; i < n.length; i++) walk(n[i]); return; }
    if (tag !== "[object Object]") return;
    for (var k in n) {
      if (!Object.prototype.hasOwnProperty.call(n, k)) continue;
      var v = n[k];
      if (v && typeof v === "object") { walk(v); continue; }
      if (FIELDS[k] === 1) {
        var nv = shape(k, v);
        if (nv !== v) { n[k] = nv; hit++; }
      }
    }
  }

  if (!ON || !$response || !$response.body) { $done({}); return; }
  var obj;
  try { obj = JSON.parse($response.body); } catch (e) { $done({}); return; }
  walk(obj);
  if (!hit) { $done({}); return; }
  if (DBG) $notification.post("Quark会员态", "改了 " + hit + " 个字段", shortUrl());
  $done({ body: JSON.stringify(obj) });

  function shortUrl() {
    return String(($request && $request.url) || "").replace(/\?.*$/, "").substring(0, 90);
  }
})();
