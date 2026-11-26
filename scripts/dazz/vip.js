// Dazz Pro · Loon 响应改写脚本
// 只改本机读到的 JSON，服务端权益不变。Dazz 改版后用同目录 probe.js 抓字段，再回填下面的表。
(function () {
  "use strict";

  var ORDER = ["unlockPro", "unlockForever", "productId", "rewriteRevenueCat", "rewriteReceipt", "farFutureTime", "strictAppOnly", "probeMode", "debugMode"];
  var FAR_BUILTIN = 4070908800000; // 2099-01-01T00:00:00Z
  var BUNDLE_FALLBACK = "dazz.camera.vintagecamera";
  var MAX_BODY = 512 * 1024;

  function raw(name) {
    var a = typeof $argument !== "undefined" ? $argument : null;
    if (a) {
      if (typeof a === "object" && a !== null) {
        if (typeof a.length === "number") {
          var i = ORDER.indexOf(name);
          if (i >= 0 && i < a.length && a[i] !== undefined && a[i] !== null) return String(a[i]);
        } else if (a[name] !== undefined && a[name] !== null) {
          return String(a[name]);
        }
      } else if (typeof a === "string") {
        var s = a.replace(/^\s+/, "");
        if (s.charAt(0) === "{") {
          try {
            var o = JSON.parse(s);
            if (o && o[name] !== undefined && o[name] !== null) return String(o[name]);
          } catch (e) {}
        }
      }
    }
    try {
      var v = $persistentStore.read("dazz_" + name);
      if (v !== null && v !== undefined && v !== "") return String(v);
    } catch (e2) {}
    return "";
  }

  function flag(name, def) {
    var v = raw(name);
    if (v === "") return !!def;
    v = v.toLowerCase();
    return !(v === "false" || v === "0" || v === "no" || v === "off");
  }

  function num(name, def) {
    var v = raw(name);
    if (v === "") return def;
    var n = parseInt(v, 10);
    return isNaN(n) ? def : n;
  }

  var UNLOCK_PRO = flag("unlockPro", true);
  var UNLOCK_FOREVER = flag("unlockForever", true);
  var PROD_ARG = raw("productId") || "auto";
  var DO_RC = flag("rewriteRevenueCat", true);
  var DO_RECEIPT = flag("rewriteReceipt", true);
  var STRICT = flag("strictAppOnly", false);
  var PROBE = flag("probeMode", false);
  var DEBUG = flag("debugMode", false);
  var FAR = num("farFutureTime", FAR_BUILTIN);
  if (FAR > 0 && FAR < 1e11) FAR = FAR * 1000;
  if (!FAR || FAR < 2000000000000) FAR = FAR_BUILTIN;

  function words(s) {
    var map = {};
    var arr = s.split(/\s+/);
    for (var i = 0; i < arr.length; i++) if (arr[i]) map[arr[i]] = 1;
    return map;
  }

  var BOOL_TRUE = words("is_pro isPro isVip is_vip vip pro isPremium is_premium premium isMember is_member member" +
    " isPaid is_paid paid purchased isPurchased is_purchased hasPurchased has_purchased" +
    " isForever is_forever forever isLifetime is_lifetime lifetime unlocked isUnlocked is_unlocked" +
    " is_valid isValid hasPro has_pro hasVip has_vip isSubscribed is_subscribed subscribed" +
    " non_consumable_purchased hasForever has_forever proUnlocked pro_unlocked isProUser is_pro_user");
  var BOOL_FALSE = words("is_trial isTrial in_trial inTrial on_trial is_expired isExpired expired" +
    " need_pay needPay need_purchase needPurchase need_buy needBuy show_pay showPay show_buy showBuy" +
    " is_free isFree free_user isGuest is_guest guest is_limited isLimited");
  var INT_MIN = {
    vip_type: 1, vipType: 1, vip_level: 9, vipLevel: 9, level: 9,
    member_type: 1, memberType: 1, pro_type: 1, proType: 1,
    sub_type: 2, subType: 2, user_type: 1, userType: 1,
    contract_status: 1, contractStatus: 1, period_type: 2, periodType: 2,
    pay_status: 1, payStatus: 1, status_vip: 1
  };
  var TIME_KEYS = words("expire_time expireTime expires_at expiresAt expire_at expireAt expiry expiry_time expiryTime" +
    " expired_at expiredAt vip_expire vipExpire pro_expire proExpire valid_until validUntil" +
    " end_time endTime member_expire memberExpire forever_time foreverTime expire_date expireDate");
  var ARRAY_KEYS = /^(purchased|owned|unlocked|bought)/i;
  var PRICE_KEYS = words("price amount currency original_price originalPrice pay_url payUrl");
  var ENT_PREFIX = /^(vip|pro|premium|member|membership|subscription|purchase|order|entitlement|account|user_info|userinfo|pay|config|profile)/i;

  function hasKey(map, k) { return Object.prototype.hasOwnProperty.call(map, k); }
  function hasAny(node, map) {
    for (var k in node) {
      if (Object.prototype.hasOwnProperty.call(node, k) && hasKey(map, k)) return true;
    }
    return false;
  }
  function isArr(v) { return Object.prototype.toString.call(v) === "[object Array]"; }

  function toBool(v, target) {
    if (typeof v === "boolean") return target;
    if (typeof v === "number") return target ? 1 : 0;
    if (typeof v === "string") return target ? "true" : "false";
    return target;
  }

  function rampInt(v, min) {
    if (typeof v === "number") return v >= min ? v : min;
    if (typeof v === "string" && /^-?\d+$/.test(v)) {
      var n = parseInt(v, 10);
      return n >= min ? v : String(min);
    }
    return v;
  }

  // 时间戳只升不降；按量级判断毫秒/秒，不把秒值抬成毫秒
  function rampTime(v, farMs) {
    if (typeof v === "number" || (typeof v === "string" && /^\d+$/.test(v))) {
      var n = typeof v === "number" ? v : Number(v);
      var target;
      if (n > 1e11) target = farMs;
      else if (n > 1e8) target = Math.floor(farMs / 1000);
      else target = farMs;
      if (n >= target) return v;
      return typeof v === "string" ? String(target) : target;
    }
    return v;
  }

  function isoOf(ms) {
    var d = new Date(ms);
    var p = function (n) { return n < 10 ? "0" + n : String(n); };
    return d.getUTCFullYear() + "-" + p(d.getUTCMonth() + 1) + "-" + p(d.getUTCDate()) +
      "T" + p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + ":" + p(d.getUTCSeconds()) + "Z";
  }

  // Apple 的 receipt 时间格式：yyyy-MM-dd HH:mm:ss Etc/GMT
  function appleDate(ms) {
    var d = new Date(ms);
    var p = function (n) { return n < 10 ? "0" + n : String(n); };
    return d.getUTCFullYear() + "-" + p(d.getUTCMonth() + 1) + "-" + p(d.getUTCDate()) + " " +
      p(d.getUTCHours()) + ":" + p(d.getUTCMinutes()) + ":" + p(d.getUTCSeconds()) + " Etc/GMT";
  }

  function b64(s) {
    try { if (typeof btoa === "function") return btoa(s); } catch (e) {}
    var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    var out = "", i;
    for (i = 0; i < s.length; i += 3) {
      var c1 = s.charCodeAt(i), c2 = s.charCodeAt(i + 1), c3 = s.charCodeAt(i + 2);
      var e1 = c1 >> 2;
      var e2 = ((c1 & 3) << 4) | (isNaN(c2) ? 0 : c2 >> 4);
      var e3 = isNaN(c2) ? 64 : (((c2 & 15) << 2) | (isNaN(c3) ? 0 : c3 >> 6));
      var e4 = isNaN(c3) ? 64 : (c3 & 63);
      out += chars.charAt(e1) + chars.charAt(e2) +
        (e3 === 64 ? "=" : chars.charAt(e3)) + (e4 === 64 ? "=" : chars.charAt(e4));
    }
    return out;
  }

  // ---------- App Store 内购凭证 ----------
  function isReceipt(url) { return /(?:buy|sandbox)\.itunes\.apple\.com\/verifyReceipt/i.test(url); }

  // verifyReceipt 是全机共用的渠道：先确认这张凭证属于 Dazz，否则会影响其它 App 的校验
  var BUNDLE_RE = /dazz|haocai|camerafilm/i;

  function userAgent() {
    var h = ($request && $request.headers) || {};
    return String(h["User-Agent"] || h["user-agent"] || "");
  }

  function ownedByDazz(rc) {
    var b = (rc && (rc.bundle_id || rc.Bundle_Id || rc.bundleId)) || "";
    if (b) return BUNDLE_RE.test(b);
    return BUNDLE_RE.test(userAgent());
  }

  function productFor(bundle) {
    var p = PROD_ARG;
    if (p === "auto" || p === "") return (bundle || BUNDLE_FALLBACK) + ".forever";
    return p;
  }

  function receiptUnlock(obj) {
    if (!obj || typeof obj !== "object" || isArr(obj)) return false;
    var rc = obj.receipt;
    if (!rc || typeof rc !== "object") return false;
    if (!ownedByDazz(rc)) return false;

    var bundle = rc.bundle_id || rc.Bundle_Id || rc.bundleId || "";
    var prod = productFor(bundle);
    var now = Date.now();
    var buyMs = now - 3 * 86400000;
    var tid = "49000" + String(now).slice(-10);
    var item = {
      quantity: "1",
      transaction_id: tid,
      original_transaction_id: tid,
      purchase_date: appleDate(buyMs),
      purchase_date_ms: String(buyMs),
      purchase_date_pst: appleDate(buyMs),
      original_purchase_date: appleDate(buyMs),
      original_purchase_date_ms: String(buyMs),
      original_purchase_date_pst: appleDate(buyMs),
      product_id: prod,
      is_trial_period: "false",
      is_in_intro_offer_period: "false",
      in_app_ownership_type: "PURCHASED",
      web_order_line_item_id: "4900" + String(now).slice(-9)
    };
    if (!UNLOCK_FOREVER) {
      item.expires_date = appleDate(FAR);
      item.expires_date_ms = String(FAR);
      item.expires_date_pst = appleDate(FAR);
    }

    var keep = [];
    if (isArr(rc.in_app)) {
      for (var i = 0; i < rc.in_app.length; i++) {
        var it = rc.in_app[i];
        if (it && it.product_id === prod) continue;
        keep.push(it);
      }
    }
    keep.unshift(item);
    rc.in_app = keep;

    obj.status = 0;
    obj.environment = "Production";
    obj.latest_receipt_info = [item];
    obj.pending_renewal_info = [{
      product_id: prod,
      original_transaction_id: tid,
      auto_renew_product_id: prod,
      auto_renew_status: "1"
    }];
    obj.latest_receipt = b64("dazz_receipt_" + tid + "_dazz_receipt_" + tid);
    return true;
  }

  // ---------- RevenueCat ----------
  function isRC(url) { return /revenuecat\.com\//i.test(url) || /rc-backup\.com\//i.test(url); }

  function firstProduct(sub, obj) {
    var list = [], k;
    if (sub && sub.subscriptions) {
      for (k in sub.subscriptions) if (Object.prototype.hasOwnProperty.call(sub.subscriptions, k)) list.push(k);
    }
    if (sub && sub.non_subscriptions) {
      for (k in sub.non_subscriptions) if (Object.prototype.hasOwnProperty.call(sub.non_subscriptions, k)) list.push(k);
    }
    if (sub && sub.entitlements) {
      for (k in sub.entitlements) {
        if (!Object.prototype.hasOwnProperty.call(sub.entitlements, k)) continue;
        var e = sub.entitlements[k];
        if (e && typeof e.product_identifier === "string" && e.product_identifier) list.push(e.product_identifier);
      }
    }
    if (obj && typeof obj.product_identifier === "string") list.push(obj.product_identifier);
    return list.length ? list[0] : productFor("");
  }

  function rcUnlock(obj) {
    if (!obj || typeof obj !== "object" || isArr(obj)) return false;
    var sub = obj.subscriber;
    if (!sub && (obj.entitlements || obj.subscriptions)) {
      sub = obj;
      obj.subscriber = sub;
    }
    if (!sub || typeof sub !== "object") return false;

    var now = Date.now();
    var exp = isoOf(FAR);
    var buy = isoOf(now - 3 * 86400000);
    var prod = firstProduct(sub, obj);
    var k;

    var ents = sub.entitlements;
    if (!ents || typeof ents !== "object") { ents = {}; sub.entitlements = ents; }
    var keys = [];
    for (k in ents) if (Object.prototype.hasOwnProperty.call(ents, k)) keys.push(k);
    if (keys.length === 0) keys = ["pro", "forever", "premium"];
    if (keys.indexOf("pro") < 0) keys.push("pro");
    for (var i = 0; i < keys.length; i++) {
      ents[keys[i]] = { expires_date: exp, purchase_date: buy, product_identifier: prod };
    }

    var subs = sub.subscriptions;
    if (!subs || typeof subs !== "object") { subs = {}; sub.subscriptions = subs; }
    var sk = [];
    for (k in subs) if (Object.prototype.hasOwnProperty.call(subs, k)) sk.push(k);
    if (sk.length === 0) sk = [prod];
    for (var j = 0; j < sk.length; j++) {
      var cur = subs[sk[j]] && typeof subs[sk[j]] === "object" ? subs[sk[j]] : {};
      cur.billing_issues_detected_at = null;
      cur.expires_date = exp;
      cur.is_sandbox = false;
      cur.original_purchase_date = buy;
      cur.period_type = "normal";
      cur.purchase_date = buy;
      cur.store = "app_store";
      cur.unsubscribe_detected_at = null;
      subs[sk[j]] = cur;
    }

    if (typeof sub.original_app_user_id !== "string" || !sub.original_app_user_id) {
      sub.original_app_user_id = "$RCAnonymousID:dazz";
    }
    if (!sub.first_seen) sub.first_seen = buy;
    sub.last_seen = isoOf(now);
    if (!sub.original_purchase_date) sub.original_purchase_date = buy;
    if (!sub.original_application_version) sub.original_application_version = "1.0";
    if (!sub.management_url) sub.management_url = "https://apps.apple.com/account/subscriptions";
    if (!sub.other_purchases || typeof sub.other_purchases !== "object") sub.other_purchases = {};
    if (!sub.non_subscriptions || typeof sub.non_subscriptions !== "object") sub.non_subscriptions = {};
    if (typeof obj.request_date !== "string") obj.request_date = isoOf(now);
    if (typeof obj.request_date_ms !== "number") obj.request_date_ms = now;
    return true;
  }

  // ---------- 自有接口兜底 ----------
  function pricedObject(node) {
    var hasPrice = false, hasEnt = false;
    for (var k in node) {
      if (!Object.prototype.hasOwnProperty.call(node, k)) continue;
      if (hasKey(PRICE_KEYS, k)) hasPrice = true;
      if (hasKey(BOOL_TRUE, k) || hasKey(TIME_KEYS, k)) hasEnt = true;
    }
    return hasPrice && !hasEnt;
  }

  function shape(node, ctx) {
    if (!node || typeof node !== "object" || isArr(node)) return;
    var skip = pricedObject(node);
    var strong = hasAny(node, BOOL_TRUE) || hasAny(node, BOOL_FALSE) ||
      (node.membership && typeof node.membership === "object") ||
      typeof node.contract_status !== "undefined" || typeof node.sub_type !== "undefined" ||
      typeof node.vip_type !== "undefined";

    for (var k in node) {
      if (!Object.prototype.hasOwnProperty.call(node, k)) continue;
      var v = node[k];
      if (v === null || typeof v === "object") continue;
      if (hasKey(BOOL_TRUE, k)) {
        if (skip) continue;
        node[k] = toBool(v, true);
      } else if (hasKey(BOOL_FALSE, k)) {
        if (skip) continue;
        node[k] = toBool(v, false);
      } else if (hasKey(TIME_KEYS, k)) {
        node[k] = rampTime(v, FAR);
      } else if (hasKey(INT_MIN, k)) {
        node[k] = rampInt(v, INT_MIN[k]);
      }
    }

    if (skip || !strong) return;
    if (hasKey(BOOL_TRUE, "is_vip") && typeof node.vip !== "undefined" && typeof node.is_vip === "undefined") {
      node.is_vip = toBool(node.vip, true);
    }
    if (typeof node.is_pro === "undefined" && (typeof node.vip_type !== "undefined" || typeof node.sub_type !== "undefined")) {
      node.is_pro = 1;
    }
  }

  function walk(node, depth) {
    if (!node || typeof node !== "object" || depth > 8) return;
    if (isArr(node)) {
      for (var i = 0; i < node.length; i++) walk(node[i], depth + 1);
      return;
    }
    shape(node, null);
    for (var k in node) {
      if (!Object.prototype.hasOwnProperty.call(node, k)) continue;
      var v = node[k];
      if (v === null || typeof v !== "object") continue;
      if (isArr(v)) {
        if (UNLOCK_FOREVER && ARRAY_KEYS.test(k) && v.length === 0) v.push(productFor(""));
        walk(v, depth + 1);
        continue;
      }
      walk(v, depth + 1);
    }
  }

  // ---------- 输出 ----------
  function notify(msg) {
    try { $notification.post("Dazz Pro", "", msg); } catch (e) {}
    try { console.log("[Dazz] " + msg); } catch (e2) {}
  }

  function pathOf(u) {
    var m = /^https?:\/\/([^\/]+)(\/[^?]*)?/i.exec(u || "");
    return m ? m[1] + (m[2] || "/") : String(u || "");
  }

  function keysOf(o, max) {
    var out = [], n = 0;
    for (var k in o) {
      if (!Object.prototype.hasOwnProperty.call(o, k)) continue;
      out.push(k);
      if (++n >= max) break;
    }
    return out.join(",");
  }

  function probe(obj) {
    var parts = [];
    parts.push(pathOf(url));
    parts.push("len=" + body.length + (isArr(obj) ? " array" : " object"));
    parts.push("keys: " + keysOf(obj, 16));
    var first = null;
    for (var k in obj) {
      if (!Object.prototype.hasOwnProperty.call(obj, k)) continue;
      if (obj[k] && typeof obj[k] === "object" && !isArr(obj[k])) { first = obj[k]; break; }
    }
    if (first) parts.push("node: " + keysOf(first, 16));
    notify(parts.join(" | "));
  }

  function emit(after, note) {
    var h = {};
    if ($response && $response.headers) {
      for (var k in $response.headers) {
        if (!Object.prototype.hasOwnProperty.call($response.headers, k)) continue;
        var lk = k.toLowerCase();
        if (lk === "etag" || lk === "if-none-match" || lk === "if-modified-since" || lk === "content-length") continue;
        h[k] = $response.headers[k];
      }
    }
    h["Cache-Control"] = "no-store";
    h["Pragma"] = "no-cache";
    if (DEBUG) notify("改写 " + note + " · " + pathOf(url));
    $done({ body: after, headers: h });
  }

  var url = ($request && ($request.url || $request.URL)) || "";
  var body = $response && typeof $response.body === "string" ? $response.body : null;
  if (body === null || body.length === 0 || body.length > MAX_BODY) { $done({}); return; }

  var head = body.replace(/^\uFEFF/, "").replace(/^\s+/, "").charAt(0);
  if (head !== "{" && head !== "[") { $done({}); return; }

  if (STRICT) {
    var ua = ($request && $request.headers && ($request.headers["User-Agent"] || $request.headers["user-agent"])) || "";
    if (!/dazz|camerafilm/i.test(ua)) { $done({}); return; }
  }

  var obj;
  try { obj = JSON.parse(body); } catch (e) { $done({}); return; }

  if (PROBE) { probe(obj); $done({}); return; }

  var note = "";
  if (DO_RECEIPT && isReceipt(url) && receiptUnlock(obj)) {
    note = "App Store 凭证";
  } else if (DO_RC && isRC(url) && rcUnlock(obj)) {
    note = "RevenueCat 订阅态";
  } else if (UNLOCK_PRO || UNLOCK_FOREVER) {
    walk(obj, 0);
    note = "会员字段";
  }

  var after = JSON.stringify(obj);
  if (after === body) { $done({}); return; }
  emit(after, note || "字段抬升");
})();
