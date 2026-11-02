/*
 * Bilibili home tabs for Loon (standalone, conservative JSON edit).
 * Based on upstream tab-removal behavior; adapted for user-selectable switches.
 * No subtitle, player, or comment endpoints are touched by this file.
 */
(function () {
  "use strict";
  var keys = [
    "customizeHomeTabs", "homeTopTabOrder", "hideTopGameCenter",
    "hideBottomPublish", "hideBottomMall", "hideBottomDynamic",
    "hideBottomMessages", "hideBottomLive", "hideTopActivity"
  ];
  var defaults = {
    customizeHomeTabs: false,
    homeTopTabOrder: "全部",
    hideTopGameCenter: true,
    hideBottomPublish: true,
    hideBottomMall: true,
    hideBottomDynamic: false,
    hideBottomMessages: false,
    hideBottomLive: false,
    hideTopActivity: true
  };
  function args() {
    var a = typeof $argument === "undefined" ? null : $argument;
    if (Array.isArray(a)) {
      var out = Object.assign({}, defaults);
      a.forEach(function (v, i) { if (keys[i]) out[keys[i]] = v; });
      return out;
    }
    if (a && typeof a === "object") return Object.assign({}, defaults, a);
    if (typeof a === "string") {
      try {
        var parsed = JSON.parse(a);
        if (Array.isArray(parsed)) {
          var out2 = Object.assign({}, defaults);
          parsed.forEach(function (v, i) { if (keys[i]) out2[keys[i]] = v; });
          return out2;
        }
        if (parsed && typeof parsed === "object") return Object.assign({}, defaults, parsed);
      } catch (ignore) {}
    }
    return defaults;
  }
  function yes(v) { return v === true || String(v).toLowerCase() === "true"; }
  function normal(v) { return String(v || "").replace(/\s+/g, "").toLowerCase(); }
  function match(item, names, ids, schemes) {
    var name = normal(item && item.name);
    var tab = normal(item && item.tab_id);
    var uri = normal(item && item.uri);
    return names.some(function (n) { return name === n || tab === n || tab === n + "bottom" || tab === n + "top"; }) ||
      ids.some(function (id) { return Number(item.id) === id; }) ||
      schemes.some(function (s) { return uri.indexOf(s) === 0; });
  }
  function positions(a) { a.forEach(function (e, i) { e.pos = i + 1; }); return a; }
  function clean(items, predicate) {
    if (!Array.isArray(items)) return items;
    var selected = items.filter(function (x) { return !predicate(x); });
    return selected.length ? positions(selected) : items;
  }
  try {
    var obj = JSON.parse($response.body || "{}");
    var config = args();
    var data = obj && obj.data;
    if (!data || typeof data !== "object") { $done({}); return; }

    if (Array.isArray(data.top)) {
      data.top = clean(data.top, function (x) {
        return (yes(config.hideTopGameCenter) &&
          match(x, ["游戏中心"], [], ["bilibili://game/"])) ||
          (yes(config.hideTopActivity) && (
            x.is_ad === true || x.is_ad === 1 ||
            (x.ad_info && typeof x.ad_info === "object" && Object.keys(x.ad_info).length > 0)
          ));
      });
    }
    if (Array.isArray(data.bottom)) {
      data.bottom = clean(data.bottom, function (x) {
        return (yes(config.hideBottomPublish) && match(x, ["发布", "投稿", "拍摄"], [], ["bilibili://uper/user_center/archive_selection"])) ||
          (yes(config.hideBottomMall) && match(x, ["会员购", "会员购bottom"], [], ["bilibili://mall/"])) ||
          (yes(config.hideBottomDynamic) && match(x, ["动态", "关注"], [179], ["bilibili://following/home/"])) ||
          (yes(config.hideBottomMessages) && match(x, ["消息"], [176], ["bilibili://link/im_home"])) ||
          (yes(config.hideBottomLive) && match(x, ["直播"], [731], ["bilibili://live/home"]));
      });
    }
    if (yes(config.customizeHomeTabs) && Array.isArray(data.tab)) {
      var raw = String(config.homeTopTabOrder || "全部").trim();
      if (raw && raw !== "全部" && raw.toLowerCase() !== "all") {
        var labels = raw.split(/[|,，、]/).map(normal).filter(Boolean);
        var ordered = [];
        var used = {};
        labels.forEach(function (label) {
          data.tab.forEach(function (entry, i) {
            if (!used[i] && normal(entry.name) === label) {
              used[i] = true; ordered.push(entry);
            }
          });
        });
        // Leave the original tabs untouched if an outdated custom list matches none.
        if (ordered.length) data.tab = positions(ordered);
      }
    }
    $done({body: JSON.stringify(obj)});
  } catch (error) {
    console.log("[Bilibili Home Tabs] Keeping original response: " + String(error));
    $done({});
  }
})();