#!/usr/bin/env node
// 本地回归：用 fixture 跑 wink/vip.js，检查字段抬升、类型保持与放行条件。
const fs = require("fs");
const path = require("path");
const vm = require("vm");

function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 6; i++) {
    if (fs.existsSync(path.join(dir, "scripts", "wink", "vip.js"))) return dir;
    const up = path.dirname(dir);
    if (up === dir) break;
    dir = up;
  }
  return path.dirname(start);
}
const ROOT = process.env.WINK_REPO_ROOT || findRoot(__dirname);
const src = fs.readFileSync(path.join(ROOT, "scripts", "wink", "vip.js"), "utf8");

function run({ url, body, argument, headers }) {
  let out = { done: false, body: null, headers: null };
  const store = new Map();
  const logs = [];
  const ctx = {
    $request: { url, headers: headers || { "User-Agent": "Wink/3.22.0 (iPhone; iOS 18.0)" } },
    $response: { body: typeof body === "string" ? body : JSON.stringify(body), headers: { "Content-Type": "application/json", ETag: "abc" } },
    $argument: argument,
    $persistentStore: {
      read: k => (store.has(k) ? store.get(k) : null),
      write: (k, v) => store.set(k, v)
    },
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
  else { fail++; console.log("  FAIL " + name + (extra ? " :: " + extra : "")); }
}

const FAR = 32495529599000;
const FAR_S = Math.floor(FAR / 1000);

const groupBody = {
  code: 0,
  message: "success",
  request_id: "dd629db310e74ab49edf9e58c0659570",
  data: {
    active_sub_type: 0,
    account_type: 0,
    sub_type_name: "",
    current_order_invalid_time: 0,
    active_order_id: "0",
    limit_type: 0,
    use_vip: false,
    have_valid_contract: false,
    derive_type_name: "普通用户",
    derive_type: 0,
    in_trial_period: true,
    is_vip: false,
    membership: { id: "0", display_name: "", level: 0, level_name: "免费用户" },
    invalid_time: 1700000000000,
    sub_type: 0,
    period_type: 0,
    contract_status: 0
  }
};

console.log("1. vip_info_by_group：会员态抬升，其它字段保留");
{
  const { out, json, logs } = run({
    url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json?app=wink",
    body: groupBody
  });
  ok("返回了 body", out.done && !!out.body);
  ok("is_vip 为 true", json && json.data.is_vip === true);
  ok("use_vip 为 true", json && json.data.use_vip === true);
  ok("have_valid_contract 为 true", json && json.data.have_valid_contract === true);
  ok("in_trial_period 为 false", json && json.data.in_trial_period === false);
  ok("invalid_time 拉到远未来", json && json.data.invalid_time === FAR, json && String(json.data.invalid_time));
  ok("current_order_invalid_time 也抬升", json && json.data.current_order_invalid_time === FAR);
  ok("sub_type 抬到 2", json && json.data.sub_type === 2);
  ok("membership.level=9", json && json.data.membership.level === 9);
  ok("membership.level_name 升级", json && json.data.membership.level_name === "超级会员");
  ok("外层 code / request_id 原样", json && json.code === 0 && json.request_id === groupBody.request_id);
  ok("data 字段数量未变", json && Object.keys(json.data).length === Object.keys(groupBody.data).length, json && String(Object.keys(json.data).length));
  ok("Cache-Control 注入且删 ETag", out.headers && out.headers["Cache-Control"] && !out.headers.ETag, JSON.stringify(out.headers));
  ok("未弹通知（debug 关）", logs.length === 0, logs.join("|"));
}

console.log("2. 秒级时间戳按秒换算");
{
  const body = { data: { is_vip: false, invalid_time: 1700000000, valid_time: "1700000000" } };
  const { json } = run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body });
  ok("数字秒级 -> far/1000", json && json.data.invalid_time === FAR_S, json && String(json.data.invalid_time));
  ok("字符串保持字符串", json && typeof json.data.valid_time === "string" && json.data.valid_time === String(FAR_S), json && json.data.valid_time);
}

console.log("3. 字符串形态的布尔与数字不被改坏");
{
  const body = { data: { is_vip: "false", use_vip: "0", have_valid_contract: "true", sub_type: "0", invalid_time: "1700000000000" } };
  const { json } = run({ url: "https://api-sub.meitu.com/v2/user/vip.json", body });
  ok("is_vip 字符串 true", json && json.data.is_vip === "true", json && String(json.data.is_vip));
  ok("use_vip 字符串 1", json && json.data.use_vip === "1", json && String(json.data.use_vip));
  ok("have_valid_contract 保持 true", json && json.data.have_valid_contract === "true");
  ok("sub_type 字符串 2", json && json.data.sub_type === "2", json && String(json.data.sub_type));
  ok("invalid_time 字符串拉满", json && json.data.invalid_time === String(FAR));
}

console.log("4. products_by_biz_code：购买页已购标记");
{
  const body = {
    code: 0,
    data: {
      biz_code: "wink_vip",
      products: [
        { product_id: "1", product_buy_flag: 0, main_explain: "立即购买 ￥25" },
        { product_id: "2", product_buy_flag: 0, purchased: false }
      ]
    }
  };
  const { json } = run({ url: "https://api-sub.meitu.com/v2/entrance/products_by_biz_code.json?sig=x", body });
  ok("product_buy_flag 置 1", json && json.data.products[0].product_buy_flag === 1);
  ok("purchased 置 true", json && json.data.products[1].purchased === true);
  ok("价格文案未改", json && json.data.products[0].main_explain === "立即购买 ￥25");
  ok("商品数量未变", json && json.data.products.length === 2);
}

console.log("5. 资料页开关：默认不动，打开才改");
{
  const body = { data: { screen_name: "abc", vip_type: 0, follower_count: 12 } };
  const off = run({ url: "https://api.account.meitu.com/users/show_current.json", body, argument: { modifyProfile: "false" } });
  ok("默认不改资料", !off.out.body);
  const on = run({ url: "https://api.account.meitu.com/users/show_current.json", body, argument: { modifyProfile: "true" } });
  ok("打开后 vip_type=1", on.json && on.json.data.vip_type === 1);
  ok("昵称与粉丝数未改", on.json && on.json.data.screen_name === "abc" && on.json.data.follower_count === 12);
}

console.log("6. strictAppOnly：非 Wink 请求放行");
{
  const body = { data: { is_vip: false, invalid_time: 0 } };
  const other = run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body, argument: { strictAppOnly: "true" }, headers: { "User-Agent": "MeituXiuxiu/9.9" } });
  ok("其它美图 App 未改", !other.out.body, other.logs.join("|"));
  const wink = run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body, argument: { strictAppOnly: "true" }, headers: { "User-Agent": "Wink/3.22.0" } });
  ok("Wink 自身命中", wink.json && wink.json.data.is_vip === true);
}

console.log("7. 无关响应原样放行");
{
  const body = { code: 0, data: { ai_cartoon_quota: 3, task_id: "t1" } };
  const { out } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_cartoon.json", body });
  ok("无会员形态不改", !out.body);
}

console.log("8. 非 JSON 与非对象响应放行");
{
  ok("HTML 放行", !run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body: "<html>502</html>" }).out.body);
  ok("数组放行", !run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body: "[1,2,3]" }).out.body);
  ok("空 body 放行", !run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body: "" }).out.body);
}

console.log("9. 全关开关时保持原样");
{
  const { out } = run({
    url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json",
    body: groupBody,
    argument: { unlockVip: "false", rewritePurchase: "false", modifyProfile: "false" }
  });
  ok("未改 body", !out.body);
}

console.log("10. probeMode 只读并输出骨架");
{
  const { out, logs } = run({
    url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json",
    body: groupBody,
    argument: { probeMode: "true" }
  });
  ok("未改 body", !out.body);
  ok("日志含路径", logs.join(" ").indexOf("api-sub.meitu.com/v2/user/vip_info_by_group.json") >= 0, logs.join("|").slice(0, 120));
  ok("日志含字段名", logs.join(" ").indexOf("is_vip") >= 0, logs.join("|").slice(0, 120));
}

console.log("11. 已有超长有效期不被缩短");
{
  const body = { data: { is_vip: false, invalid_time: 4102444800000000 } };
  const { json } = run({ url: "https://api-sub.meitu.com/v2/user/vip_info_by_group.json", body });
  ok("更长期保留", json && json.data.invalid_time === 4102444800000000, json && String(json.data.invalid_time));
}

console.log("12. 只带时间键的无关对象不凭空长出会员字段");
{
  const body = { code: 0, data: { task_id: "t1", end_time: 1700000000000, cover_url: "https://x/y.jpg" } };
  const { json } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_cartoon_task_query.json", body });
  ok("未新增 is_vip", json && json.data.is_vip === undefined, JSON.stringify(json && json.data));
  ok("其它字段未改", json && json.data.cover_url === "https://x/y.jpg" && json.data.task_id === "t1");
}

console.log("13. AI 次数配额抬升");
{
  const body = { code: 0, data: { remain_count: 0, used_count: 3, daily_limit: 1, task_id: "t9" } };
  const { json } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_repair.json", body });
  ok("剩余次数抬到上限", json && json.data.remain_count === 9999, json && String(json.data.remain_count));
  ok("已用次数归零", json && json.data.used_count === 0, json && String(json.data.used_count));
  ok("上限抬到上限", json && json.data.daily_limit === 9999, json && String(json.data.daily_limit));
  ok("无关字段保留", json && json.data.task_id === "t9");
}

console.log("14. 配额开关关闭时保持原值");
{
  const body = { code: 0, data: { remain_count: 0, used_count: 3 } };
  const { out } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_repair.json", body, argument: { boostQuota: "false", unlockVip: "false" } });
  ok("未改 body", !out.body);
}

console.log("15. 排队文案抹平");
{
  const body = { code: 30001, message: "当前使用人数较多，请稍后再试哦", data: null };
  const { json } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_repair.json", body, argument: { retryOnBusy: "true" } });
  ok("业务码归零", json && json.code === 0, json && String(json.code));
  ok("提示文案清空", json && json.message === "", json && String(json.message));
}

console.log("16. 排队开关关闭时保持原样");
{
  const body = { code: 30001, message: "当前使用人数较多，请稍后再试哦" };
  const { out } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_repair.json", body, argument: { unlockVip: "false", boostQuota: "false", rewritePurchase: "false" } });
  ok("未改 body", !out.body);
}

console.log("17. 同名但不是配额的对象不动");
{
  const body = { code: 0, data: { ai_cartoon_quota: 3, style_count: 12, task_id: "t1" } };
  const { out } = run({ url: "https://h5api-winkcut.meitu.com/activity/ai_cartoon.json", body });
  ok("未改 body", !out.body);
}

console.log("\n" + pass + " passed, " + fail + " failed");
process.exit(fail ? 1 : 0);
