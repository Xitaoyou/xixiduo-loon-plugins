// 夸克网盘 · 查看抓到的直链 / 探测到的路径
// Xitaoyou | xixiduo-loon-plugins / QuarkEnhance

// 不是复写脚本，手动跑：复制到本地 js 运行器，或在宿主里把 quark_links 读出来。
// 这里只把两个 persistentStore 键格式化成便于复制的一行一个 URL。

(function () {
  var links = [];
  var paths = {};
  try { links = JSON.parse($persistentStore.read("quark_links") || "[]"); } catch (e) { links = []; }
  try { paths = JSON.parse($persistentStore.read("quark_paths") || "{}"); } catch (e) { paths = {}; }

  var body = links.map(function (x) { return x.u; }).join("\n");
  var keys = Object.keys(paths);
  $notification.post("Quark导出", links.length + " 条直链 · " + keys.length + " 条路径",
    body ? body.substring(0, 120) : "还没抓到东西");
  console.log("=== links (" + links.length + ") ===");
  console.log(body || "(empty)");
  console.log("=== paths (" + keys.length + ") ===");
  console.log(keys.join("\n") || "(empty)");
  $done({});
})();
