// 芒果TV界面精简：仅改写抓包确认的开关和频道数据。
// Xitaoyou | iOS 9.4.6
(function () {
  var original = $response.body;
  var url = ($request && $request.url) || "";
  var keys = ["cleanAdConfig", "trimBottomTabs", "hideMangoCard", "hideAIChat", "trimTopTabs", "topChannels"];
  var options = {};
  var arg = typeof $argument === "undefined" ? null : $argument;
  if (Array.isArray(arg)) {
    arg.forEach(function (v, i) { if (keys[i]) options[keys[i]] = v; });
  } else if (arg && typeof arg === "object") {
    options = arg;
  } else if (typeof arg === "string") {
    try {
      var parsed = JSON.parse(arg);
      if (Array.isArray(parsed)) parsed.forEach(function (v, i) { if (keys[i]) options[keys[i]] = v; });
      else if (parsed && typeof parsed === "object") options = parsed;
    } catch (_) {}
  }
  function enabled(k) { return options[k] === true || String(options[k]).toLowerCase() === "true"; }
  var obj, changed = false;
  try { obj = JSON.parse(original); } catch (_) { $done({body: original}); return; }
  if (!obj || typeof obj !== "object" || !obj.data) { $done({body: original}); return; }

  function update(o, key, value) {
    if (o && Object.prototype.hasOwnProperty.call(o, key) && o[key] !== value) {
      o[key] = value;
      changed = true;
    }
  }
  // 某些配置字段是 JSON 字符串，必须保留原始类型，否则客户端可能无法解析。
  function patchConfig(data, key, callback) {
    if (!Object.prototype.hasOwnProperty.call(data, key)) return;
    var raw = data[key];
    var asString = typeof raw === "string";
    var parsed;
    try { parsed = asString ? JSON.parse(raw) : raw; } catch (_) { return; }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return;
    var before = JSON.stringify(parsed);
    callback(parsed);
    var after = JSON.stringify(parsed);
    if (before !== after) {
      data[key] = asString ? after : parsed;
      changed = true;
    }
  }

  if (/\/mobile\/config(?:\?|$)/i.test(url) && typeof obj.data === "object" && !Array.isArray(obj.data)) {
    var data = obj.data;
    if (enabled("cleanAdConfig")) {
      ["dc_adConfig", "relative_ads", "progress_bar_ad_switch", "playview_box_ad_switch"].forEach(function (k) { update(data, k, "0"); });
    }
    if (enabled("trimBottomTabs")) {
      // 关闭已知的视频、商城、大芒及短剧推广入口；不触碰首页、搜索、片库和我的。
      ["XmVideoB", "XmsellSwitch", "damang_tab", "damang_duanju_tab"].forEach(function (k) { update(data, k, "0"); });
      patchConfig(data, "new_homepage_switch", function (conf) { if (Object.prototype.hasOwnProperty.call(conf, "jbp")) conf.jbp = "0"; });
    }
    if (enabled("hideMangoCard")) {
      patchConfig(data, "pendantSwitch", function (conf) { if ("display" in conf) conf.display = 0; if ("entry" in conf) conf.entry = 0; });
      patchConfig(data, "mg_card_avatar_entry", function (conf) { if ("isOpen" in conf) conf.isOpen = 0; });
    }
    if (enabled("hideAIChat")) {
      update(data, "sayhi_entry_switch", "0");
      patchConfig(data, "mg_agent_switch", function (conf) {
        ["enable", "state", "mobile", "proactive", "bubbleInPlayer", "bubbleNotInPlayer", "dailyApprTimes", "maxApprTimes"].forEach(function (k) { if (k in conf) conf[k] = 0; });
      });
      patchConfig(data, "ai_mouthpiece_switch", function (conf) { if ("enabled" in conf) conf.enabled = 0; });
      patchConfig(data, "new_homepage_switch", function (conf) { if ("mg_agent_switch" in conf) conf.mg_agent_switch = "0"; });
    }
  } else if (/\/dynamic\/v1\/channel\/vrsList\//i.test(url) && enabled("trimTopTabs") && Array.isArray(obj.data)) {
    var input = typeof options.topChannels === "string" ? options.topChannels : "首页,电视剧,电影,综艺";
    var whitelist = input.split(/[,，]/).map(function (s) { return s.trim(); }).filter(Boolean);
    if (whitelist.indexOf("首页") < 0) whitelist.unshift("首页");
    var kept = obj.data.filter(function (item) {
      return item && (whitelist.indexOf(String(item.title || "")) >= 0 || String(item.vclassId) === "60");
    });
    if (kept.length > 0 && kept.length < obj.data.length) { obj.data = kept; changed = true; }
  }
  if (enabled("debugMode")) {
    console.log("[芒果TV] " + (/\/mobile\/config(?:\?|$)/i.test(url) ? "底部和浮窗" : "顶部频道") + "：" + (changed ? "已精简" : "未修改响应"));
  }
  $done({body: changed ? JSON.stringify(obj) : original});
})();
