# 轻听英语 VIP 插件 · 说明

插件：`plugins/QingTing_English_VIP.plugin`
脚本：`scripts/qingting/vip.js`、`scripts/qingting/probe.js`
适用：轻听英语 iOS 1.9.1（明文 v1 接口）与 2.0.6（v3 加密接口）；Loon 3.5.x

---

## 1. 怎么装

[点此一键导入 Loon](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FQingTing_English_VIP.plugin)

1. Loon → 配置 → 插件 → 右上角 ➕ → 从 URL 添加：

   ```
   https://raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/plugins/QingTing_English_VIP.plugin
   ```

   本地调试可以先把 `plugins/` 与 `scripts/` 一起传到仓库再装；脚本地址写死在 .plugin 里，改脚本必须推仓库，Loon 只缓存 URL。

2. 确认 MitM 已开启，证书已信任（插件会自动把 `api.beingfine.cn, sapi.beingfine.cn, learnywhere.cn` 加进 hostname）。

3. 杀掉轻听英语后台再重开，让它重新拉启动接口。

## 2. 开关

| 开关 | 默认 | 作用 |
| --- | --- | --- |
| modifyPrivileges | 开 | 启动接口里 granted / expire_date / user_type / dl_quota 等字段拉满 |
| downgradeV3 | 开 | 2.0.6 的 `data_encrypted=1` 改成 0 并注入明文 privileges |
| modifyPurchase | 开 | purchase2 的 `account.vip_type` 置 1、`expiry` 置远期 |
| modifyPromote | 开 | in-duration 的 `auth.*` 的 op / pa 全部置 1 |
| quota | 999 | 写入 dl_quota，只往上抬 |
| expireAt | 4077153336000 | 毫秒时间戳（2099 年），只往上抬 |
| probeMode | 关 | 只读探测，不发通知以外的副作用；App 改版后排障用 |
| debugMode | 关 | 每次改写弹通知，说明改了哪个接口、多少处 |

`quota`、`expireAt` 在插件里是 input，但 Loon 的 input 值走 `$argument` 的字符串通道；脚本同时支持 `$persistentStore` 里的 `qt_quota` / `qt_expireAt` 覆盖。

## 3. 改写了什么

### 3.1 1.9.1 明文启动接口

`GET https://sapi.beingfine.cn/v1/UserLaunchAppReport` 的响应：

```json
{"data_body":{"privileges":{
  "lrc_unlimited_online_playback":{"expire_date":1700000000000,"granted":0},
  "lrc_unlimited_download":{"expire_date":1700000000000,"granted":0},
  "wordroot":{"expire_date":1700000000000,"granted":0,"user_type":0},
  "collins":{"expire_date":1700000000000,"granted":0,"collins_user_type":0},
  "user_status":{"dl_quota":3,"subscription_count":0}
},"user_status":{"dl_quota":40}}}
```

改写后：

```json
{"data_body":{"privileges":{
  "lrc_unlimited_online_playback":{"expire_date":4077153336000,"granted":1},
  "lrc_unlimited_download":{"expire_date":4077153336000,"granted":1},
  "wordroot":{"expire_date":4077153336000,"granted":1,"user_type":1},
  "collins":{"expire_date":4077153336000,"granted":1,"collins_user_type":1},
  "user_status":{"dl_quota":999,"subscription_count":1,"user_has_preferences":1,"subscription_has_updates":1}
},"user_status":{"dl_quota":999,"subscription_count":1}}}
```

字段级规则：`granted`/`is_vip`/`is_member` 之类恒真；`need_vip`/`locked` 之类恒假；`*_user_type` 抬到 1、`*_level` 抬到 3；`expire_*`/`end_*` 取 `Math.max(原值, expireAt)`；`dl_quota` 取 `Math.max(原值, quota)`。类型跟随原值（数字还数字、字符串还字符串），避免客户端 JSON 解析崩。

### 3.2 2.0.6 V3 启动接口

`POST https://api.beingfine.cn/v3/2/report/launch/{13位时间戳}` 的 `data_body` 是 1344 字符的密文字符串，`data_encrypted=1`，另有 `v3_security{guest,token,secret}`。

脚本不伪造密文（密钥在 App 里、且服务端校验），做法是把信封降级：

```json
{"data_encrypted":0,"data_body":{"privileges":{...与 3.1 同构...}},"v3_security":{...原样保留...}}
```

客户端拿到 `data_encrypted=0` 会按明文路径解析。**这条路能不能走通取决于客户端是否硬编码要求密文**：2.0.6 的实机上如果界面报错或会员态不刷新，把 `downgradeV3` 关掉，只留明文接口那几条。

### 3.3 购买与促销接口（两版共有）

- `/api/qt/buy/vip/purchase2`：`account.is_login=1`、`vip_type=1`、`expiry` 从空串变 `2100-01-01 00:00:00`；`products` 数组原样不动（那是商品列表，改了会点不出购买）。
- `/api/buy/promote/in-duration`：`auth` 下 11 个权益键（qtvip/bbvip/collins/wordroot/wordderive/wordsyn/wordlist/bbnote/yanzhibao/sushua/wordbooks）的 `op`、`pa` 全部置 1，`in_purchase_duration` 置 1。

### 3.4 兜底路径

插件规则按**域名**匹配（`(api|sapi).beingfine.cn`、`learnywhere.cn`），脚本内部再按响应形态分流。同域名下出现没登记的新路径时，只要响应里能找到 `privileges` / `vip_type` / `granted` / `need_vip` 之类语义，就按 3.1 的字段规则改。App 换路径不会立刻失效。

## 4. 验证

脚本层：

```bash
node tests/qingting/plugin.js   # 结构、参数顺序、11 条 URL 命中表、MitM 覆盖
node tests/qingting/run.js      # 9 组 fixture、27 条断言：明文启动 / V3 降级 / 降级关闭放行 / purchase2 / in-duration / 无关响应不改 / 兜底命中 / 非法 JSON / 全关开关 / probe 只读
```

实机：

1. `probeMode` 开，重开 App，看通知里 `path=`、`enc=`、`bodyType=`、`privKeys=` 是否出现预期接口。
2. 关掉 `probeMode`，开 `debugMode`，重开 App，应看到「启动响应权益改写 N 处」。
3. 检查：下载中心额度是否变 999、柯林斯/词根入口是否可点、下载按钮是否不再提示会员。

Loon 日志里搜 `轻听英语 VIP` 能看到每次改写的 tag。

## 5. 边界（写清楚，省得反复试）

- **服务端仍然是真实账号**。本插件只改客户端读到的 JSON。凡是服务端在发音频/发密文时二次校验权益的路径（V3 加密资源、付费课程音频地址），改字段解不开内容。
- **V3 密文不能伪造**。`v3_security.secret` 的派生逻辑在 App 二进制里，脚本层拿不到；降级路径只在客户端接受明文时才有效。
- **不要给 `products` 造假 SKU**。购买页走 StoreKit，假商品点击会失败并可能触发风控。
- 与「轻听英语 2.0.6 只读诊断」插件（`QingTing_English_2.0.6_Inspect.plugin`）互斥：两个都开时诊断插件会看到改写后的响应，读数失真。排障时先关主插件。

## 6. 后续版本怎么跟

1. 开 `probeMode`，重开 App，通知里看新路径与新字段名。
2. 把新字段名加进 `scripts/qingting/vip.js` 的 `GRANT` / `DENY` / `EXPIRE` / `QUOTA_K` / `TYPE` 词表；新域名加进 .plugin 的 `[Script]` 与 `[MitM]`。
3. `node tests/qingting/plugin.js && node tests/qingting/run.js` 跑一遍，再补一条 fixture。
