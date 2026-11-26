#!/usr/bin/env node
// 校验 Dazz 插件结构与规则命中：解析 [Script] 每条正则，按 probeMode 状态判断走哪条规则。
const fs = require("fs");
const path = require("path");

function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "plugins", "Dazz_VIP.plugin"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.dirname(start);
}
const ROOT = process.env.DAZZ_REPO_ROOT || findRoot(__dirname);
const src = fs.readFileSync(path.join(ROOT, "plugins", "Dazz_VIP.plugin"), "utf8");

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
  else { fail++; console.log("  FAIL " + name + (extra ? " -> " + extra : "")); }
}

// ---- Argument ----
const args = (sections["Argument"] || []).map(l => {
  const i = l.indexOf("=");
  return { key: l.slice(0, i).trim(), rest: l.slice(i + 1).trim() };
});
const keys = args.map(a => a.key);
ok("9 个开关", keys.length === 9, keys.join(","));

const ORDER = ["unlockPro", "unlockForever", "productId", "rewriteRevenueCat", "rewriteReceipt", "farFutureTime", "strictAppOnly", "probeMode", "debugMode"];
ok("开关与脚本 ORDER 一致", JSON.stringify(keys) === JSON.stringify(ORDER), keys.join(","));
ok("switch/input 类型合法", args.every(a => /^(switch|input),/.test(a.rest)), args.map(a => a.rest.split(",")[0]).join(","));
ok("每个开关有 tag", args.every(a => /tag=/.test(a.rest)));
ok("每个开关有 desc", args.every(a => /desc=/.test(a.rest)));

// ---- Script ----
const scripts = sections["Script"] || [];
ok("四条规则", scripts.length === 4, String(scripts.length));
ok("每条都是 response if", scripts.every(s => s.startsWith("response if ")));
ok("每条都有 requires_body", scripts.every(s => /requires_body=true/.test(s)));
ok("每条都有 tag", scripts.every(s => /tag="/.test(s)));

const vipRules = scripts.filter(s => /\/dazz\/vip\.js/.test(s));
const probeRules = scripts.filter(s => /\/dazz\/probe\.js/.test(s));
ok("三条走 vip.js", vipRules.length === 3, String(vipRules.length));
ok("一条走 probe.js", probeRules.length === 1, String(probeRules.length));
ok("改写规则都带 probeMode == false 前置", vipRules.every(s => s.indexOf("${probeMode} == false") >= 0));
ok("probe 规则带 probeMode == true 前置", probeRules.every(s => s.indexOf("${probeMode} == true") >= 0));

// 参数占位符顺序
const argsBlock = /script\("[^"]+",\s*\{(.*?)\}\s*\)/.exec(vipRules[0] || "");
const passed = argsBlock ? argsBlock[1].split(",").map(x => x.trim().replace(/^[$][{]/, "").replace(/[}]$/, "").trim()) : [];
ok("vip.js 传参 9 个", passed.length === 9, argsBlock ? argsBlock[1] : "no match");
ok("传参顺序与开关一致", JSON.stringify(passed) === JSON.stringify(ORDER), passed.join(","));
ok("三条 vip 规则传参一致", vipRules.every(s => {
  const b = /script\("[^"]+",\s*\{(.*?)\}\s*\)/.exec(s);
  return !!b && b[1].replace(/\s+/g, "") === argsBlock[1].replace(/\s+/g, "");
}));

function ruleMatches(regex, url) {
  const re = new RegExp(regex, "i");
  return re.test(url);
}
// 按 probeMode 状态过滤规则，模拟 Loon 的前置条件求值
function pick(url, probeMode) {
  const hits = [];
  for (const s of scripts) {
    const rx = /[$][{]url[}] ~= \/(.+?)\/i then/.exec(s);
    if (!rx) continue;
    const wantsProbe = s.indexOf("${probeMode} == true") >= 0;
    const wantsNormal = s.indexOf("${probeMode} == false") >= 0;
    if (wantsProbe && !probeMode) continue;
    if (wantsNormal && probeMode) continue;
    if (!ruleMatches(rx[1], url)) continue;
    hits.push(/\/dazz\/probe\.js/.test(s) ? "probe" : "vip");
  }
  return hits;
}

const cases = [
  ["https://buy.itunes.apple.com/verifyReceipt", ["vip"]],
  ["https://sandbox.itunes.apple.com/verifyReceipt", ["vip"]],
  ["https://api.revenuecat.com/v1/receipts", ["vip"]],
  ["https://api.revenuecat.com/v1/subscribers/abc", ["vip"]],
  ["https://api.rc-backup.com/v1/subscribers/abc", ["vip"]],
  ["https://dazz.cam/v1/user/profile", ["vip"]],
  ["https://api.camerafilm.com/v1/app/config", ["vip"]],
  ["https://dazzapp.com/api/user", ["vip"]],
  ["https://buy.itunes.apple.com.evil.cn/verifyReceipt", []],
  ["https://buyx.itunes.apple.com/verifyReceipt", []],
  ["https://api.revenuecat.com.evil.cn/v1/receipts", []],
  ["https://dazz.cam.evil.cn/v1/user/profile", []],
  ["https://api.xiuxiu.meitu.com/v2/user/vip_info_by_group.json", []],
  ["https://api-sub.meitu.com/v2/user/vip_info_by_group.json", []]
];
for (const [url, want] of cases) {
  const got = pick(url, false);
  ok("URL 命中 " + url, JSON.stringify(got) === JSON.stringify(want), "got " + JSON.stringify(got));
}
ok("probe 模式只走 probe 规则", JSON.stringify(pick("https://dazz.cam/v1/user/profile", true)) === JSON.stringify(["probe"]), JSON.stringify(pick("https://dazz.cam/v1/user/profile", true)));
ok("probe 模式不误伤非目标域名", JSON.stringify(pick("https://example.com/x", true)) === JSON.stringify([]));

// ---- MitM ----
const mitm = (sections["MitM"] || []).join(" ");
ok("MitM 声明 hostname", /hostname\s*=/.test(mitm));
for (const h of ["buy.itunes.apple.com", "sandbox.itunes.apple.com", "api.revenuecat.com", "api.rc-backup.com", "dazz.cam", "api.camerafilm.com", "camerafilm.com", "dazzapp.com"]) {
  ok("MitM 含 " + h, mitm.indexOf(h) >= 0);
}

// ---- 语法卫生 ----
const BT = String.fromCharCode(96);
ok("无反引号", src.indexOf(BT) < 0);
ok("无 CRLF", src.indexOf("\r") < 0);
ok("无 BOM", src.charCodeAt(0) !== 0xfeff);
ok("无重复开关", new Set(keys).size === keys.length);
ok("脚本 URL 全为 raw 主分支", (src.match(/script\("([^"]+)"/g) || []).every(s => s.indexOf("raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/") >= 0));

console.log(fail === 0 ? "\nall checks passed" : "\n" + fail + " checks failed");
process.exit(fail === 0 ? 0 : 1);
