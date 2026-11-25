#!/usr/bin/env node
// 本地回归：用固定 fixture 跑 vip.js，检查字段改写与结构保持。
// 用法：node qingtingloon/tests/run.js
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "scripts", "qingting", "vip.js"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.dirname(start);
}
const ROOT = process.env.QT_REPO_ROOT || findRoot(__dirname);
const SCRIPT = path.join(ROOT, "scripts", "qingting", "vip.js");
const src = fs.readFileSync(SCRIPT, "utf8");

function run({ url, body, argument }) {
  let out = { done: false, body: null };
  const store = new Map();
  const ctx = {
    $request: { url },
    $response: { body: typeof body === "string" ? body : JSON.stringify(body) },
    $argument: argument,
    $persistentStore: {
      read: k => (store.has(k) ? store.get(k) : null),
      write: (k, v) => store.set(k, v)
    },
    $notification: { post: (...a) => { logs.push(a.join(" / ")); } },
    $done: o => { out.done = true; if (o && o.body !== undefined) out.body = o.body; },
    console: { log: (...a) => { logs.push(a.join(" ")); } }
  };
  const logs = [];
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { timeout: 5000 });
  return { out, logs, json: out.body ? JSON.parse(out.body) : null };
}

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

const FAR = 4077153336000;

console.log("1. 1.9.1 明文启动接口 privileges 改写");
{
  const body = {
    result_code: 0,
    data_kind: 1,
    data_version: 1,
    data_encrypted: 0,
    data_body: {
      privileges: {
        lrc_unlimited_online_playback: { expire_date: 1700000000000, granted: 0 },
        lrc_unlimited_download: { expire_date: 1700000000000, granted: 0 },
        wordroot: { expire_date: 1700000000000, granted: 0, user_type: 0 },
        collins: { expire_date: 1700000000000, granted: 0, collins_user_type: 0 },
        user_status: { dl_quota: 3, subscription_count: 0, user_has_preferences: 0, subscription_has_updates: 0 }
      },
      user_status: { dl_quota: 40, subscription_count: 0 }
    }
  };
  const { out, json } = run({ url: "https://sapi.beingfine.cn/v1/UserLaunchAppReport?app_id=1", body, argument: { modifyPrivileges: "true" } });
  ok("返回了 body", out.done && !!out.body);
  const p = json.data_body.privileges;
  ok("在线播放 granted=1", p.lrc_unlimited_online_playback.granted === 1);
  ok("在线播放 expire_date 拉满", p.lrc_unlimited_online_playback.expire_date === FAR);
  ok("下载 granted=1", p.lrc_unlimited_download.granted === 1);
  ok("词根 user_type=1", p.wordroot.user_type === 1);
  ok("柯林斯 collins_user_type=1", p.collins.collins_user_type === 1);
  ok("privileges.dl_quota=999", p.user_status.dl_quota === 999);
  ok("subscription_count=1", p.user_status.subscription_count === 1);
  ok("顶层 user_status.dl_quota 也提升", json.data_body.user_status.dl_quota === 999);
  ok("其它顶层字段保留", json.result_code === 0 && json.data_encrypted === 0);
}

console.log("2. 2.0.6 V3 加密启动响应：降级注入");
{
  const body = {
    result_code: 0, data_kind: 1, data_version: 3,
    data_body: "QWJjZGVmZ2hpamt..cipher..",
    data_encrypted: 1,
    v3_security: { guest: "x", token: "y", secret: "z" },
    v3_security_overwrite: 0
  };
  const { out, json } = run({ url: "https://api.beingfine.cn/v3/2/report/launch/1795604950977", body, argument: { downgradeV3: "true" } });
  ok("data_encrypted 置 0", json.data_encrypted === 0);
  ok("data_body 变对象", json.data_body && typeof json.data_body === "object");
  ok("privileges 齐备", json.data_body.privileges.wordroot.granted === 1 && json.data_body.privileges.collins.expire_date === FAR);
  ok("v3_security 原样保留", json.v3_security.token === "y");
  ok("result_code 未被污染", json.result_code === 0);
}

console.log("3. V3 加密但降级关闭：原样放行");
{
  const body = { result_code: 0, data_body: "cipher", data_encrypted: 1, v3_security: { token: "y" } };
  const { out } = run({ url: "https://api.beingfine.cn/v3/2/report/launch/1795604950977", body, argument: { downgradeV3: "false" } });
  ok("未改 body", !out.body);
}

console.log("4. purchase2 会员态");
{
  const body = { data_body: { account: { is_login: 1, vip_type: 0, expiry: "" }, products: [{ id: 1 }, { id: 2 }, { id: 3 }] } };
  const { json } = run({ url: "https://learnywhere.cn/api/qt/buy/vip/purchase2?sid=1&feat=2", body, argument: { modifyPurchase: "true" } });
  ok("vip_type=1", json.data_body.account.vip_type === 1);
  ok("expiry 变成日期串", typeof json.data_body.account.expiry === "string" && json.data_body.account.expiry.length > 4);
  ok("products 三条不变", json.data_body.products.length === 3);
}

console.log("5. promote/in-duration 权益位");
{
  const keys = ["qtvip", "bbvip", "collins", "wordroot", "wordderive", "wordsyn", "wordlist", "bbnote", "yanzhibao", "sushua", "wordbooks"];
  const auth = {};
  keys.forEach(k => { auth[k] = { op: 1, pa: k === "qtvip" || k === "sushua" ? 0 : 1 }; });
  const body = { data_body: { in_purchase_duration: 0, auth } };
  const { json } = run({ url: "https://learnywhere.cn/api/buy/promote/in-duration?sid=1&feat=2&promote=1&purchase_page=1", body, argument: { modifyPromote: "true" } });
  ok("11 项全为 1", Object.keys(json.data_body.auth).every(k => json.data_body.auth[k].op === 1 && json.data_body.auth[k].pa === 1));
  ok("in_purchase_duration=1", json.data_body.in_purchase_duration === 1);
}

console.log("6. 同域名无关响应不介入");
{
  const body = { data_body: { courses: [{ id: 1, name: "BBC" }], total: 1 } };
  const { out } = run({ url: "https://api.beingfine.cn/v1/LE_GetMySubscribedCourses", body, argument: {} });
  ok("无权益形态时未改 body", !out.body);
}

console.log("6b. 未知路径但含权益形态时兜底改写");
{
  const body = { data_body: { privileges: { collins: { granted: 0, expire_date: 1700000000000 } } } };
  const { json } = run({ url: "https://api.beingfine.cn/v9/whatever/new-path/1", body, argument: {} });
  ok("兜底命中并改写", json && json.data_body.privileges.collins.granted === 1 && json.data_body.privileges.collins.expire_date === 4077153336000);
}

console.log("7. 非法 JSON 放行不崩");
{
  const { out } = run({ url: "https://sapi.beingfine.cn/v1/UserLaunchAppReport", body: "<html>502</html>", argument: {} });
  ok("未改 body", !out.body);
}

console.log("8. 全关开关时保持语义不变");
{
  const body = { data_body: { privileges: { wordroot: { granted: 0 } } } };
  const { out } = run({
    url: "https://sapi.beingfine.cn/v1/UserLaunchAppReport",
    body,
    argument: { modifyPrivileges: "false" }
  });
  ok("未改 body", !out.body);
}

console.log("9. probeMode 只读：有权益也不改");
{
  const body = { data_body: { privileges: { collins: { granted: 0 } } } };
  const { out, logs } = run({ url: "https://api.beingfine.cn/v9/unknown/1", body, argument: { probeMode: "true" } });
  ok("未改 body", !out.body);
  ok("日志里有路径", logs.join(" ").indexOf("path=/v9/unknown/1") >= 0, logs.join(" | ").slice(0, 80));
}

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
