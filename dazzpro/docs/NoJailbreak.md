# DazzPro · 不越狱怎么装

DazzPro 本体是 Theos 插件，但它**不依赖 MobileSubstrate**——实测 `DazzPro.dylib` 的 `LC_LOAD_DYLIB` 只有 libobjc / Foundation / CoreFoundation / UIKit / libc++ / libSystem：

```
ID_DYLIB        -> /Library/MobileSubstrate/DynamicLibraries/DazzPro.dylib
LOAD_DYLIB      -> /usr/lib/libobjc.A.dylib
LOAD_DYLIB      -> /System/Library/Frameworks/Foundation.framework/Foundation
LOAD_DYLIB      -> /System/Library/Frameworks/CoreFoundation.framework/CoreFoundation
LOAD_DYLIB      -> /System/Library/Frameworks/UIKit.framework/UIKit
LOAD_DYLIB      -> /usr/lib/libc++.1.dylib
LOAD_DYLIB      -> /usr/lib/libSystem.B.dylib
BUILD_VERSION   platform=2 minos=15.0.0        # platform 2 = iOS，最低 iOS 15
```

全部改写只用 ObjC runtime 的 `method_setImplementation`，没有 `MSHookFunction`、没有 substrate 头文件。所以它可以直接被塞进 IPA，走**注入 dylib** 这条免越狱路线。

## 先看你的设备能走哪条

| 系统 | 有没有 TrollStore | 路线 | 要不要砸壳 |
| --- | --- | --- | --- |
| iOS 14.0 – 17.0 | 能装（TrollStore 支持区间） | **TrollStore + TrollFools 注入**（最省事） | 不用 |
| iOS 17.1 – 17.x | 不能 | Sideloadly / zsign 自签 + 注入 | 要 |
| iOS 18 / 26 及以上 | 不能 | Sideloadly / zsign 自签 + 注入 | 要 |

判断方法：设置 → 通用 → 关于本机 → 软件版本。TrollStore 的安装方法按系统版本和芯片分好几种（TrollStar / TrollInstallerX / kfd 等），装不上就是装不上，别硬折腾。

## 路线 A：TrollStore + TrollFools（iOS 14.0 – 17.0）

这条路线**不需要砸壳**。TrollFools 的官方限制列表里明确写了「Encrypted App Store applications with bare dynamic library」——只要被注入的是单架构裸 dylib（不带 framework 依赖），加密的 App Store 应用也能注入。我们的 `DazzPro.dylib` 正好是 thin arm64。

1. 装 [TrollStore](https://github.com/opa334/TrollStore)（按你的系统版本选对应安装器）；
2. 从 App Store 正常装 Dazz，确保能打开；
3. 装 [TrollFools](https://github.com/Lessica/TrollFools/releases)（Havoc 源或 GitHub Release 都有）；
4. TrollFools 里选 **Dazz** → 注入 → 选 `DazzPro.dylib`（[Release 下载](https://github.com/Xitaoyou/xixiduo-loon-plugins/releases/tag/dazzpro-v1.0.0)）；
5. 完全退出 Dazz 再打开。

验证：

```bash
# 能连电脑的话
log stream --device --predicate 'subsystem == "com.xitaoyou.dazzpro"'
```

看到 `[DazzPro] loaded com.dazz.camera.vintagecamera dump=0` 就是注入成功。

卸载：TrollFools 里选 Dazz → 移除注入。不动 App 本体。

## 路线 B：Sideloadly 自签 + 注入（任意系统，要砸壳）

重签会把 FairPlay 加密的二进制换成你的证书签的副本，加密段解不开，App 一启动就崩。所以这条路必须先拿到**已解密（砸壳）的 Dazz IPA**。

### B1. 准备砸壳后的 IPA

| 方式 | 说明 |
| --- | --- |
| 别人砸好的包 | 网上流传的「Dazz 破解/去广告 IPA」基本都是砸过壳的，但版本可能旧、可能被塞了别的东西，自己看着办 |
| 越狱设备 `frida-ios-dump` | 需要一台越狱机抓内存镜像，如果你没有越狱机就跳过 |
| 已有 TrollStore 设备 | TrollStore 装过的 App 在 TrollFools 里可以直接注入，等于走路线 A |

### B2. 打进去

用仓库里的 [inject_dylib.py](../tools/inject_dylib.py)（纯 Python，无第三方依赖）：

```bash
python tools/inject_dylib.py \
  --ipa Dazz_decrypted.ipa \
  --dylib DazzPro.dylib \
  -o DazzPro.ipa \
  --dry-run            # 先干跑，确认头部空间够、二进制没加密
```

干跑通过后去掉 `--dry-run` 出包。脚本做四件事：

1. 给主可执行文件加一条 `LC_LOAD_DYLIB @executable_path/Frameworks/DazzPro.dylib`；
2. 删掉旧的 `LC_CODE_SIGNATURE`（重签会重新生成）；
3. 把 `DazzPro.dylib` 拷进 `Payload/DazzCamera.app/Frameworks/`；
4. 删 `_CodeSignature/`，重新打包 IPA。

它会拦三种情况：二进制还带 FairPlay（`LC_ENCRYPTION_INFO_64.cryptid != 0`）、头部空间不够放 load command、重复注入。三种都是报错退出且**不改文件**。

### B3. 签名安装

| 工具 | 命令 / 说明 |
| --- | --- |
| Sideloadly | 直接把 `DazzPro.ipa` 拖进去，Tweak Injection 已经包含在内，不用再单独选 dylib |
| zsign | `zsign -k cert.p12 -p 密码 -m app.mobileprovision -o signed.ipa DazzPro.ipa` |
| AltStore / SideStore | 拖 IPA 进去即可，免费 Apple ID 7 天有效期 |

免费 Apple ID 签的包 7 天过期，过期要重签；付费开发者账号 1 年。

## 两种路线都会遇到的坑

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 启动就闪退，日志里有 `Code Signature Invalid` | 签名不完整 | 用 zsign / Sideloadly 重签，别手改 `_CodeSignature` |
| 启动闪退但签名正常 | App 自带重签检测 | 这是少数派情况，需要额外 hook `NSBundle` 校验，把闪退日志贴出来再补 |
| App 能开但会员还在 | dylib 没被加载 | 看 `log stream` 有没有 `[DazzPro] loaded`；没有就是 load command 没写进去 |
| 加载了但功能没解锁 | 门控点不在 ObjC 层 | 开 dumpMode 拿候选日志，见下方跟版 |
| 字体/相机权限异常 | 换了 bundle id 后系统权限没继承 | 自签时就别改 bundle id |

## 跟版（不越狱也能做）

不越狱就改不了 `com.dazz.camera.vintagecamera` 的 NSUserDefaults，所以 dumpMode 走「编译期默认值」：

1. 编辑 `dazzpro/Tweak.xm` 的 `dz_init()`，把

   ```objc
   BOOL dump = [[NSUserDefaults standardUserDefaults] boolForKey:@"DazzProDump"];
   ```

   临时改成 `BOOL dump = YES;`；

2. 推上去让 Actions 重建（或本地 `make ARCHS=arm64`），拿新 `DazzPro.dylib`；
3. 按上面任一路线注入，打开 Dazz 点开会员页，用 Console.app 或 `log stream --device` 抓 `com.xitaoyou.dazzpro`；
4. 候选日志长这样：

   ```
   [DazzPro] cand _TtC10DazzCamera15DazzProCard isPro [B] want=YES
   [DazzPro] cand _TtC10DazzCamera14PurchaseController hasActiveSubscription [B] want=YES
   ```

5. 把真正控制功能开关的选择子补进 `kStrong`（强词，任何 Dazz 类都生效）或 `kBuyClass`（类名命中才用弱词）；
6. 改回 `BOOL dump = [[NSUserDefaults standardUserDefaults] boolForKey:@"DazzProDump"];`，重新出正式包。

`.github/workflows/build-dazzpro.yml` 支持手动触发，改完 `dazzpro/**` 也会自动跑，产物在 Actions 的 Artifacts 里。
## 边界

- 只改运行时返回值，不伪造收据、不改价格、不碰支付；
- Swift 原生直调（不走 ObjC 方法表）的门控改不到，需要 inline hook，等 dumpMode 的实机日志再定；
- 自签安装的 App 数据容器是新的，需要重新登录 Dazz 账号（如果有）；
- 和别的 StoreKit hook 插件（StoreKitHelper / IAPFree 一类）同装会互相覆盖 IMP。