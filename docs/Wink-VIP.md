# Wink · Loon 插件使用说明

Wink（视频修图，App Store id 1594288016，包名 com.meitu.wink）的会员判定接口在 `api-sub.meitu.com` 的 `vip_info_by_group` / `products_by_biz_code` 这一族。本插件把这些响应里的会员字段在本机抬到会员态，App 读到就是「已开通」。

## 一、安装

三种方式任选其一：

| 方式 | 地址 |
|---|---|
| Loon 直接导入 | 见仓库 README 表格里的 `Loon 直接导入` 链接 |
| 粘贴 raw 链接 | Loon → 配置 → 插件 → ➕ → 从 URL 添加 |
| jsDelivr 镜像 | raw.githubusercontent.com 打不开时换 `Wink_VIP_CDN.plugin` |

装完必做：

1. Loon 首页 → 复写（MitM）→ 生成并安装证书 → 系统设置里信任证书；
2. 确认插件已启用，MitM 里能看到 `api-sub.meitu.com`、`api-winkcut.meitu.com`、`h5api-winkcut.meitu.com`、`api.account.meitu.com`；
3. **完全退出 Wink**（上滑杀掉），再打开——会员态是进会员页时拉的，缓存里还是旧的。

## 二、开关

| 开关 | 默认 | 作用 |
|---|---|---|
| 会员态解锁 | 开 | `is_vip`、`use_vip`、`have_valid_contract` 置真；`invalid_time` 等时间键抬到 2999 年；`sub_type`、`active_sub_type`、`derive_type` 等枚举抬到最高档；`membership` 升到 9 级 |
| 购买页已购态 | 开 | 商品列表里的 `product_buy_flag`、`purchased` 置真。不改价格、不造 SKU |
| AI 次数配额 | 开 | AI 接口里的 `remain_count`/`left_times`/`available_count` 等剩余额度抬到 9999，`used_count`/`used_times` 等已用计数归零，`daily_limit`/`quota` 等上限抬到 9999。只改响应里的计数，服务端算力仍按真实账号排队 |
| 抹平排队提示 | 关 | 响应里出现「使用人数较多，请稍后再试」「请求过于频繁」这类文案时，把该响应的业务码写 0、文案清空。只是不让本机弹这句提示，派发失败的任务本身仍由服务端决定 |
| 资料页会员标识 | 关 | `vip_type`、`blue_v_status`、`red_v_status` 置 1。只影响展示，默认关 |
| 仅改 Wink 自身请求 | 关 | 只处理 User-Agent 带 Wink 的请求。api-sub.meitu.com 是美图全家共用域名，打开后同机其它美图 App 不受影响 |
| 到期时间戳 | 32495529599000 | 毫秒，2999 年。只往上抬，不会缩短服务端已有的更长有效期 |
| 接口探测 | 关 | 只读，把路径和字段骨架发通知。跟版用 |
| 排障日志 | 关 | 每次改写弹通知说明改了哪些字段 |

## 三、改写前后对照

`GET https://api-sub.meitu.com/v2/user/vip_info_by_group.json`（Wink 3.x 实测形态）

```jsonc
// 改前
{ "code": 0, "data": { "is_vip": false, "use_vip": false, "have_valid_contract": false,
    "in_trial_period": true, "sub_type": 0, "active_sub_type": 0,
    "invalid_time": 1700000000000, "current_order_invalid_time": 0,
    "membership": { "id": "0", "display_name": "", "level": 0, "level_name": "免费用户" } } }

// 改后
{ "code": 0, "data": { "is_vip": true, "use_vip": true, "have_valid_contract": true,
    "in_trial_period": false, "sub_type": 2, "active_sub_type": 2,
    "invalid_time": 32495529599000, "current_order_invalid_time": 32495529599000,
    "membership": { "id": "0", "display_name": "Wink会员", "level": 9, "level_name": "超级会员" } } }
```

关键点：**只改这几个字段，`data` 里其它字段原样保留**。开源脚本常见做法是把整个 `data` 替换成写死对象，新版客户端读到缺字段会走异常分支，表现就是「装了没反应」或会员页白屏。本插件不整体替换，也不凭空新增服务端没给的键（`membership.display_name` 只在为空时补）。

值的类型跟着原值走：原值是数字写数字，是字符串写字符串，是 `"true"` 就写 `"true"`。秒级时间戳自动识别（小于 1e11 按秒补到 2999 年的秒值）。

## 四、验证

1. 打开 Wink → 我的 → 会员中心，应显示已开通/超级会员，到期时间是很远的年份；
2. 原本锁定的滤镜、导出、去水印，逐个点一遍；
3. Loon → 日志，能看到 `Wink 会员态` 命中 `api-sub.meitu.com`；
4. 不生效时：打开「排障日志」重开 App，通知里写「未命中可改字段 + 路径」说明字段名换了，用「接口探测」抓新字段再回填字段表。

## 五、AI 修复提示「当前使用人数较多，请稍后再试哦」

这是**服务端算力队列/并发限流的业务文案**，不是会员校验失败。修复结果已经渲染出来说明任务曾经跑通，是后续派发/重试被排在队列外。会员字段改写只影响本机读到的 JSON，云端 AI 任务的配额与排队在美图服务端记账，改字段拿不到算力。

插件能做的是两件事，分别对应「AI 次数配额」和「抹平排队提示」两个开关：

1. **AI 次数配额**（默认开）：AI 相关接口返回的剩余次数抬到 9999、已用次数归零、上限抬到 9999。客户端本地的前置判断（「今日次数已用完」「需要开通会员」）会因此放行。对「次数用完型」拦截有效。
2. **抹平排队提示**（默认关）：命中文案时把该响应的 `code` 写 0、`message` 清空。如果客户端只是因为这句提示中止，打开它就能继续走重试流程；如果服务端本来就没派发任务、响应里没有可用结果，这一项不会凭空造出结果。

已知的三个 AI 响应形态（`h5api-winkcut.meitu.com`，均需登录态）：

| 路径 | 无凭据时的返回 | 说明 |
|---|---|---|
| `/activity/ai_repair.json` | `{"code":10111,"message":"登录验证失败，请先登录"}` | AI 修复入口 |
| `/activity/ai_repair_task_query.json` | 同上 | 任务轮询 |
| `/activity/ai_cartoon.json` | `{"code":10101,"message":"请求参数client_id不能为空"}` | AI 动漫化 |

这三条路径都已落在插件的「Wink H5·账号」规则里（按域名匹配），不需要额外加规则。

排查口径：打开「排障日志」重试一次，通知会写清楚这次是哪种情况——

- 出现「配额 N」且 N>0：本地计数被抬上去了，再看还能不能出图；
- 只出现「限流 N」：命中的是排队文案，服务端没派发，打开「抹平排队提示」再试；
- 两个都是 0：这次请求走的是插件没覆盖的域名，用「接口探测」抓一次再补规则。

## 六、边界（务必知道）

- **只改本机读到的 JSON**。服务端仍按真实账号下发权益。滤镜、模板、AI 素材、导出如果拿到字节时还有服务端二次校验，改字段解不开内容——那类失败是服务端判的，不是插件写错。
- `api-sub.meitu.com` 是美图全家共用会员域名（美图秀秀、海报工厂、丹波等都走它）。插件按响应形态判断，只改会员形态的 JSON，但**同机其它美图 App 会被顺带命中**；要隔离请打开「仅改 Wink 自身请求」。
- 部分接口带 `sig` 参数，签名在客户端算。插件改的是**响应**，不碰请求签名；若哪天响应也带签名、客户端验签，就只能关掉对应开关。
- 不要同时装其它 Wink 脚本（qx/surge 的 wink.js 等），会重复改写同一份响应。
- 插件不碰支付、不改价格、不造 SKU，购买页只是显示成已购。

## 七、跟版流程

Wink 改版换字段时：

1. 打开「接口探测」，完全退出 Wink 再打开，进一次会员页；
2. 通知里会给出响应骨架，例如 `{code:number,data:{is_vip:boolean,invalid_time:number,membership:{...}}}`；
3. 把新字段名补进 `scripts/wink/vip.js` 的 `BOOL_TRUE` / `TIME_KEYS` / `INT_MIN` 表；
4. 改完跑 `node tests/wink/plugin.js` 与 `node tests/wink/run.js` 回归（50 条断言）；
5. 推仓库，等 raw 缓存刷新（约 2–4 分钟），手机上重开 App。

## 八、来源与改动

改写自 `K4Z3X0R/NguyenNgocAnhTu` 的 `Module/js/Wink.js`（原作者 Hausd0rff 2023-05-30 版本）：

- 原脚本路径写死 `^https?://api-sub\.meitu\.com/.*vip`，命中面窄，且把整个 `data` 换成写死对象；
- 本插件按域名匹配 + 按响应形态分派，只抬升已知字段，其余原样保留；
- 补上购买页、资料页、有效期、会员等级这几处原脚本没管的地方；
- 加了 AI 次数配额与排队文案两个开关，覆盖「全能修复」这类按次数与队列放行的 AI 功能；
- 加了探测脚本与 50 条 fixture 回归，App 改版能自己定位新字段。

仅供学习与研究使用。
