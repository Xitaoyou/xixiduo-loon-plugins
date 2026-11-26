/*
 * Wink 接口探测（只读）
 * 排障用：把命中接口的路径、响应骨架、会员相关键打出来，不改任何字节。
 * 用来在 Wink 升级后确认新字段名，再回填 scripts/wink/vip.js 的字段表。
 */
(function () {
  function pathOf(url) {
    var m = String(url).match(/^https?:\/\/([^\/?#]+)([^?#]*)/i);
    return m ? m[1] + (m[2] || "/") : String(url);
  }

  function skeleton(node, depth) {
    if (node === null) return "null";
    if (typeof node !== "object") return typeof node + "=" + String(node).slice(0, 20);
    if (depth > 2) return "...";
    if (Array.isArray(node)) return "[" + (node.length ? skeleton(node[0], depth + 1) : "") + "]x" + node.length;
    var ks = Object.keys(node);
    var parts = [];
    for (var i = 0; i < ks.length && i < 16; i++) parts.push(ks[i] + ":" + skeleton(node[ks[i]], depth + 1));
    return "{" + parts.join(",") + (ks.length > 16 ? ",..." : "") + "}";
  }

  var url = ($request && $request.url) || "";
  var body = ($response && $response.body) || "";
  var line = pathOf(url) + " len=" + String(body).length;

  try {
    if (!body) { line += " body=empty"; }
    else {
      var obj = JSON.parse(body);
      line += " " + skeleton(obj, 0);
    }
  } catch (e) {
    line += " body=not-json head=" + String(body).slice(0, 60);
  }

  try { console.log("[WinkProbe] " + line); } catch (e) {}
  try {
    if (typeof $notification !== "undefined" && $notification && $notification.post) {
      $notification.post("Wink 探测", pathOf(url), line.slice(0, 600));
    }
  } catch (e) {}
  $done({});
})();
