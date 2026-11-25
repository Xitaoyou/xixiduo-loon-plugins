/*
 * 轻听英语 VIP · 权益改写
 * Xitaoyou | xixiduo-loon-plugins
 *
 * 分三层处理，从精确到兜底：
 *   1) 已知接口：1.9.1 GET /v1/UserLaunchAppReport、2.0.6 POST /v3/2/report/launch/{ts}、
 *      learnywhere.cn 的 purchase2 / promote/in-duration / le/buy/member、V3 的 app-configs 与 episode/command
 *   2) V3 启动接口 data_encrypted=1：按开关改写成 data_encrypted=0 + 明文 privileges
 *   3) 兜底：同域名下没见过的路径，只要响应里出现权益语义就按字段级改，App 改版换路径时不会静默失效
 *
 * 只改本机客户端读到的 JSON：服务端仍按真实账号下发权益，加密的 V3 报文由服务端密钥生成，
 * 本脚本不伪造密文，只在明文层与降级路径上生效。
 */
(function () {
  "use strict";

  // 顺序必须与 .plugin 的 [Argument] 声明顺序、[Script] 里的占位符顺序保持一致，
  // Loon 在某些版本下把 $argument 当位置数组传。
  var ORDER = [
    "modifyPrivileges", "downgradeV3", "modifyPurchase", "modifyPromote",
    "quota", "expireAt", "probeMode", "debugMode"
  ];

  function readArgs() {
    var out = {};
    function absorb(v) {
      if (!v) return;
      if (Array.isArray(v)) {
        v.forEach(function (x, i) { if (ORDER[i]) out[ORDER[i]] = x; });
        return;
      }
      if (typeof v === "object") {
        for (var k in v) if (Object.prototype.hasOwnProperty.call(v, k)) out[k] = v[k];
        return;
      }
      if (typeof v === "string") {
        var t = v.trim();
        if (t.charAt(0) === "{" || t.charAt(0) === "[") {
          try { absorb(JSON.parse(t)); } catch (e) {}
        }
      }
    }
    absorb(typeof $argument === "undefined" ? null : $argument);
    return out;
  }

  var A = readArgs();

  function raw(name) {
    if (Object.prototype.hasOwnProperty.call(A, name)) return A[name];
    return $persistentStore.read("qt_" + name);
  }

  function flag(name, dft) {
    var v = raw(name);
    if (v === null || v === undefined || v === "") return dft;
    if (v === true || v === 1) return true;
    if (v === false || v === 0) return false;
    var s = String(v).toLowerCase();
    if (s === "true" || s === "1" || s === "on" || s === "yes") return true;
    if (s === "false" || s === "0" || s === "off" || s === "no") return false;
    return dft;
  }

  function num(name, dft) {
    var v = raw(name);
    if (v === null || v === undefined || v === "") return dft;
    var n = Number(String(v).replace(/[^\d.-]/g, ""));
    return isFinite(n) && n > 0 ? n : dft;
  }

  var DBG = flag("debugMode", false);
  var PROBE = flag("probeMode", false);
  var DO_PRIV = flag("modifyPrivileges", true);
  var DO_DOWN = flag("downgradeV3", true);
  var DO_BUY = flag("modifyPurchase", true);
  var DO_PROMO = flag("modifyPromote", true);
  var QUOTA = Math.round(num("quota", 999));
  var FAR = Math.round(num("expireAt", 4077153336000)); // 2099-03-…，与旧版脚本同值

  var GRANT = words("granted is_granted isgranted enabled available usable valid is_valid can_use canuse unlocked is_unlocked purchased is_purchased owned is_owned is_vip isvip is_member ismember vip svip activated is_activated");
  var DENY = words("need_vip needvip need_pay needpay locked is_locked islocked pay_required payrequired vip_only viponly require_vip requirevip is_expired expired");
  var EXPIRE = words("expire_date expiredate expire_time expiretime expire_at expireat expiry expired_at expiredat end_time endtime end_date enddate valid_until validuntil exp_at expat dead_line deadline");
  var QUOTA_K = words("dl_quota dlquota download_quota downloadquota download_limit downloadlimit max_download maxdownload free_download_count freedownloadcount quota_left quotaleft");
  var SUB = words("subscription_count subscriptioncount user_has_preferences userhaspreferences subscription_has_updates subscriptionhasupdates");
  var HINT = words("privileges privilege rights entitlements entitlement auth vip member account user_status userstatus membership");
  var TYPE = {
    user_type: 1, usertype: 1,
    collins_user_type: 1, collinsusertype: 1,
    vip_type: 1, viptype: 1,
    member_type: 1, membertype: 1,
    vip_level: 3, viplevel: 3,
    member_level: 3, memberlevel: 3
  };

  // 已知特权键：即使不在 privileges 子树里也照改
  var KNOWN = words("lrc_unlimited_online_playback lrc_unlimited_download wordroot collins wordderive wordsyn wordlist bbvip bbnote yanzhibao sushua wordbooks");

  function words(list) {
    var o = Object.create(null);
    list.split(/\s+/).forEach(function (w) { if (w) o[w] = 1; });
    return o;
  }

  function shapeGrant(v) {
    if (typeof v === "boolean") return true;
    if (typeof v === "number") return v > 0 ? v : 1;
    if (typeof v === "string") {
      if (v === "" || v === "0" || v.toLowerCase() === "false") return "1";
      return v;
    }
    return v;
  }

  function shapeDeny(v) {
    if (typeof v === "boolean") return false;
    if (typeof v === "number") return 0;
    if (typeof v === "string") return v === "0" ? v : "0";
    return v;
  }

  function shapeExpire(v) {
    if (typeof v === "number") return v > FAR ? v : FAR;
    if (typeof v === "string") {
      if (v === "") return "2100-01-01 00:00:00";
      if (/^\s*\d+\s*$/.test(v)) return String(Math.max(Number(v), FAR));
      return v; // 带时区的日期串语义不明，保持原值
    }
    return v;
  }

  function shapeQuota(v) {
    if (typeof v === "number") return v > QUOTA ? v : QUOTA;
    if (typeof v === "string" && /^\s*\d+\s*$/.test(v)) return String(Math.max(Number(v), QUOTA));
    return v;
  }

  function shapeType(v, target) {
    if (typeof v === "number") return v > target ? v : target;
    if (typeof v === "string") return /^\s*\d+\s*$/.test(v) ? String(target) : v;
    if (typeof v === "boolean") return true;
    return v;
  }

  var hitCount = 0;

  function rewriteTree(root, rootIsEnt) {
    walk(root, rootIsEnt === true);
    return hitCount;

    function walk(n, ent) {
      if (Array.isArray(n)) {
        for (var i = 0; i < n.length; i++) walk(n[i], ent);
        return;
      }
      if (!n || typeof n !== "object") return;
      for (var k in n) {
        if (!Object.prototype.hasOwnProperty.call(n, k)) continue;
        var v = n[k];
        if (v && typeof v === "object") {
          walk(v, ent || HINT[String(k).toLowerCase()] === 1);
          continue;
        }
        var nv = pick(String(k), v, ent);
        if (nv !== v) { n[k] = nv; hitCount++; }
      }
    }

    function pick(k, v, ent) {
      var lk = k.toLowerCase();
      if (GRANT[lk]) return shapeGrant(v);
      if (DENY[lk]) return shapeDeny(v);
      if (SUB[lk]) return shapeGrant(v);
      if (QUOTA_K[lk]) return shapeQuota(v);
      if (Object.prototype.hasOwnProperty.call(TYPE, lk)) return shapeType(v, TYPE[lk]);
      if (EXPIRE[lk] && (ent || KNOWN[lk])) return shapeExpire(v);
      return v;
    }
  }

  function buildEntitlement() {
    var body = {
      privileges: {
        lrc_unlimited_online_playback: { expire_date: FAR, granted: 1 },
        lrc_unlimited_download: { expire_date: FAR, granted: 1 },
        wordroot: { expire_date: FAR, granted: 1, user_type: 1 },
        collins: { expire_date: FAR, granted: 1, collins_user_type: 1 },
        user_status: {
          dl_quota: QUOTA,
          subscription_count: 1,
          user_has_preferences: 1,
          subscription_has_updates: 1
        }
      },
      user_status: { dl_quota: QUOTA, subscription_count: 1 }
    };
    return body;
  }

  // data_body 可能是对象，也可能是 JSON 字符串；返回 {obj, wasString} 或 null
  function peel(data) {
    var b = data.data_body;
    if (b && typeof b === "object") return { obj: b, wasString: false };
    if (typeof b === "string" && b) {
      var t = b.trim();
      if (t.charAt(0) === "{" || t.charAt(0) === "[") {
        try { return { obj: JSON.parse(t), wasString: true }; } catch (e) {}
      }
    }
    return null;
  }

  function commit(data, holder) {
    if (!holder) return;
    data.data_body = holder.wasString ? JSON.stringify(holder.obj) : holder.obj;
  }

  var notes = [];

  var before = "";

  // 只有真的改动了才回写 body；没变就走 $done({}) 原样放行，避免无意义重写。
  function finish(url) {
    if (DBG && notes.length) {
      try {
        $notification.post("轻听英语 VIP", notes.join("；"), shortUrl(url));
      } catch (e) {}
    }
    if (PROBE) {
      try { console.log("[QT probe] " + notes.join(" | ")); } catch (e) {}
    }
    var after = JSON.stringify(current);
    if (after === before) { $done({}); return; }
    $done({ body: after });
  }

  // 判断响应里是否出现权益/会员语义，兜底路径用
  function hasHint(o) {
    var found = false;
    (function scan(n, depth) {
      if (found || !n || typeof n !== "object" || depth > 4) return;
      for (var k in n) {
        if (!Object.prototype.hasOwnProperty.call(n, k)) continue;
        var lk = String(k).toLowerCase();
        var v = n[k];
        if (HINT[lk] || KNOWN[lk] || GRANT[lk] || DENY[lk] || TYPE[lk] || SUB[lk]) { found = true; return; }
        if (v && typeof v === "object") scan(v, depth + 1);
        if (found) return;
      }
    })(o, 0);
    return found;
  }

  function shortUrl(u) {
    return String(u || "").replace(/^https?:\/\//, "").replace(/\?.*$/, "").substring(0, 80);
  }

  function peek(data, path) {
    var info = [];
    info.push("path=" + path);
    info.push("enc=" + (data.data_encrypted === undefined ? "-" : data.data_encrypted));
    var t = data.data_body;
    info.push("bodyType=" + (t === null ? "null" : Array.isArray(t) ? "array" : typeof t));
    if (t && typeof t === "object") info.push("keys=" + Object.keys(t).join(","));
    if (data.v3_security && typeof data.v3_security === "object") {
      info.push("v3sec=" + Object.keys(data.v3_security).join(","));
    }
    return info.join(" ");
  }

  // ---------- 主流程 ----------

  if (!$response || typeof $response.body !== "string" || !$response.body) { $done({}); return; }

  var url = String(($request && $request.url) || "");
  var path = url.replace(/^https?:\/\/[^\/]+/i, "").replace(/\?.*$/, "");

  var current;
  try { current = JSON.parse($response.body); } catch (e) {
    if (DBG) { try { $notification.post("轻听英语 VIP", "响应不是 JSON，放行", shortUrl(url)); } catch (e2) {} }
    $done({}); return;
  }
  if (!current || typeof current !== "object") { $done({}); return; }
  before = JSON.stringify(current);

  var isV3Launch = /\/v3\/2\/report\/launch\//.test(path);
  var isV1Launch = /\/v1\/UserLaunchAppReport/.test(path);
  var isAppConfig = /\/v3\/qt\/app-configs\//.test(path);
  var isPurchase = /\/api\/qt\/buy\/vip\/purchase2/.test(path);
  var isPromote = /\/api\/buy\/promote\/in-duration/.test(path);
  var isMember = /\/le\/buy\/member/.test(path);
  var isEpisode = /\/v3\/qt\/episode\/command\//.test(path);

  var KNOWN_HOST = /^https?:\/\/(?:api|sapi)\.beingfine\.cn\//i.test(url) || /^https?:\/\/learnywhere\.cn\//i.test(url);

  if (PROBE) {
    notes.push(peek(current, path));
    if (isPurchase || isPromote || isMember) {
      var pb = peel(current);
      if (pb && pb.obj && pb.obj.auth) notes.push("authKeys=" + Object.keys(pb.obj.auth).join(","));
      if (pb && pb.obj && pb.obj.account) notes.push("accountKeys=" + Object.keys(pb.obj.account).join(","));
    }
    finish(url);
    return;
  }

  if (!(isV3Launch || isV1Launch || isAppConfig || isPurchase || isPromote || isMember || isEpisode)) {
    // 兜底：同域名下的新路径（App 改版常换路径），只要 body 里出现权益形态就按字段级改，
    // 不依赖路径白名单，避免下次升级直接静默失效。
    if (!KNOWN_HOST) { $done({}); return; }
    var gh = peel(current);
    if (!gh || !hasHint(gh.obj)) { $done({}); return; }
    rewriteTree(gh.obj, true);
    notes.push("兜底路径 " + path + " 改写 " + hitCount + " 处");
    commit(current, gh);
    finish(url);
    return;
  }

  if (isV3Launch && current.data_encrypted === 1) {
    if (!DO_DOWN) { notes.push("V3 加密响应，降级开关关闭，放行"); finish(url); return; }
    current.data_encrypted = 0;
    current.data_body = buildEntitlement();
    notes.push("V3 启动响应降级注入 privileges");
    finish(url);
    return;
  }

  var holder = peel(current);
  if (!holder) { notes.push("data_body 无法解析，放行"); finish(url); return; }

  if (isV3Launch || isV1Launch) {
    if (DO_PRIV) {
      rewriteTree(holder.obj, true);
      notes.push("启动响应权益改写 " + hitCount + " 处");
    }
    commit(current, holder);
    finish(url);
    return;
  }

  if (isAppConfig || isEpisode) {
    // 配置与播放指令只做明文下的权益字段改写，不动结构
    rewriteTree(holder.obj, true);
    if (hitCount) notes.push(path + " 权益改写 " + hitCount + " 处");
    commit(current, holder);
    finish(url);
    return;
  }

  if (isPurchase) {
    if (DO_BUY) {
      var acct = holder.obj.account;
      if (acct && typeof acct === "object") {
        if (Object.prototype.hasOwnProperty.call(acct, "is_login")) acct.is_login = 1;
        if (Object.prototype.hasOwnProperty.call(acct, "vip_type")) acct.vip_type = shapeType(acct.vip_type, 1);
        if (Object.prototype.hasOwnProperty.call(acct, "expiry")) acct.expiry = shapeExpire(acct.expiry);
        notes.push("purchase2 account 会员态改写");
      }
      rewriteTree(holder.obj, true);
    }
    commit(current, holder);
    finish(url);
    return;
  }

  if (isPromote) {
    if (DO_PROMO) {
      var auth = holder.obj.auth;
      if (auth && typeof auth === "object") {
        Object.keys(auth).forEach(function (k) {
          var it = auth[k];
          if (!it || typeof it !== "object") return;
          if (Object.prototype.hasOwnProperty.call(it, "op")) it.op = shapeGrant(it.op);
          if (Object.prototype.hasOwnProperty.call(it, "pa")) it.pa = shapeGrant(it.pa);
        });
        notes.push("promote auth 权益位改写");
      }
      if (Object.prototype.hasOwnProperty.call(holder.obj, "in_purchase_duration")) {
        holder.obj.in_purchase_duration = shapeGrant(holder.obj.in_purchase_duration);
      }
    }
    commit(current, holder);
    finish(url);
    return;
  }

  if (isMember) {
    rewriteTree(holder.obj, true);
    notes.push("le/buy/member 会员态改写 " + hitCount + " 处");
    commit(current, holder);
    finish(url);
    return;
  }

  $done({});
})();
