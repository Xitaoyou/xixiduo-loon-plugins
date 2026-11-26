# Dazz Pro · 会员解锁（Loon 插件）

改写 Dazz（Dazz Cam - Vintage Camera，`dazz.camera.vintagecamera`）会员判定相关的响应。会员判定分散在三个入口，插件对三处分别处理：

| 入口 | 接口 | 脚本行为 |
| --- | --- | --- |
| App Store 内购凭证 | `buy.itunes.apple.com/verifyReceipt`、`sandbox.itunes.apple.com/verifyReceipt` | 把响应改成 `status=0` 并写入 Dazz 的永久内购条目（`<bundle_id>.forever`），同步 `receipt.in_app` / `latest_receipt_info` / `pending_renewal_info` / `latest_receipt` |
| RevenueCat 订阅态 | `api.revenuecat.com`、`api.rc-backup.com` | 补全 `subscriber.entitlements`（pro/forever/premium）、`subscriptions`、`original_app_user_id`、`first_seen`、`request_date` |
| 自有接口 | `dazz.cam`、`camerafilm.com`、`dazzapp.com`（含子域） | 递归抬升 `is_pro` / `is_vip` / `member_type` / `vip_type` 等会员字段，到期时间抬到 `farFutureTime`；只有价格没有权益的对象跳过 |

## 安装

- Loon 直接导入：`loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FDazz_VIP.plugin`
- 一键导入（nsloon 中转）：`https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FDazz_VIP.plugin`
- raw 打不开时用 CDN 镜像版：`plugins/Dazz_VIP_CDN.plugin`（插件与脚本都走 jsDelivr）

需要 Loon 3.5.1 (998) 或更高、开启 MitM、安装并信任证书。装完**完全退出 Dazz 再打开**。

## 开关

| 开关 | 默认 | 作用 |
| --- | --- | --- |
| 会员字段解锁 `unlockPro` | 开 | 自有接口的会员字段抬到会员态，到期时间抬到 `farFutureTime` |
| 永久版 `unlockForever` | 开 | 内购条目写成永久（不带 `expires_date`）；关掉则写一年期订阅条目 |
| 内购商品 id `productId` | `auto` | `auto` 时按 `receipt.bundle_id` 拼 `<bundle_id>.forever`；Dazz 实测为 `com.haocai.dazzcam.forever` |
| RevenueCat 订阅态 `rewriteRevenueCat` | 开 | 是否处理 RevenueCat 响应 |
| App Store 凭证 `rewriteReceipt` | 开 | 是否处理 `verifyReceipt` 响应 |
| 到期时间戳 `farFutureTime` | `4070908800000` | 毫秒时间戳（2099-01-01Z）。只往上抬，不缩短更长的有效期；秒级字段按秒自动换算 |
| 仅改 Dazz 自身请求 `strictAppOnly` | 关 | 打开后只处理 UA 带 `dazz`/`camerafilm` 的请求 |
| 接口探测 `probeMode` | 关 | 只读：通知里给出域名、路径、body 长度与两层字段名，不改响应。打开时三条改写规则全部让路 |
| 排障日志 `debugMode` | 关 | 每次改写弹通知说明命中的接口 |

## 改写前后对照

### verifyReceipt

```json
// 改前
{ "status": 21007, "receipt": { "bundle_id": "dazz.camera.vintagecamera", "in_app": [] } }

// 改后
{
  "status": 0,
  "environment": "Production",
  "receipt": {
    "bundle_id": "dazz.camera.vintagecamera",
    "in_app": [{ "product_id": "dazz.camera.vintagecamera.forever", "purchase_date": "… Etc/GMT", "in_app_ownership_type": "PURCHASED" }]
  },
  "latest_receipt_info": [ /* 同一条 */ ],
  "pending_renewal_info": [{ "auto_renew_status": "1", /* … */ }],
  "latest_receipt": "<base64>"
}
```

### RevenueCat

```json
// 改前
{ "request_date": "…", "subscriber": { "entitlements": {}, "subscriptions": {}, "original_app_user_id": "$RCAnonymousID:x" } }

// 改后
{
  "request_date": "…",
  "request_date_ms": 1790000000000,
  "subscriber": {
    "entitlements": { "pro": { "expires_date": "2099-01-01T00:00:00Z", "purchase_date": "…", "product_identifier": "…" } },
    "subscriptions": { "<product>": { "expires_date": "2099-01-01T00:00:00Z", "store": "app_store", "period_type": "normal" } },
    "original_app_user_id": "$RCAnonymousID:dazz",
    "first_seen": "…", "last_seen": "…",
    "management_url": "https://apps.apple.com/account/subscriptions"
  }
}
```

### 自有接口

```json
// 改前
{ "data": { "is_pro": false, "vip_type": 0, "expire_time": 1700000000000, "nickname": "x" } }

// 改后
{ "data": { "is_pro": true, "vip_type": 1, "expire_time": 4070908800000, "nickname": "x" } }
```

字段类型跟随原值：原值是 `true/false` 就写布尔，是 `1/0` 就写数字，是 `"true"` 就写字符串。未命中任何字段时脚本原样放行（`$done({})`），不会给无关响应凭空造字段。

## 验证

1. Loon → 配置 → 插件，确认插件已启用、MitM 已开、证书已信任。
2. 打开「排障日志」，完全退出 Dazz 再打开；通知里应出现命中的接口（`Dazz 内购凭证` / `Dazz RevenueCat` / `Dazz 自有接口`）。
3. 若一条通知都没有，打开「接口探测」重开 App，看 App 实际请求了哪些域名。
4. 通知里的域名不在插件覆盖范围内 → 按下面的「跟版」补域名。

## 跟版

1. 打开「接口探测」，重开 App，把通知内容记下来（域名 + 路径 + 字段名）。
2. 如果出现新的域名，在 `[Script]` 的 `Dazz 自有接口` 规则正则和 `[MitM]` 里补上。
3. 如果字段名不认识，把字段名加进 `scripts/dazz/vip.js` 顶部的 `BOOL_TRUE` / `TIME_KEYS` / `INT_MIN` 词表。
4. 如果内购商品 id 变了，把 `productId` 从 `auto` 改成抓到的实际 id。
5. 改完跑 `node tests/dazz/plugin.js` 与 `node tests/dazz/run.js`，两者都要全绿。

## 边界

- 只改 App 本机读到的 JSON。服务端仍按真实账号下发权益。
- `verifyReceipt` 是全机共用的渠道（所有走 App Store 内购的 App 都会请求）。插件靠 `receipt.bundle_id` 判断归属，不是 Dazz 的凭证一律放行；`bundle_id` 缺失时才回落到 UA 判断。
- `sig` 类请求签名在客户端算，插件不碰请求侧。接口若哪天对响应也验签，对应开关要关掉。
- 不碰支付、不改商品价格、不伪造 SKU。
- 不要与其它 Dazz 内购脚本（如 `iTunes.js` / `revenuecat_multi.js`，它们同样改写 `verifyReceipt`）同时启用，两边会互相覆盖。
- 云端 AI 修图、模板下载若在服务端按账号二次校验，改字段解不开。

## 还需要真机抓包确认的部分

公开渠道拿不到 Dazz 自有 API 域名：`dazz.cam` / `camerafilm.com` / `dazzapp.com` 的证书里只有裸域与 `www`，`api.dazz.cam` 直接 TLS 握手失败，也未在公开脚本里找到调用地址。所以「自有接口」这条规则是**按域名兜底**的：域名一对上就按内容挑会员字段改，对不上就什么都不做。

要确认的话，抓一次包并提供：

1. 打开会员页时 App 请求的域名与完整路径（探测通知里的 `域名/路径` 就够）。
2. 返回 body 的前两层字段名（探测通知里的 `keys:` 与 `node:` 两行）。
3. 如果 body 是加密的（看起来像 base64 或二进制乱码），说明这层改不了，需要看有没有别的明文接口。

拿到这三样就能把兜底规则换成精确规则。

## 来源

内购凭证与 RevenueCat 的处理思路来自 [K4Z3X0R/NguyenNgocAnhTu](https://github.com/K4Z3X0R/NguyenNgocAnhTu) 的 `Module/js/iTunes.js` 与 `Module/js/revenuecat_multi.js`，本插件重写为按域名匹配 + 按响应形态分派，并补了 bundle 归属校验、类型保持、只升不降与只读探测。
