// 123Pan iOS ad response cleaner; modifies only observed advertising fields.
// Maintainer: Xitaoyou. Account/VIP, transfer limits and user identity are untouched.
(function () {
  var original = $response.body;
  var url = ($request && $request.url) || "";
  var obj;
  try { obj = JSON.parse(original); } catch (e) { $done({body: original}); return; }
  if (!obj || typeof obj !== "object" || obj.code !== 0) { $done({body: original}); return; }
  var data = obj.data;
  var changed = false;
  function set(key, value) {
    if (data && Object.prototype.hasOwnProperty.call(data, key) && data[key] !== value) {
      data[key] = value; changed = true;
    }
  }
  if (/\/api\/config\/get(?:\?|$)/i.test(url)) {
    set("isInitAd", 0);
    ["isOpenSplash", "isOpenAbortAd", "isOpenDownloadAd", "isOpenMineAd", "isOpenUploadAd"].forEach(function (key) { set(key, false); });
    set("interstitialShowCount", 0);
    set("showCount", 0);
    if (data && Array.isArray(data.bannerList) && data.bannerList.length) {
      data.bannerList = []; changed = true;
    }
    if (data && data.preloadConfig && typeof data.preloadConfig === "object") {
      ["iosInter", "iosSplash", "androidInter", "androidSplash"].forEach(function (key) {
        if (Object.prototype.hasOwnProperty.call(data.preloadConfig, key) && data.preloadConfig[key] !== 0) {
          data.preloadConfig[key] = 0; changed = true;
        }
      });
    }
  } else if (/\/api\/app\/config\/get(?:\?|$)/i.test(url)) {
    set("isInitAd", 0);
  } else if (/\/api\/user\/info(?:\?|$)/i.test(url)) {
    set("IsShowAdvertisement", false);
  } else if (/\/api\/v2\/advert_resource\/get(?:\?|$)/i.test(url)) {
    if (data !== null && data !== undefined) { obj.data = null; changed = true; }
  } else if (/\/api\/taku\/ad\/config(?:\?|$)/i.test(url)) {
    set("ad_count", 0);
  }
  $done({body: changed ? JSON.stringify(obj) : original});
})();