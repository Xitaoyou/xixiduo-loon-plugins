#!/usr/bin/env node
// 校验 Wink 插件结构与规则命中：解析 [Script] 每条正则，对真实 URL 判断走哪条规则。
const fs = require("fs");
const path = require("path");

function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "plugins", "Wink_VIP.plugin"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.dirname(start);
}
const ROOT = process.env.WINK_REPO_ROOT || findRoot(__dirname);
const file = path.join(ROOT, "plugins", "Wink_VIP.plugin");
const src = fs.readFileSync(file, "utf8");

const sections = {};
let cur = null;
for (const line of src.split(/\r?\n/)) {
  const m = line.match(/^\[(.+)\]$/);
  if (m) { cur = m[1]; sections[cur] = sections[cur] || []; continue; }
  if (cur && line.trim() && !line.trim().startsWith("#")) sections[cur].push(line.trim());
}

let fail = 0;
function ok(name, cond, extra) {
  if (cond) console.log("  PASS " + name);
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

console.log("1. 结构");
ok("[Argument] 存在", Array.isArray(sections["Argument"]));
ok("[Script] 存在", Array.isArray(sections["Script"]));
ok("[MitM] 存在", Array.isArray(sections["MitM"]));
ok("头部有 #!name", /^#!name=/m.test(src));
ok("头部有 #!loon_version", /^#!loon_version=/m.test(src));
ok("头部有 #!homepage", /^#!homepage=/m.test(src));

const argLines = sections["Argument"] || [];
const argNames = argLines.map(l => l.split("=")[0].trim());
ok("7 个开关", argNames.length === 7, argNames.join(","));
ok("开关顺序与脚本 ORDER 一致",
  argNames.join(",") === "unlockVip,rewritePurchase,modifyProfile,strictAppOnly,farFutureTime,probeMode,debugMode",
  argNames.join(","));
ok("switch 项形如 name=switch, a, b", argLines.filter(l => l.includes("=switch")).every(l => /^\w+=switch,\s*(true|false),\s*(true|false),/.test(l)));
ok("input 项有默认值", argLines.filter(l => l.includes("=input")).every(l => /^\w+=input,\s*\S/.test(l)));
ok("每项都有 tag 与 desc", argLines.every(l => /tag=/.test(l) && /desc=/.test(l)));

console.log("2. 规则");
const rules = sections["Script"] || [];
ok("3 条 response 规则", rules.length === 3, String(rules.length));
const parsed = rules.map(r => {
  const re = r.match(/~=\s*\/(.*)\/i/);
  const scriptUrl = (r.match(/script\("([^"]+)"/) || [])[1];
  const argBlob = (r.match(/script\("[^"]+",\s*\{(.*?)\}\s*\)/) || [])[1];
  const tag = (r.match(/tag="([^"]+)"/) || [])[1];
  return {
    regex: re ? new RegExp(re[1], "i") : null,
    scriptUrl,
    argNames: argBlob ? argBlob.replace(/[$${}\s]/g, "").split(",") : null,
    tag,
    hasBody: /requires_body=true/.test(r)
  };
});
ok("每条都有正则", parsed.every(x => !!x.regex));
ok("每条都有脚本地址", parsed.every(x => /^https:\/\//.test(x.scriptUrl || "")));
ok("每条都 requires_body", parsed.every(x => x.hasBody));
ok("每条都有 tag", parsed.every(x => !!x.tag));

const mainRules = parsed.filter(x => (x.scriptUrl || "").endsWith("vip.js"));
const probeRule = parsed.find(x => (x.scriptUrl || "").endsWith("probe.js"));
ok("vip.js 规则 2 条", mainRules.length === 2, String(mainRules.length));
ok("probe.js 规则 1 条", !!probeRule);
ok("vip.js 参数 7 个", mainRules.every(x => x.argNames && x.argNames.length === 7), mainRules.map(x => (x.argNames || []).length).join(","));
ok("参数顺序与 [Argument] 一致", mainRules.every(x => (x.argNames || []).join(",") === argNames.join(",")));
ok("probe 规则受 probeMode 约束", /\$\{probeMode\} == true &&/.test(rules.find(r => r.includes("probe.js")) || ""));
ok("改写规则受 probeMode == false 约束", rules.filter(r => r.includes("vip.js")).every(r => /\$\{probeMode\} == false &&/.test(r)));

console.log("3. 命中测试");
const cases = [
  ["https://api-sub.meitu.com/v2/user/vip_info_by_group.json?app=wink", "Wink 会员态"],
  ["https://api-sub.meitu.com/v2/entrance/products_by_biz_code.json?sig=1", "Wink 会员态"],
  ["https://api-sub.meitu.com/v2/user/vip.json", "Wink 会员态"],
  ["https://api-winkcut.meitu.com/user/show.json", "Wink 会员态"],
  ["https://h5api-winkcut.meitu.com/activity/ai_cartoon.json", "Wink H5·账号"],
  ["https://api.account.meitu.com/users/show_current.json", "Wink H5·账号"],
  ["https://api-sub.meitu.com.evil.cn/v2/user/vip_info_by_group.json", null],
  ["https://api-subxmeitu.com/v2/user/vip_info_by_group.json", null],
  ["https://api.xiuxiu.meitu.com/v2/user/vip.json", null],
  ["https://example.com/v2/user/vip_info_by_group.json", null]
];
for (const [url, want] of cases) {
  const hit = mainRules.find(x => x.regex.test(url));
  const got = hit ? hit.tag : null;
  ok(url.replace(/^https:\/\//, "").slice(0, 58) + " -> " + (got || "放行"), got === want, "want=" + want + " got=" + got);
}

console.log("4. MitM 覆盖全部规则域名");
const mitm = (sections["MitM"] || []).join(" ");
["api-sub.meitu.com", "api-winkcut.meitu.com", "h5api-winkcut.meitu.com", "api.account.meitu.com"]
  .forEach(h => ok("MitM 含 " + h, mitm.indexOf(h) >= 0));

console.log("5. 语法卫生");
const body = rules.join("\n");
ok("无全角括号", !/[（）]/.test(body));
ok("无反引号", body.indexOf(String.fromCharCode(96)) < 0);
ok("每条规则以 response if 开头", rules.every(r => r.indexOf("response if ") === 0));
ok("Argument 无重复键", new Set(argNames).size === argNames.length);
ok("无 CRLF", src.indexOf("\r") < 0);
ok("无 BOM", src.charCodeAt(0) !== 0xfeff);

console.log("\n" + (fail ? fail + " failed" : "all checks passed"));
process.exit(fail ? 1 : 0);
