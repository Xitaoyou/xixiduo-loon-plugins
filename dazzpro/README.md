# DazzPro —— Dazz（Dazz相机）Pro 权益本地解锁

越狱环境下的 Theos 插件。**不是 Loon 插件**，原因见下方「为什么 Loon 做不到」。

## 为什么 Loon 做不到

对 Dazz相机 2.18（`com.dazz.camera.vintagecamera`，App Store id 1422471180）主二进制取证：

| 检查项 | 结果 |
|---|---|
| 自有会员 API 域名 | 无。全部域名只有 Firebase、AdMob/Google 归因、Apple（itunes / ocsp / crl）、CloudFront 素材、Instagram/TikTok 分享 |
| RevenueCat / Adapty / Qonversion | 0 处符号 |
| 服务端 `verifyReceipt` | 无。只有 Firebase Analytics 里一个叫 `verifyReceipt:` 的埋点参数 |
| 会员判定位置 | 本地：`Transaction.currentEntitlements` 遍历 + `VerificationResult` 校验 + `DazzStoreKitPersistence` 本地 JSON |
| 本地缓存键 | `DazzStoreKitTransactionsKey`（内部 `_transactionsDictionary`，队列 `com.dazzstorekit.persistence.queue`） |
| 商品 ID 来源 | Firebase Remote Config：`dazz_products_pro`、`dazz_products_onetime` |

App 自带诊断文案直接印证是纯本地判定：

- `StoreKit has purchase history but no current Pro entitlement`
- `current entitlement failed StoreKit verification`
- `StoreKit access is active but the App's local entitlement was not refreshed (developerIssue)`
- `no Pro record in the current App Store context`

权益不经 HTTP → 响应改写插件没有可改的响应，**抓包一片空白正是这个原因**，不是配置错。

## 插件做什么

运行时把本地门控的布尔结果固定成会员态，三层：

| 层 | 动作 | 说明 |
|---|---|---|
| L1 | 无参、返回 `BOOL` 的 getter | 强词（`Pro`/`Vip`/`Premium`/`Subscribed`/`Purchased`/`Unlocked`/`Entitled`/`Lifetime`/`Forever`/`Membership`）命中 → `YES`；弱词只在购买/会员相关类上生效；试用/欠费词 → `NO` |
| L2 | `applyTamper(reason:persistFlag:fromBootstrap:)` | 置空，避免注入被判成 `jailbreak_detected` 触发降级 |
| L3 | `dumpMode` | 只打印候选（类名 + 选择子 + 返回类型），不改任何东西，用于跟版 |

安全护栏：只处理 `class_getImageName` 含 `DazzCamera` 的类（即主二进制）；跳过 Firebase / Google / SDWebImage / APM 等静态链入的第三方类；`RAW` / `ProRes` / `Progress` / `Property` / `Protect` / `Process` / `Proxy` / `Event` / `Purpose` / `Receipt` / `PurchaseHistory` 等片段一律不碰；`isAppleProRAW*`、`isProgressive`、`isProxy`、`isPurchaseEvent` 等显式黑名单。

## 能力边界（照实说）

- ObjC 暴露出来的那层门控可以直接换 IMP；Swift 原生直调（不走 ObjC 方法列表）的方法改不到。
- Dazz 的会员 UI 与持久化类是 ObjC 可见的 Swift 类（`_TtC10DazzCamera*`），但真正的门控入口是否为 ObjC 方法，需要在真机上用 `dumpMode` 打日志确认。
- 若 `dumpMode` 打出来的候选里没有真正的门控点，下一步是按符号偏移做 inline hook（`Transaction.currentEntitlements` 的 `getter` 或 `VerificationResult` 校验分支），那需要进一步的实机日志。

## 下载现成的包

[Releases · dazzpro-v1.0.0](https://github.com/Xitaoyou/xixiduo-loon-plugins/releases/tag/dazzpro-v1.0.0) 里直接下，不用自己编译：

| 文件 | 用途 |
| --- | --- |
| `dazzpro-rootful.deb` | 有根越狱（unc0ver / checkra1n / Taurine / palera1n 有根），装到 `/Library/MobileSubstrate/DynamicLibraries/` |
| `dazzpro-rootless.deb` | 无根越狱（Dopamine / palera1n rootless），装到 `/var/jb/Library/MobileSubstrate/DynamicLibraries/` |
| `DazzPro.dylib` | TrollStore 或其它注入方式单独用 |

## 构建

### GitHub Actions（推荐，仓库内已配）

`.github/workflows/build-dazzpro.yml` 在 `ubuntu-latest` 上交叉编译（swift-toolchain-linux + theos/sdks），手动触发或改 `dazzpro/**` 自动触发，产出三样：

- `dazzpro-rootful.deb` —— 有根越狱包
- `dazzpro-rootless.deb` —— 无根越狱包（`THEOS_PACKAGE_SCHEME=rootless`）
- `DazzPro.dylib` —— TrollStore / 自签注入用

### 本地 Theos

```bash
export THEOS=~/theos
cd dazzpro
make package FINALPACKAGE=1        # 出 deb
make ARCHS=arm64                   # 出 .theos/obj/arm64/DazzPro.dylib
```

## 安装

**越狱（推荐）**：从 [Releases](https://github.com/Xitaoyou/xixiduo-loon-plugins/releases/tag/dazzpro-v1.0.0) 下对应架构的 deb，用 Filza / Sileo 装，或 `dpkg -i dazzpro-*.deb`；装完重启 App。

**TrollStore**：把 `DazzPro.dylib` 注入 Dazz 的 IPA 后重签安装（`DazzPro.plist` 里已写死 bundle filter `com.dazz.camera.vintagecamera`）。

装完完全退出 Dazz 再打开。日志：`log stream --predicate 'subsystem == "com.xitaoyou.dazzpro"'`。

## 跟版 / 排障

1. `defaults write com.dazz.camera.vintagecamera DazzProDump -bool YES` 后重启 App，看候选列表；
2. 确认哪几个候选是真正的门控（点开会员页时反复求值的那些）；
3. 把选择子加进 `kStrong` / 把类名加进 `kBuyClass`，或对 Swift 原生方法改走 inline hook；
4. 改完 `defaults delete com.dazz.camera.vintagecamera DazzProDump` 关掉 dump。

## 边界

- 只改本机运行时判定，服务端若做二次校验（当前实证没有）仍会拦；
- 不动支付流程、不改商品价格、不伪造 SKU；
- 不要与其它 StoreKit hook 类插件（`StoreKitHelper`、`IAPFree` 一类）同时装，会互相覆盖 IMP；
- 越狱环境本身有风险，`AntiDetector` 检测被置空只是让 App 不当成篡改，不代表设备变安全。