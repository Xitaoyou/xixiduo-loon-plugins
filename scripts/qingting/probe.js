/*
 * 轻听英语 · 接口探测（排障用）
 * Xitaoyou | xixiduo-loon-plugins
 *
 * 只读：不改响应，只把命中的接口形态发到通知/日志，用来在 App 改版后找回路径与字段。
 * 输出永远不含 token、secret、guest、cookie 或密文原文。
 */
(function () {
  "use strict";

  function shortUrl(u) {
    return String(u || "").replace(/^https?:\/\//, "").replace(/\?.*$/, "").substring(0, 96);
  }

  var url = String(($request && $request.url) || "");
  var method = String(($request && $request.method) || "GET").toUpperCase();
  var info = { m: method, u: shortUrl(url) };

  try {
    var raw = ($response && typeof $response.body === "string") ? $response.body : "";
    if (!raw) {
      info.body = "empty";
    } else {
      var data = JSON.parse(raw);
      info.json = true;
      info.enc = data.data_encrypted === undefined ? "-" : data.data_encrypted;
      var b = data.data_body;
      info.bodyType = b === null ? "null" : Array.isArray(b) ? "array" : typeof b;
      if (b && typeof b === "object") {
        info.bodyKeys = Object.keys(b).slice(0, 12).join(",");
        if (b.privileges && typeof b.privileges === "object") {
          info.privKeys = Object.keys(b.privileges).slice(0, 16).join(",");
        }
        if (b.auth && typeof b.auth === "object") info.authKeys = Object.keys(b.auth).join(",");
        if (b.account && typeof b.account === "object") info.acctKeys = Object.keys(b.account).join(",");
      } else if (typeof b === "string") {
        info.bodyLen = b.length;
        if (b.charAt(0) === "{") {
          try {
            var p = JSON.parse(b);
            info.innerKeys = Object.keys(p).slice(0, 12).join(",");
            if (p.privileges) info.innerPriv = Object.keys(p.privileges).slice(0, 16).join(",");
          } catch (e) {}
        }
      }
      if (data.v3_security && typeof data.v3_security === "object") {
        info.v3sec = Object.keys(data.v3_security).join(","); // 只记字段名，不记值
      }
      info.top = Object.keys(data).slice(0, 12).join(",");
    }
  } catch (e) {
    info.json = false;
  }

  var line = JSON.stringify(info);
  try { console.log("[QT probe] " + line); } catch (e) {}
  try {
    if (String($persistentStore.read("qt_probeSilent") || "false") !== "true") {
      $notification.post("轻听英语探测", shortUrl(url), line);
    }
  } catch (e) {}

  $done({});
})();
