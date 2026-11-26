# Dazz Pro · 会员解锁

> **结论先说**：Dazz（Dazz相机，`dazz.camera.vintagecamera`，App Store id 1422471180）没有任何自有会员接口，
> 会员判定 100% 在设备本地完成。**Loon / Surge / Quantumult X 这类响应改写插件在 Dazz 上结构上无效**，
> 抓包空白不是配置问题。能用的是越狱侧运行时插件：[`dazzpro/`](../dazzpro)。

## 一、为什么 Loon 插件无效

对 2.18 主二进制（Mach-O，26.6 MB，`cryptid=0` 未加密）逐项取证：

| 检查项 | 实证结果 |
| --- | --- |
| 自有会员 API 域名 | **无**。全量域名只有 Firebase（`firebaselogging` / `firebaseremoteconfig` / `app-measurement` / `firebase-settings.crashlytics`）、AdMob/Google 归因、Apple（`itunes.apple.com`、`ocsp` / `crl` / `certs.apple.com`）、CDN `d2qjvbbxrax3kk.cloudfront.net`、Instagram/TikTok 分享 |
| RevenueCat / Adapty / Qonversion | 符号计数 0 |
| `SwiftyStoreKit` / `RMStore` / `TPInAppReceipt` | 0（2.6.2 时代曾有，2.18 已移除） |
| 服务端 `verifyReceipt` | 无。唯一命中是 Firebase Analytics 里的埋点名 `verifyReceipt:` |
| 会员判定位置 | 本地：`Transaction.currentEntitlements` 遍历 + StoreKit 2 `VerificationResult` 校验 + `DazzStoreKitPersistence` 本地 JSON |
| 本地缓存 | 键 `DazzStoreKitTransactionsKey`，内部 `_transactionsDictionary`，串行队列 `com.dazzstorekit.persistence.queue`，方法 `setTransactionsDictionary(_:)` / `StoreKitGetValue(key:)` / `StoreKitSetValue(value:key:)` |
| 门控协议 | `ProductPurchedDelegate`（拼写就是 purched）+ 属性 `purchedDelegate` |
| 商品 ID 来源 | Firebase Remote Config 键 `dazz_products_pro`、`dazz_products_onetime`（不是写死 SKU） |
| 其它 RC 开关 | `admob_enable_unlock`、`double_11_promotion`、`liit_promote_auto_show`、`show_liit_prompt` |

App 自带诊断文案直接印证是纯本地判定：

- `StoreKit has purchase history but no current Pro entitlement`
- `current entitlement failed StoreKit verification`
- `StoreKit access is active but the App's local entitlement was not refreshed (developerIssue)`
- `no Pro record in the current App Store context`
- `purchase storefront differs from current storefront; region change may be involved`

权益不经 HTTP → 响应改写没有可改的对象。

## 二、早前那版 Loon 插件为什么也不该用

仓库里 `plugins/Dazz_VIP.plugin` / `Dazz_VIP_CDN.plugin` 是照早期推断写的：它假设存在 `verifyReceipt` 服务端校验、RevenueCat 订阅态、以及 `dazz.cam` / `camerafilm.com` / `dazzapp.com` 自有接口。
实证结论是这三处**全都不存在**：

- `dazz.cam`、`api.dazz.cam`、`dazzapp.com` 都是 GoDaddy「Coming Soon」停放页（泛解析：任意子域都指向同一批 Linode IP），不是 API；
- 主二进制里没有 `api.revenuecat.com`；
- 收据只在本地用 StoreKit 2 校验，不发往任何服务端。

所以那两个插件保留在仓库只为历史对照，**不提供会员功能**；`README` 里已改为「已弃用 / 见 dazzpro」。

## 三、真正的解法：越狱运行时插件

见 [`dazzpro/`](../dazzpro)：Theos 插件，在 Dazz 进程内把本地门控的布尔结果固定为会员态。

| 层 | 动作 |
| --- | --- |
| L1 | Dazz 自有类里，无参、返回 `BOOL`、名字命中会员词表的 getter → `return YES`；试用/欠费词 → `return NO` |
| L2 | `applyTamper(reason:persistFlag:fromBootstrap:)` 置空，避免注入被判成 `jailbreak_detected` |
| L3 | `dumpMode`（`defaults write com.dazz.camera.vintagecamera DazzProDump -bool YES`）只打印候选，用于跟版 |

安装：装 `dazzpro` 打出的 `.deb`（越狱），或把 `DazzPro.dylib` 注入 IPA 后 TrollStore 安装。构建走仓库里的 GitHub Actions（`.github/workflows/build-dazzpro.yml`，手动触发，产出 deb + dylib）。

## 四、能力边界

- 只改本机运行时判定；服务端若做二次校验（当前实证没有）仍会拦。
- ObjC 暴露的门控可以直接换 IMP；Swift 原生直调、不进 ObjC 方法列表的方法改不到，需要按符号偏移做 inline hook，得先用 `dumpMode` 拿实机日志确认门控点。
- 不动支付、不改价、不伪造 SKU。
- 不要与其它 StoreKit hook 插件（`StoreKitHelper`、`IAPFree` 一类）同时装，会互相覆盖 IMP。

## 五、跟版流程

1. 开 `DazzProDump`，重启 App，翻会员页，看 `log stream --predicate 'subsystem == "com.xitaoyou.dazzpro"'` 里被反复求值的候选；
2. 把真正门控的选择子加进 `kStrong`，或把类名加进 `kBuyClass`；
3. 若候选里根本没有门控点 → 说明走的是 Swift 原生直调，下一步是符号级 inline hook；
4. `defaults delete com.dazz.camera.vintagecamera DazzProDump` 关掉 dump。
