#!/usr/bin/env node
// 校验 plugin 结构与规则命中：解析 [Script] 每行正则，对真实 URL 判断走哪条规则。
const fs = require("fs");
const path = require("path");

// 兼容两种目录：本地包（qingtingloon/plugins）与仓库（plugins/）。向上找含 plugins 的目录。
function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "plugins", "QingTing_English_VIP.plugin"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.dirname(start);
}
const ROOT = process.env.QT_REPO_ROOT || findRoot(__dirname);
const file = path.join(ROOT, "plugins", "QingTing_English_VIP.plugin");
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
const argLines = sections["Argument"] || [];
const argNames = argLines.map(l => l.split("=")[0]);
ok("8 个开关齐全", argNames.length === 8, argNames.join(","));
ok("开关顺序与脚本 ORDER 一致",
  argNames.join(",") === "modifyPrivileges,downgradeV3,modifyPurchase,modifyPromote,quota,expireAt,probeMode,debugMode",
  argNames.join(","));
ok("input 项有默认值", argLines.filter(l => l.indexOf("=input") === 0).every(l => /^[^=]+=input,\s*\S/.test(l)));

console.log("2. 规则");
const rules = sections["Script"] || [];
ok("3 条 script 规则", rules.length === 3, String(rules.length));
const parsed = rules.map(r => {
  const re = r.match(/~=\s*\/(.*)\/i/);
  const scriptUrl = r.match(/script\("([^"]+)"/)[1];
  const argBlob = (r.match(/script\("[^"]+",\s*\{(.*?)\}\s*\)/) || [null, null])[1];
  const tag = (r.match(/tag="([^"]+)"/) || [])[1];
  return {
    regex: re && new RegExp(re[1], "i"),
    scriptUrl,
    argNames: argBlob ? argBlob.replace(/[${}\s]/g, "").split(",") : null,
    tag,
    hasBody: /requires_body=true/.test(r)
  };
});
ok("每条都 requires_body", parsed.every(x => x.hasBody));
ok("每条都有 tag", parsed.every(x => !!x.tag));
const vipRules = parsed.filter(x => x.scriptUrl.endsWith("vip.js"));
ok("vip.js 规则 2 条（按域名）", vipRules.length === 2, String(vipRules.length));
ok("vip.js 参数 8 个", vipRules.every(x => x.argNames && x.argNames.length === 8), vipRules.map(x => x.argNames && x.argNames.length).join(","));
ok("vip.js 参数名与 [Argument] 顺序一致",
  vipRules.every(x => x.argNames && x.argNames.join(",") === argNames.join(",")),
  (vipRules[0].argNames || []).join(","));

console.log("3. 命中测试");
const cases = [
  ["https://api.beingfine.cn/v3/2/report/launch/1795604950977", "域名改写·beingfine"],
  ["https://sapi.beingfine.cn/v1/UserLaunchAppReport?app_id=1&udid=x", "域名改写·beingfine"],
  ["https://api.beingfine.cn/v3/qt/app-configs/1795604950977", "域名改写·beingfine"],
  ["https://api.beingfine.cn/v3/qt/episode/command/1795604950977", "域名改写·beingfine"],
  ["https://learnywhere.cn/api/qt/buy/vip/purchase2?sid=1&feat=2", "域名改写·learnywhere"],
  ["https://learnywhere.cn/api/buy/promote/in-duration?sid=1&feat=2&promote=1&purchase_page=1", "域名改写·learnywhere"],
  ["https://learnywhere.cn/le/buy/member?sid=1", "域名改写·learnywhere"],
  ["https://api.beingfine.cn/v1/LE_GetMySubscribedCourses", "域名改写·beingfine"],
  ["https://api.example-files.cn/v3/qt/app-configs/1", null],
  ["https://learnying.com/api/qt/buy/vip/purchase2", null],
  ["https://api.beingfine.cn.evil.cn/v3/qt/app-configs/1", null]
];
const mainRules = parsed.filter(x => !x.scriptUrl.endsWith("probe.js"));
for (const [url, want] of cases) {
  const hit = mainRules.find(x => x.regex.test(url));
  const got = hit ? hit.tag : null;
  ok(url.replace(/^https:\/\//, "").substring(0, 56) + " -> " + (got || "放行"), got === want, "want=" + want + " got=" + got);
}

console.log("4. MitM 覆盖全部规则域名");
const mitm = (sections["MitM"] || []).join(" ");
["api.beingfine.cn", "sapi.beingfine.cn", "learnywhere.cn"].forEach(h => ok("MitM 含 " + h, mitm.indexOf(h) >= 0));

console.log("5. 语法卫生");
ok("规则无全角括号", !/[（）]/.test(rules.join("")));
ok("规则无反引号", rules.join("").indexOf(String.fromCharCode(96)) < 0);
ok("每条规则以 response if 开头", rules.every(r => r.indexOf("response if ") === 0));
ok("Argument 无重复键", new Set(argNames).size === argNames.length);
ok("probe 规则受 probeMode 约束", /\$\{probeMode\} == true &&/.test(rules[rules.length - 1]));

console.log("\n" + (fail ? fail + " failed" : "all checks passed"));
process.exit(fail ? 1 : 0);
