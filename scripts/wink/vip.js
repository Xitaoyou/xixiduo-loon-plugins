/*
 * Wink VIP · 会员态改写（Loon 版）
 *
 * 来自 K4Z3X0R/NguyenNgocAnhTu 的 Module/js/Wink.js，重写要点：
 *   - 原脚本把整个 data 换成写死的对象，服务端其它字段全丢；新版客户端读到缺字段会走异常分支。
 *   - 原脚本只认 ^https?://api-sub\.meitu\.com/.*vip，Wink 3.x 换成了 vip_info_by_group / products_by_biz_code
 *     等具体路径，正则还能命中但改的位置不对，表现就是「装了没反应」。
 *   - 这一版按响应里出现哪些键判断是不是权益对象，只抬升已知字段，其余原样保留，值的类型跟着原值走
 *     （数字还是数字、字符串还是字符串），避免客户端 JSON 解析或类型断言崩掉。
 */
(function () {
  var ORDER = ["unlockVip", "rewritePurchase", "modifyProfile", "strictAppOnly", "farFutureTime", "probeMode", "debugMode"];

  var BOOL_TRUE = {
    is_vip: 1, use_vip: 1, vip: 1, is_vip_user: 1, is_svip: 1, is_premium: 1, svip: 1,
    is_vip_member: 1, is_member: 1, is_vip_account: 1, can_use_vip: 1, vip_valid: 1,
    have_valid_contract: 1, has_valid_contract: 1, valid_contract: 1, is_contract_valid: 1,
    is_valid_user: 1, is_subscribed: 1, subscribed: 1, is_forever_vip: 1, show_renew_flag: 1
  };

  var BOOL_FALSE = {
    in_trial_period: 1, is_trial: 1, is_trial_user: 1, is_expired: 1, expired: 1,
    need_pay: 1, need_purchase: 1, need_buy: 1, need_renew: 1, show_buy: 1, show_purchase: 1
  };

  var INT_MIN = {
    account_type: 1, sub_type: 2, active_sub_type: 2, derive_type: 1, period_type: 1,
    contract_status: 1, limit_type: 1, active_promotion_status: 2, pay_status: 1
  };

  // 资料页字段：和会员接口里的同名字段语义不同，只在「资料页会员标识」开关打开时处理
  var PROFILE_KEYS = { vip_type: 1, vip_status: 1, vip_mode: 2, vip_level: 9, level: 9, blue_v_status: 1, red_v_status: 1 };

  var TIME_KEYS = {
    valid_time: 1, invalid_time: 1, in_valid_time: 1, expire_time: 1, expiry: 1, expire: 1,
    expire_at: 1, expire_date: 1, expired_at: 1, end_time: 1, valid_until: 1,
    current_order_invalid_time: 1, trial_period_invalid_time: 1, sub_expire_time: 1,
    vip_expire_time: 1, member_expire_time: 1, subscription_end_time: 1, contract_end_time: 1,
    next_expire_time: 1, renew_time: 1
  };

  var PROD_ARRAYS = { products: 1, product_list: 1, entrance_products: 1, goods_list: 1, skus: 1, vip_products: 1 };

  var logs = [];
  function log(s) { logs.push(String(s)); }

  function raw(name) {
    var a = typeof $argument !== "undefined" ? $argument : undefined;
    var v;
    if (Array.isArray(a)) {
      var i = ORDER.indexOf(name);
      v = i >= 0 ? a[i] : undefined;
    } else if (a && typeof a === "object") {
      v = a[name];
    } else if (typeof a === "string" && a) {
      try { v = JSON.parse(a)[name]; } catch (e) { v = undefined; }
    }
    if (v === undefined || v === null || v === "") {
      try { v = $persistentStore.read("wink_" + name); } catch (e) {}
    }
    return v;
  }

  function flag(name, def) {
    var v = raw(name);
    if (v === undefined || v === null || v === "") return def;
    if (typeof v === "boolean") return v;
    var s = String(v).trim().toLowerCase();
    if (s === "true" || s === "1" || s === "on" || s === "yes") return true;
    if (s === "false" || s === "0" || s === "off" || s === "no") return false;
    return def;
  }

  function num(name, def) {
    var v = raw(name);
    var n = Number(v);
    return isFinite(n) && n > 0 ? n : def;
  }

  var FAR = Math.floor(num("farFutureTime", 32495529599000));
  var DO_UNLOCK = flag("unlockVip", true);
  var DO_PURCHASE = flag("rewritePurchase", true);
  var DO_PROFILE = flag("modifyProfile", false);
  var STRICT = flag("strictAppOnly", false);
  var PROBE = flag("probeMode", false);
  var DEBUG = flag("debugMode", false);

  var stats = { ent: 0, bool: 0, time: 0, int: 0, prod: 0, prof: 0 };

  function lc(k) { return String(k).toLowerCase(); }

  function pathOf(url) {
    var m = String(url).match(/^https?:\/\/([^\/?#]+)([^?#]*)/i);
    return m ? m[1] + (m[2] || "/") : String(url);
  }

  function notify(title, msg) {
    try {
      if (typeof $notification !== "undefined" && $notification && $notification.post) $notification.post(title, "", msg);
    } catch (e) {}
  }

  function toBool(v, target) {
    if (typeof v === "boolean") return target ? true : false;
    if (typeof v === "number") return target ? 1 : 0;
    if (typeof v === "string") {
      var s = v.trim().toLowerCase();
      if (s === "true" || s === "false") return target ? "true" : "false";
      if (s === "1" || s === "0") return target ? "1" : "0";
      if (s === "") return v;
      if (/^\d+$/.test(s)) return target ? "1" : "0";
      return v;
    }
    return v;
  }

  function rampInt(v, min) {
    if (typeof v === "number") return v < min ? min : v;
    if (typeof v === "string" && /^-?\d+$/.test(v.trim())) {
      var n = parseInt(v.trim(), 10);
      return n < min ? String(min) : v;
    }
    return v;
  }

  function rampTime(v, farMs) {
    if (typeof v === "number") {
      var nt = v === 0 ? farMs : (v > 1e11 ? farMs : (v > 1e8 ? Math.floor(farMs / 1000) : farMs));
      return v < nt ? nt : v;
    }
    if (typeof v === "string") {
      var s = v.trim();
      if (s === "") return String(farMs);
      if (/^\d+$/.test(s)) {
        var n = parseInt(s, 10);
        var target = n === 0 ? farMs : (n > 1e11 ? farMs : (n > 1e8 ? Math.floor(farMs / 1000) : farMs));
        return n < target ? String(target) : v;
      }
      return v;
    }
    return v;
  }

  function shapeValue(k, v) {
    var key = lc(k);
    if (PROFILE_KEYS[key] !== undefined) return v;
    if (TIME_KEYS[key]) {
      var t = rampTime(v, FAR);
      if (t !== v) stats.time++;
      return t;
    }
    if (BOOL_TRUE[key]) {
      var b = toBool(v, true);
      if (b !== v) stats.bool++;
      return b;
    }
    if (BOOL_FALSE[key]) {
      var f = toBool(v, false);
      if (f !== v) stats.bool++;
      return f;
    }
    if (INT_MIN[key] !== undefined) {
      var n = rampInt(v, INT_MIN[key]);
      if (n !== v) stats.int++;
      return n;
    }
    return v;
  }

  function isEntitlementKey(k) {
    var key = lc(k);
    if (BOOL_TRUE[key] || BOOL_FALSE[key] || TIME_KEYS[key] || INT_MIN[key] !== undefined) return true;
    return /^(vip|svip|member|membership|subscription|contract)/.test(key);
  }

  function hasAny(node, map) {
    var ks = Object.keys(node);
    for (var i = 0; i < ks.length; i++) if (map[lc(ks[i])] !== undefined) return true;
    return false;
  }

  function shape(node) {
    var ks = Object.keys(node);
    for (var i = 0; i < ks.length; i++) {
      var k = ks[i];
      var v = node[k];
      if (v !== null && typeof v === "object") continue;
      var nv = shapeValue(k, v);
      if (nv !== v) node[k] = nv;
    }
    // 只有「明显是权益对象」的节点才补字段，避免给只带 end_time 之类时间键的无关对象凭空塞 is_vip
    var strong = hasAny(node, BOOL_TRUE) || hasAny(node, BOOL_FALSE) ||
      (node.membership && typeof node.membership === "object") ||
      node.contract_status !== undefined || node.sub_type !== undefined || node.derive_type !== undefined;
    if (strong && !hasAny(node, BOOL_TRUE)) {
      node.is_vip = true;
      node.use_vip = true;
      node.have_valid_contract = true;
      stats.bool += 3;
    }
    if (!hasAny(node, TIME_KEYS)) {
      node.invalid_time = FAR;
      stats.time++;
    }
    var m = node.membership;
    if (m && typeof m === "object" && !Array.isArray(m)) {
      if (typeof m.level === "number" && m.level < 9) m.level = 9;
      if (typeof m.level_name === "string") m.level_name = "超级会员";
      if (m.display_name === undefined || m.display_name === "") m.display_name = "Wink会员";
      if (m.id === undefined) m.id = "4";
    }
    stats.ent++;
  }

  function walk(node) {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      for (var i = 0; i < node.length; i++) walk(node[i]);
      return;
    }
    var ks = Object.keys(node);
    var ent = hasAny(node, BOOL_TRUE) || hasAny(node, TIME_KEYS);
    if (!ent) {
      for (var j = 0; j < ks.length; j++) {
        var cv = node[ks[j]];
        if (!cv || typeof cv !== "object" || Array.isArray(cv)) continue;
        if (/^(vip|svip|member|membership|subscription|contract)/.test(lc(ks[j]))) { ent = true; break; }
      }
    }
    if (ent) shape(node);
    for (var q = 0; q < ks.length; q++) walk(node[ks[q]]);
  }

  function products(node) {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      for (var i = 0; i < node.length; i++) products(node[i]);
      return;
    }
    var ks = Object.keys(node);
    for (var j = 0; j < ks.length; j++) {
      var k = ks[j];
      var v = node[k];
      if (Array.isArray(v) && PROD_ARRAYS[lc(k)]) {
        for (var p = 0; p < v.length; p++) {
          var item = v[p];
          if (!item || typeof item !== "object" || Array.isArray(item)) continue;
          var ik = Object.keys(item);
          var hit = false;
          for (var x = 0; x < ik.length; x++) {
            var key = lc(ik[x]);
            if (key === "product_buy_flag" || key === "buy_flag" || key === "purchased" ||
                key === "is_purchased" || key === "bought" || key === "is_bought") {
              var nv = toBool(item[ik[x]], true);
              if (nv !== item[ik[x]]) { item[ik[x]] = nv; hit = true; }
            }
          }
          if (hit) stats.prod++;
        }
      }
      products(v);
    }
  }

  function profile(node) {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      for (var i = 0; i < node.length; i++) profile(node[i]);
      return;
    }
    var ks = Object.keys(node);
    for (var j = 0; j < ks.length; j++) {
      var k = ks[j];
      var v = node[k];
      var key = lc(k);
      if (v !== null && typeof v !== "object" && PROFILE_KEYS[key] !== undefined) {
        var nv = rampInt(v, PROFILE_KEYS[key]);
        if (nv !== v) { node[k] = nv; stats.prof++; }
      }
      if (v && typeof v === "object") profile(v);
    }
  }

  function skeleton(node, depth) {
    if (node === null) return "null";
    if (typeof node !== "object") return typeof node;
    if (depth > 2) return "...";
    if (Array.isArray(node)) return "[" + (node.length ? skeleton(node[0], depth + 1) : "") + "]x" + node.length;
    var ks = Object.keys(node);
    var parts = [];
    for (var i = 0; i < ks.length && i < 14; i++) parts.push(ks[i] + ":" + skeleton(node[ks[i]], depth + 1));
    return "{" + parts.join(",") + (ks.length > 14 ? ",..." : "") + "}";
  }

  function emit(bodyOut) {
    var out = { body: bodyOut };
    try {
      var h = $response && $response.headers;
      if (h) {
        var copy = {};
        for (var k in h) if (Object.prototype.hasOwnProperty.call(h, k)) copy[k] = h[k];
        copy["Cache-Control"] = "no-store, no-cache, must-revalidate";
        copy["Pragma"] = "no-cache";
        delete copy["ETag"]; delete copy["etag"]; delete copy["Etag"];
        delete copy["If-None-Match"]; delete copy["if-none-match"];
        out.headers = copy;
      }
    } catch (e) {}
    $done(out);
  }

  function main() {
    var url = ($request && $request.url) || "";
    var body = ($response && $response.body) || "";

    if (!body || typeof body !== "string") { $done({}); return; }
    if (body.length > 512 * 1024) {
      if (DEBUG) notify("Wink VIP", "跳过超长响应 " + pathOf(url) + " len=" + body.length);
      $done({});
      return;
    }
    var head = body.replace(/^\uFEFF/, "").replace(/^\s+/, "").charAt(0);
    if (head !== "{" && head !== "[") { $done({}); return; }

    if (STRICT) {
      var ua = "";
      try {
        var hs = ($request && $request.headers) || {};
        ua = hs["User-Agent"] || hs["user-agent"] || "";
      } catch (e) {}
      if (!/wink/i.test(String(ua))) {
        if (DEBUG || PROBE) notify("Wink VIP", "跳过非 Wink 请求 " + pathOf(url) + " ua=" + String(ua).slice(0, 60));
        $done({});
        return;
      }
    }

    var obj;
    try { obj = JSON.parse(body); } catch (e) { $done({}); return; }
    if (!obj || typeof obj !== "object") { $done({}); return; }

    if (PROBE) {
      var sk = skeleton(obj, 0);
      var line = pathOf(url) + " " + sk;
      log(line);
      notify("Wink 探测", line.slice(0, 400));
      $done({});
      return;
    }

    var before = JSON.stringify(obj);
    if (DO_UNLOCK) walk(obj);
    if (DO_PURCHASE) products(obj);
    if (DO_PROFILE) profile(obj);
    var after = JSON.stringify(obj);

    if (after === before) {
      if (DEBUG) notify("Wink VIP", "未命中可改字段 " + pathOf(url));
      $done({});
      return;
    }

    if (DEBUG) {
      notify("Wink VIP", pathOf(url) + " 权益" + stats.ent + " 布尔" + stats.bool + " 时间" + stats.time + " 枚举" + stats.int + " 商品" + stats.prod + " 资料" + stats.prof);
    }
    emit(after);
  }

  try { main(); } catch (e) {
    if (DEBUG) notify("Wink VIP", "脚本异常 " + (e && e.message ? e.message : String(e)));
    $done({});
  }
})();
