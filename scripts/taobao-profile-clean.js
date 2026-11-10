/*
 * 淘宝个人页营销模块定向净化
 * 原开屏规则：可莉 / RuCu6；增强：西西多增强
 * 仅删除有明确文案标记的活动卡片和「飞猪」快捷入口；保留订单/购物车/普通商品。
 */
(function () {
  const body = $response && $response.body;
  if (typeof body !== "string" ||
      !/(狂欢最后|旅行节|旅游节|飞猪|shuang11qqlxjh_copy)/.test(body)) {
    $done({});
    return;
  }
  let data;
  try { data = JSON.parse(body); } catch (_) { $done({}); return; }

  const textKeys = [
    "title", "name", "label", "text", "mainTitle", "subTitle", "subtitle",
    "moduleTitle", "moduleName", "bannerTitle", "marketingTitle", "promotionTitle",
    "headerTitle", "displayName", "serviceName", "itemName", "shortTitle",
    "titleText", "jumpUrl", "linkUrl", "landingUrl", "url"
  ];
  const campaign = /(?:11[.\s]*11|双\s*11).{0,30}(?:狂欢最后|官方立减)|狂欢最后\s*[一二三四五六七八九十\d]+\s*天|飞猪.{0,14}(?:旅行节|旅游节)|shuang11qqlxjh_copy/i;
  let removed = 0;
  let changed = false;

  function matchText(value) {
    if (typeof value !== "string") return false;
    const normalized = value.replace(/<[^>]+>/g, "").trim();
    return normalized === "飞猪" || campaign.test(normalized);
  }
  function marked(obj) {
    if (!obj || typeof obj !== "object" || Array.isArray(obj)) return false;
    if (textKeys.some(key => matchText(obj[key]))) return true;
    // 营销卡片通常把标题包装在 data/model/content 中，最多检查一层。
    for (const key of ["data", "model", "content", "fields", "bizData"]) {
      let nested = obj[key];
      if (typeof nested === "string" && nested.charAt(0) === "{" && nested.length < 250000) {
        try { nested = JSON.parse(nested); } catch (_) { continue; }
      }
      if (nested && typeof nested === "object" && !Array.isArray(nested) &&
          textKeys.some(k => matchText(nested[k]))) return true;
    }
    return false;
  }
  function clean(value, depth) {
    if (depth > 32 || value == null) return value;
    if (Array.isArray(value)) {
      const result = [];
      for (const item of value) {
        if (marked(item)) { removed++; changed = true; continue; }
        result.push(clean(item, depth + 1));
      }
      return result;
    }
    if (typeof value === "object") {
      for (const key of Object.keys(value)) value[key] = clean(value[key], depth + 1);
      return value;
    }
    if (typeof value === "string" && value.length < 250000 &&
        /^[\s]*[\[{]/.test(value) &&
        /(狂欢最后|旅行节|旅游节|飞猪|shuang11qqlxjh_copy)/.test(value)) {
      try {
        const parsed = JSON.parse(value);
        const before = removed;
        const after = clean(parsed, depth + 1);
        if (removed > before) return JSON.stringify(after);
      } catch (_) { /* 保持原始字符串 */ }
    }
    return value;
  }
  const output = clean(data, 0);
  if (changed) {
    console.log("淘宝个人页净化：移除活动卡片/飞猪快捷入口 " + removed + " 项");
    $done({ body: JSON.stringify(output) });
  } else {
    $done({});
  }
})();
