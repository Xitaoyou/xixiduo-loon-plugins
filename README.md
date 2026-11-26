# 西西多的 Loon 插件库

个人自用的 Loon 插件和免费节点合集。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| Siri AI 定向代理 · 手动节点轻量版 | 只代理 Siri、Apple Intelligence 的 6 个相关域名；在插件设置手动指定固定节点，无测速、无脚本、无 MITM，不改动去广告配置 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSiriAI-Split-Proxy.plugin) · [使用说明](docs/SiriAI-Split-Proxy.md) |
| 常用服务检测（测试版） | 图文展示服务连通与地区状态，附可选 IP 类型/质量参考；手动运行 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FService-Check.plugin) · [使用说明](docs/Service-Check.md) |
| 哔哩哔哩去广告 · 字幕修复+自动空降版 | 修复原版插件AI字幕丢失的问题，增加支持自动空降恰饭广告的功能，过滤开屏广告，首页信息流广告和视频下方广告；支持首页精简，搜索页和我的页精简；支持解锁后台播放与投屏 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FBilibili-AI-Enhanced.plugin) · [查看文件](plugins/Bilibili-AI-Enhanced.plugin) |
| 芒果TV去广告 · 开屏摇一摇增强版 | 清理开屏、摇一摇及页面推广，支持导航精简 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FMangoTV-Enhanced.plugin) · [查看文件](plugins/MangoTV-Enhanced.plugin) |
| 菜鸟去广告 · 联动完整版 v3 | 清理开屏与页面广告，需配合两个广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCainiao-Adblock-Full.plugin) · [查看文件](plugins/Cainiao-Adblock-Full.plugin) |
| 广告平台补充拦截器 · DNS优先版 v3 | 补充广告平台域名拦截，无需 MitM | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FAdPlatform-Supplement.plugin) · [查看文件](plugins/AdPlatform-Supplement.plugin) |
| 123云盘去广告 · 精简专用版 v6 | 清理应用内广告开关，需配合两个广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Enhanced.plugin) · [查看文件](plugins/123Pan-Splash-Enhanced.plugin) |
| 123云盘去广告 · 完整版 | 清理应用内广告并拦截常见广告域名，可独立使用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Full.plugin) · [查看文件](plugins/123Pan-Splash-Full.plugin) |
| SideStore 刷新助手 · 兼容版 v2 | 常驻基础回环插件；SideStore 0.7+ 刷新时需另启 IPv6 按需兼容开关 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| SideStore IPv6 按需兼容开关 | SideStore 0.7+ 刷新前启用，完成后停用；启用期间全局关闭 Loon TUN IPv6 VIF | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-IPv6-OnDemand.lpx) · [查看文件](plugins/SideStore-IPv6-OnDemand.lpx) |
| SideStore 本机回环 · 官方参数对照测试 | 独立诊断版；启用期间关闭 IPv6 VIF，可单独隔离回环问题 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Official-Loopback-Test.lpx) · [查看文件](plugins/SideStore-Official-Loopback-Test.lpx) |
| 京东去广告 · 开屏浮窗精简增强版 | 兼容京东新版 Base64 响应；清理开屏、首页悬浮挂件、活动弹窗、促销楼层；5 个可选开关，默认保留常用工具入口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FJD-Clean-Enhanced.lpx) · [使用说明](docs/JD-Clean-Enhanced.md) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名和接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |
| 夸克网盘增强 · 清晰度择优+直链抓取 | 播放清晰度择优、门禁字段翻越、并发与限速字段改写、直链抓取导出、会员态字段伪装、广告位清空，全部合成一次遍历；按响应内容判断而非接口路径，夸克改版本也不会静默失效；附接口探测脚本用于跟版本 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FQuarkEnhance.plugin) · [使用说明](docs/QuarkEnhance.md) |
| 一木记账 VIP · 永久会员（2.6.2 实测） | 修改账户信息返回的会员类型为永久会员（vipType=2）、到期时间至 2099 年；2.6.2 有用户实测可用反馈，云端付费功能不保证 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FYimu_Bookkeeping_Loon_2.6.0.plugin) · [查看文件](plugins/Yimu_Bookkeeping_Loon_2.6.0.plugin) |
| 轻听英语 VIP · 权益解锁（1.9.1 / 2.0.6） | 改写启动、购买与促销接口的会员字段：无限在线收听、无限下载、词根/柯林斯词典、促销权益位与购买页会员态；按域名匹配并在脚本内按响应形态分派，2.0.6 的 V3 加密启动响应按开关降级成明文形态再注入；附只读探测脚本 | [Loon 直接导入](loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FQingTing_English_VIP.plugin) · [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FQingTing_English_VIP.plugin) · [使用说明](docs/QingTing-English-VIP.md) |
| 轻听英语 VIP · 权益解锁（CDN 镜像版） | 与上一行内容一致，插件与脚本都走 jsDelivr：raw.githubusercontent.com 打不开时用这版导入 | [Loon 直接导入](loon://import?plugin=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FXitaoyou%2Fxixiduo-loon-plugins%40main%2Fplugins%2FQingTing_English_VIP_CDN.plugin) · [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FXitaoyou%2Fxixiduo-loon-plugins%40main%2Fplugins%2FQingTing_English_VIP_CDN.plugin) · [查看文件](plugins/QingTing_English_VIP_CDN.plugin) |
| Wink VIP · 会员解锁 | 改写 Wink 会员接口：is_vip / use_vip / have_valid_contract 置真，有效期抬到 2999 年，会员子类型与会员组升到最高档，购买页显示已购；按域名匹配并在脚本内按响应形态分派，只抬升已知字段、其余原样保留；附只读探测脚本用于跟版 | [Loon 直接导入](loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FWink_VIP.plugin) · [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FWink_VIP.plugin) · [使用说明](docs/Wink-VIP.md) |
| Wink VIP · 会员解锁（CDN 镜像版） | 与上一行内容一致，插件与脚本都走 jsDelivr：raw.githubusercontent.com 打不开时用这版导入 | [Loon 直接导入](loon://import?plugin=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FXitaoyou%2Fxixiduo-loon-plugins%40main%2Fplugins%2FWink_VIP_CDN.plugin) · [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FXitaoyou%2Fxixiduo-loon-plugins%40main%2Fplugins%2FWink_VIP_CDN.plugin) · [查看文件](plugins/Wink_VIP_CDN.plugin) |
| Dazz Pro · 会员解锁 | 改写 Dazz 会员判定三处入口：App Store 内购凭证校验回写永久内购条目、RevenueCat 订阅态补全、自有接口会员字段抬升；按域名匹配并在脚本内按响应形态分派，只改已知字段、类型跟随原值、有效期只升不降；`verifyReceipt` 按 bundle_id 判归属，其它 App 凭证原样放行；附只读探测脚本用于跟版 | [Loon 直接导入](loon://import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FDazz_VIP.plugin) · [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FDazz_VIP.plugin) · [使用说明](docs/Dazz-VIP.md) |
| Dazz Pro · 会员解锁（CDN 镜像版） | 与上一行内容一致，插件与脚本都走 jsDelivr：raw.githubusercontent.com 打不开时用这版导入 | [Loon 直接导入](loon://import?plugin=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FXitaoyou%2Fxixiduo-loon-plugins%40main%2Fplugins%2FDazz_VIP_CDN.plugin) · [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fcdn.jsdelivr.net%2Fgh%2FXitaoyou%2Fxixiduo-loon-plugins%40main%2Fplugins%2FDazz_VIP_CDN.plugin) · [查看文件](plugins/Dazz_VIP_CDN.plugin) |

## 节点订阅

[候选池与精选池规则](docs/Node-Pools.md) · [最近检测状态](subscriptions/free-nodes.json)


| 订阅 | 功能 | 使用 |
| --- | --- | --- |
| 免费节点海外版 | GitHub 海外云测，每国最多 4 个、总计最多 30 个精选出口，保留原订阅地址 | [导入页面](https://xitaoyou.github.io/xixiduo-loon-plugins/#overseas) · [使用说明](docs/Free-Nodes.md) |
| 免费节点大陆版 | 广州每日检测与轮换扩展来源；连通且延迟<1200ms，按服务分别推荐 | [检测状态与导入](https://xitaoyou.github.io/xixiduo-loon-plugins/#mainland) · [使用说明](docs/Free-Nodes.md#免费节点大陆版) |

## 使用提示

- **哔哩哔哩**：过滤开屏、首页等广告，提供 AI 字幕兼容、导航精简和赞助片段跳过。自动跳过默认开启，为实验功能，依赖第三方片段数据，效果随视频和客户端版本变化；可能影响播放或字幕。请勿同时启用原版插件。需开启 MitM、MitM over HTTP/2 并信任证书。
- **芒果 TV**：支持开屏、摇一摇及页面广告清理。需开启 MitM、复写并信任证书；更新后完全退出应用再打开。避免与其他芒果 TV 去广告插件重复启用。
- **菜鸟**：联动完整版需同时启用可莉广告平台拦截器和本库的「广告平台补充拦截器」；关闭其他菜鸟去广告插件，避免重复改写。首页及素材清理需要 MitM、复写和受信任的证书。请使用 Loon 分流模式。
- **123 云盘**：精简版需搭配上述两个广告平台拦截器；完整版可独立使用。两版任选其一，接口清理需要 MitM 和受信任的证书。
- **京东**：适配新版 Base64/旧版 JSON 接口，默认开启开屏、悬浮、弹窗与推广楼层清理；「极简工具入口」默认关闭。需要 Loon 3.5.1 (983) 或更高、MitM 已开启且证书受信任。请停用可莉原版京东插件及其他相同 API 的京东响应脚本。若京东页面异常，可在插件设置中关闭「精简推广楼层」再测试。详情见 [使用说明](docs/JD-Clean-Enhanced.md)。
- **携程**：拦截指定广告域名和接口；接口拦截需要开启 MitM 并信任证书。
- **轻听英语**：只改 App 本机读到的 JSON。服务端仍按真实账号下发权益，V3 加密报文由服务端密钥生成，插件不伪造密文，只是把 `data_encrypted=1` 的信封降级为明文形态按开关注入权益；若 2.0.6 界面报错或会员态不刷新，关掉「V3 加密响应降级」只留明文接口。付费课程音频若在服务端二次校验，改字段解不开内容。需 Loon 3.5.1 (998)+、MitM、复写并信任证书，装完完全退出轻听英语再打开；不要与「轻听英语 2.0.6 只读诊断」插件同时启用。细节见 [使用说明](docs/QingTing-English-VIP.md)。两种导入方式：`Loon 直接导入`（`loon://import?plugin=` 直达 Loon，Safari 里点一下即可）与 `一键导入`（nsloon 中转页）。若提示下载失败，说明手机侧访问不到 raw.githubusercontent.com，改用下面那行「CDN 镜像版」（插件与脚本都走 jsDelivr）。
- **Wink**：只改 App 本机读到的 JSON。服务端仍按真实账号下发权益，滤镜、模板、AI 素材、导出若在拿到字节时还有服务端二次校验，改字段解不开内容。`api-sub.meitu.com` 是美图全家共用会员域名，同机其它美图 App 会被顺带命中，要隔离就打开「仅改 Wink 自身请求」。部分接口的 `sig` 在客户端算，插件不碰请求签名；接口若哪天变成响应也带签名、客户端会验签，就关掉对应开关。不要与其它 Wink 脚本（qx/surge 的 wink.js 等）同时启用。需 Loon 3.5.1 (998)+、MitM、复写并信任证书，装完完全退出 Wink 再打开。细节与改写前后对照见 [使用说明](docs/Wink-VIP.md)。两种导入方式：`Loon 直接导入` 点在 Loon 里打开，`一键导入` 走 nsloon 中转；下载失败就换 CDN 镜像版。
- **Dazz**：只改 App 本机读到的 JSON。会员判定分散在 App Store 内购凭证、RevenueCat 订阅态、自有接口三处，插件分别处理；`buy.itunes.apple.com/verifyReceipt` 是全机共用渠道，插件按 `receipt.bundle_id` 判归属，不是 Dazz 的凭证一律放行。Dazz 自有 API 域名没有公开渠道可查（`api.dazz.cam` 直接握手失败），所以自有接口这条按域名兜底：域名对上就按内容挑会员字段改。`sig` 类请求签名在客户端算，插件不碰请求侧。不要与其它 Dazz 内购脚本（`iTunes.js`、`revenuecat_multi.js` 同样改写 `verifyReceipt`）同时启用。需 Loon 3.5.1 (998)+、MitM、复写并信任证书，装完完全退出 Dazz 再打开。细节、改写前后对照与跟版步骤见 [使用说明](docs/Dazz-VIP.md)。两种导入方式：`Loon 直接导入` 点在 Loon 里打开，`一键导入` 走 nsloon 中转；下载失败就换 CDN 镜像版。
- **夸克网盘**：只改 App 本机读到的数据。会员专属的服务端签名能力（离线缓存、超大文件直链）和 CDN 限速不受影响；清晰度择优只在服务端已下发的流里排序。直链带会话 cookie、有时效，换客户端会 412。只声明一条响应改写规则，按响应内容识别功能，避免多条规则抢同一条响应。需要 Loon 3.5.1 (998)+、MitM、复写并信任证书，装完完全退出夸克 App 再打开。细节与实测数据见 [使用说明](docs/QuarkEnhance.md)。
- **SideStore**：需 Loon Build 1007+。常驻启用「SideStore 刷新助手」基础插件。SideStore 0.7+ 刷新前，手动启用「SideStore IPv6 按需兼容开关」，完成刷新后再停用；启用期间它会关闭整个 Loon TUN 的 IPv6 VIF，停用后按主配置恢复。Loon 没有公开的 SideStore 刷新事件钩子，因此不能由插件自动在刷新开始/结束时切换。首次启用后断开并重新连接 Loon VPN；Health Check 中 Loon 的 IPv4 utun 应不再带 IPv6 地址。若 Peer IP 已出现但 TCP 探测失败，再检查 RemotePairing 动态端口。插件不固定端口，也不修复配对文件。
- **SideStore 官方参数对照测试版**：独立诊断配置，自带 `ipv6-vif = off` 和官方回环参数。仅用于隔离排查；启用期间同样会关闭整个 Loon TUN 的 IPv6 VIF。

不同应用版本和网络环境可能影响效果。若出现异常，可先停用对应插件排查；部分广告缓存可能需要完全退出应用后才会更新。

## 来源与许可

插件及脚本内保留原作者和引用信息；第三方内容的许可和权利以其来源为准。本仓库使用 [MIT 许可证](LICENSE)。


## SideStore 0.7 及更新版本

SideStore 的新版 `minimuxer` 只接受有 IPv4 且没有 IPv6 地址的本地 VPN `utun`。Health Check 中 Loon 的 `utun4` 同时有 IPv4 `198.19.0.1` 和链路本地 IPv6 `fe80::…`，因此被排除，Tunnel Peer IP 留为 N/A，并报 `DeviceEndpointNotInitialized`。

为避免常驻关闭 IPv6，配置拆为两个插件：常驻启用「SideStore 刷新助手」，它提供本机回环路由与 IP Rewrite；仅在 SideStore 0.7+ 刷新前启用「SideStore IPv6 按需兼容开关」，完成后停用。IPv6 开关插件启用期间会关闭整个 Loon TUN 的 IPv6 VIF，不会只影响 SideStore 的流量。停用后，若没有其他启用插件声明 `ipv6-vif = off`，Loon 按主配置恢复 IPv6 VIF 模式。

开关含义：**开启兼容开关 = 关闭 TUN IPv6 VIF；关闭兼容开关 = 恢复主配置的 IPv6 VIF 设置**。切换后如接口状态未更新，请断开再连接 Loon VPN。恢复 IPv6 时请同时停用旧版刷新助手及「官方参数对照测试版」等仍声明 `ipv6-vif = off` 的插件。

Loon 当前公开配置没有基于 SideStore 前台状态或刷新事件自动切换该设置的入口，因此需要手动启停。首次启用开关后断开并重新连接 Loon VPN，让接口重建。确认 Health Check 的 IPv4 utun 不再带 IPv6、Tunnel Peer IP 已出现且 Device Reachability 可达。若 Peer IP 已出现但 TCP 探测仍失败，再检查 RemotePairing 动态端口。
