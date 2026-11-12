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

## 节点订阅

[候选池与精选池规则](docs/Node-Pools.md) · [最近检测状态](subscriptions/free-nodes.json)


| 订阅 | 功能 | 使用 |
| --- | --- | --- |
| 免费节点海外版 | GitHub 海外云测，每国最多 4 个、总计最多 30 个精选出口，保留原订阅地址 | [导入页面](https://xitaoyou.github.io/xixiduo-loon-plugins/#overseas) · [使用说明](docs/Free-Nodes.md) |
| 免费节点大陆版 | 广州每日检测与轮换扩展来源；连通且延迟<1200ms，按服务分别推荐 | [检测状态与导入](https://xitaoyou.github.io/xixiduo-loon-plugins/#mainland) · [使用说明](docs/Free-Nodes.md#免费节点大陆版) |

## 使用提示

- **哔哩哔哩**：过滤开屏、首页等广告，提供 AI 字幕兼容、导航精简和赞助片段跳过。自动跳过默认关闭，为实验功能，依赖第三方片段数据，效果随视频和客户端版本变化；可能影响播放或字幕。请勿同时启用原版插件。需开启 MitM、MitM over HTTP/2 并信任证书。
- **芒果 TV**：支持开屏、摇一摇及页面广告清理。需开启 MitM、复写并信任证书；更新后完全退出应用再打开。避免与其他芒果 TV 去广告插件重复启用。
- **菜鸟**：联动完整版需同时启用可莉广告平台拦截器和本库的「广告平台补充拦截器」；关闭其他菜鸟去广告插件，避免重复改写。首页及素材清理需要 MitM、复写和受信任的证书。请使用 Loon 分流模式。
- **123 云盘**：精简版需搭配上述两个广告平台拦截器；完整版可独立使用。两版任选其一，接口清理需要 MitM 和受信任的证书。
- **京东**：适配新版 Base64/旧版 JSON 接口，默认开启开屏、悬浮、弹窗与推广楼层清理；「极简工具入口」默认关闭。需要 Loon 3.5.1 (983) 或更高、MitM 已开启且证书受信任。请停用可莉原版京东插件及其他相同 API 的京东响应脚本。若京东页面异常，可在插件设置中关闭「精简推广楼层」再测试。详情见 [使用说明](docs/JD-Clean-Enhanced.md)。
- **携程**：拦截指定广告域名和接口；接口拦截需要开启 MitM 并信任证书。
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
