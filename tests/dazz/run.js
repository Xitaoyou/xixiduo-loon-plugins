#!/usr/bin/env node
// 本地回归：用 fixture 跑 dazz/vip.js，检查字段抬升、类型保持、凭证补全与放行条件。
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "scripts", "dazz", "vip.js"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.dirname(start);
}
const ROOT = process.env.DAZZ_REPO_ROOT || findRoot(__dirname);
const src = fs.readFileSync(path.join(ROOT, "scripts", "dazz", "vip.js"), "utf8");

const DEFAULTS = ["true", "true", "auto", "true", "true", "4070908800000", "false", "false", "false"];

function run({ url, body, argument, headers }) {
  let out = { done: false, body: null, headers: null };
  const store = new Map();
  const logs = [];
  const ctx = {
    $request: { url, headers: headers || { "User-Agent": "Dazz/2.18 (iPhone; iOS 18.0)" } },
    $response: { body: typeof body === "string" ? body : JSON.stringify(body), headers: { "Content-Type": "application/json", ETag: "x" } },
    $argument: argument || DEFAULTS,
    $persistentStore: { read: k => (store.has(k) ? store.get(k) : null), write: (k, v) => store.set(k, v) },
    $notification: { post: (...a) => { logs.push(a.join(" / ")); } },
    $done: o => { out.done = true; if (o && o.body !== undefined) out.body = o.body; if (o && o.headers) out.headers = o.headers; },
    console: { log: (...a) => { logs.push(a.join(" ")); } }
  };
  vm.createContext(ctx);
  vm.runInContext(src, ctx, { timeout: 5000 });
  let json = null;
  if (out.body) { try { json = JSON.parse(out.body); } catch (e) { json = null; } }
  return { out, logs, json };
}

let pass = 0, fail = 0;
function ok(name, cond, extra) {
  if (cond) { pass++; console.log("  PASS " + name); }
  else { fail++; console.log("  FAIL " + name + (extra ? " -> " + extra : "")); }
}

const RECEIPT_URL = "https://buy.itunes.apple.com/verifyReceipt";
const RC_URL = "https://api.revenuecat.com/v1/subscribers/abc";

// 1. verifyReceipt：写入 Dazz 永久条目
{
  const payload = { status: 21007, receipt: { bundle_id: "dazz.camera.vintagecamera", in_app: [] } };
  const r = run({ url: RECEIPT_URL, body: payload });
  ok("1 verifyReceipt 被改写", !!r.out.body);
  ok("1 status 归零", r.json && r.json.status === 0, String(r.json && r.json.status));
  const item = r.json && r.json.latest_receipt_info && r.json.latest_receipt_info[0];
  ok("1 写入 product_id", !!item && item.product_id === "dazz.camera.vintagecamera.forever", item && item.product_id);
  ok("1 永久条目无 expires_date", !!item && item.expires_date === undefined);
  ok("1 receipt.in_app 同步", !!r.json && r.json.receipt.in_app.length === 1);
  ok("1 去掉 ETag", !!r.out.headers && !Object.keys(r.out.headers).some(k => k.toLowerCase() === "etag"));
}

// 2. 自定义 productId
{
  const args = DEFAULTS.slice();
  args[2] = "com.haocai.dazzcam.forever";
  const r = run({ url: RECEIPT_URL, body: { status: 0, receipt: { bundle_id: "dazz.camera.vintagecamera", in_app: [] } }, argument: args });
  const item = r.json && r.json.latest_receipt_info && r.json.latest_receipt_info[0];
  ok("2 用自定义 productId", !!item && item.product_id === "com.haocai.dazzcam.forever", item && item.product_id);
}

// 3. 非永久：写一年期 expires_date
{
  const args = DEFAULTS.slice();
  args[1] = "false";
  const r = run({ url: RECEIPT_URL, body: { status: 0, receipt: { bundle_id: "dazz.camera.vintagecamera", in_app: [] } }, argument: args });
  const item = r.json && r.json.latest_receipt_info && r.json.latest_receipt_info[0];
  ok("3 非永久带 expires_date", !!item && typeof item.expires_date === "string" && item.expires_date.length > 10);
  ok("3 expires_date_ms 是 2099", !!item && item.expires_date_ms === "4070908800000", item && item.expires_date_ms);
}

// 4. RevenueCat
{
  const payload = { request_date: "2026-01-01T00:00:00Z", subscriber: { entitlements: {}, subscriptions: {}, original_app_user_id: "$RCAnonymousID:x" } };
  const r = run({ url: RC_URL, body: payload });
  ok("4 RC 被改写", !!r.out.body);
  const ents = r.json && r.json.subscriber.entitlements;
  ok("4 补出 pro 权益", !!ents && !!ents.pro, ents && Object.keys(ents).join(","));
  ok("4 pro 到期 2099", !!ents && ents.pro.expires_date.indexOf("2099") === 0, ents && ents.pro.expires_date);
  ok("4 subscriptions 非空", !!r.json && Object.keys(r.json.subscriber.subscriptions).length > 0);
}

// 5. 自有接口会员字段
{
  const payload = { code: 0, data: { is_pro: false, vip_type: 0, expire_time: 1700000000000, nickname: "x" } };
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: payload });
  ok("5 会员字段被改写", !!r.out.body);
  ok("5 is_pro 置真", r.json && r.json.data.is_pro === true, String(r.json && r.json.data.is_pro));
  ok("5 vip_type 抬到 1", r.json && r.json.data.vip_type === 1);
  ok("5 expire_time 抬到 2099", r.json && r.json.data.expire_time === 4070908800000, String(r.json && r.json.data.expire_time));
  ok("5 其它字段保留", r.json && r.json.data.nickname === "x");
}

// 6. 无关响应放行
{
  const payload = { code: 0, data: { nickname: "x", avatar: "y" } };
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: payload });
  ok("6 无会员字段时放行", r.out.body === null);
}

// 7. 价格对象不动
{
  const payload = { data: { price: 6.99, currency: "USD", productId: "x.yearly", title: "Pro" } };
  const r = run({ url: "https://dazz.cam/v1/config", body: payload });
  const body = r.out.body ? r.json : payload;
  ok("7 价格保持", body.data.price === 6.99, String(body.data.price));
  ok("7 币种保持", body.data.currency === "USD");
}

// 8. 非 JSON 放行
{
  const r = run({ url: "https://dazz.cam/v1/x", body: "<html>hi</html>" });
  ok("8 HTML 放行", r.out.body === null);
}

// 9. 非 verifyReceipt 的 apple 域名不动
{
  const r = run({ url: "https://buy.itunes.apple.com/other", body: { status: 0, receipt: { bundle_id: "dazz.camera.vintagecamera" } } });
  ok("9 非 verifyReceipt 放行", r.out.body === null);
}

// 10. 开关全关
{
  const args = ["false", "false", "auto", "false", "false", "4070908800000", "false", "false", "false"];
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: { data: { is_pro: false } }, argument: args });
  ok("10 全关时放行", r.out.body === null);
}

// 11. probe 只读
{
  const args = DEFAULTS.slice();
  args[7] = "true";
  const r = run({ url: RC_URL, body: { subscriber: {} }, argument: args });
  ok("11 probe 不放改 body", r.out.body === null);
  ok("11 probe 有通知", r.logs.length > 0, String(r.logs.length));
}

// 12. strictAppOnly
{
  const args = DEFAULTS.slice();
  args[6] = "true";
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: { data: { is_pro: false } }, argument: args, headers: { "User-Agent": "Safari/18.0" } });
  ok("12 非 Dazz UA 放行", r.out.body === null);
  const r2 = run({ url: "https://dazz.cam/v1/user/profile", body: { data: { is_pro: false } }, argument: args, headers: { "User-Agent": "Dazz/2.18" } });
  ok("12 Dazz UA 改写", !!r2.out.body);
}

// 13. 秒级时间戳按秒补
{
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: { data: { is_pro: false, expire_time: 1700000000 } } });
  ok("13 秒级时间戳补到秒值", r.json && r.json.data.expire_time === 4070908800, String(r.json && r.json.data.expire_time));
}

// 14. 已更长的有效期不缩短
{
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: { data: { is_pro: true, expire_time: 5000000000000 } } });
  const val = r.out.body ? r.json.data.expire_time : 5000000000000;
  ok("14 更长期限不缩短", val === 5000000000000, String(val));
}

// 15. verifyReceipt 里其它 App 的凭证不被改
{
  const payload = { status: 0, receipt: { bundle_id: "com.apple.mobilesafari", in_app: [] } };
  const r = run({ url: RECEIPT_URL, body: payload, headers: { "User-Agent": "AppStore/3.0" } });
  ok("15 其它 App 凭证放行", r.out.body === null);
}

// 16. verifyReceipt 里 bundle_id 缺失时按 UA 判断
{
  const r = run({ url: RECEIPT_URL, body: { status: 0, receipt: { in_app: [] } }, headers: { "User-Agent": "Dazz/2.18 CFNetwork/1.0" } });
  ok("16 UA 命中 Dazz 时改写", !!r.out.body);
  const r2 = run({ url: RECEIPT_URL, body: { status: 0, receipt: { in_app: [] } }, headers: { "User-Agent": "SomeOtherApp/1.0" } });
  ok("16 UA 不命中时放行", r2.out.body === null);
}

// 17. 自有接口里 is_pro 由 vip_type 派生且保持数字类型
{
  const r = run({ url: "https://dazz.cam/v1/user/profile", body: { data: { vip_type: 0, nick: "x" } } });
  ok("17 补出 is_pro 且为数字", r.json && r.json.data.is_pro === 1, String(r.json && r.json.data.is_pro));
}

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail === 0 ? 0 : 1);
