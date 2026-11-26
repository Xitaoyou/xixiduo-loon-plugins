// Dazz · 接口探测（只读）
// 打开「接口探测」后重开 App，通知里会给出域名、路径、body 长度与前两层字段名。
(function () {
  "use strict";

  function pathOf(u) {
    var m = /^https?:\/\/([^\/]+)(\/[^?]*)?/i.exec(u || "");
    return m ? m[1] + (m[2] || "/") : String(u || "");
  }

  function isArr(v) { return Object.prototype.toString.call(v) === "[object Array]"; }

  function keysOf(o, max) {
    var out = [], n = 0;
    for (var k in o) {
      if (!Object.prototype.hasOwnProperty.call(o, k)) continue;
      var v = o[k];
      var t = v === null ? "null" : (isArr(v) ? "array" : typeof v);
      out.push(k + ":" + t);
      if (++n >= max) break;
    }
    return out.join(",");
  }

  var url = ($request && ($request.url || $request.URL)) || "";
  var body = $response && typeof $response.body === "string" ? $response.body : "";
  var lines = ["[DazzProbe] " + pathOf(url) + " · " + body.length + "B"];

  var head = body.replace(/^\uFEFF/, "").replace(/^\s+/, "").charAt(0);
  if (head === "{" || head === "[") {
    var obj = null;
    try { obj = JSON.parse(body); } catch (e) { obj = null; }
    if (obj && typeof obj === "object") {
      lines.push((isArr(obj) ? "array[" + obj.length + "]" : "object") + " {" + keysOf(obj, 18) + "}");
      var first = null, fk = "";
      for (var k in obj) {
        if (!Object.prototype.hasOwnProperty.call(obj, k)) continue;
        if (obj[k] && typeof obj[k] === "object" && !isArr(obj[k])) { first = obj[k]; fk = k; break; }
      }
      if (first) lines.push(fk + " {" + keysOf(first, 18) + "}");
      if (isArr(obj) && obj.length && obj[0] && typeof obj[0] === "object") {
        lines.push("item0 {" + keysOf(obj[0], 18) + "}");
      }
    } else {
      lines.push("JSON 解析失败");
    }
  } else {
    lines.push("非 JSON（跳过）");
  }

  var ua = ($request && $request.headers && ($request.headers["User-Agent"] || $request.headers["user-agent"])) || "";
  if (ua) lines.push("UA: " + ua.slice(0, 80));

  var msg = lines.join("\n");
  try { console.log(msg); } catch (e) {}
  try { $notification.post("Dazz 探测", "", lines.slice(0, 4).join(" | ")); } catch (e2) {}
  $done({});
})();
