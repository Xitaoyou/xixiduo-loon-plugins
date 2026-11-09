# 西西多的 Loon 插件库

个人自用的 Loon 插件合集。选择需要的插件，点击「一键导入」后在 Loon 中启用。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| 常用服务检测（测试版） | 图文展示服务连通与地区状态，附可选 IP 类型/质量参考；手动运行 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FService-Check.plugin) · [使用说明](docs/Service-Check.md) |
| 哔哩哔哩去广告 · 字幕修复+自动空降版 | 修复原版插件AI字幕丢失的问题，增加支持自动空降恰饭广告的功能，过滤开屏广告，首页信息流广告和视频下方广告；支持首页精简，搜索页和我的页精简；支持解锁后台播放与投屏 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FBilibili-AI-Enhanced.plugin) · [查看文件](plugins/Bilibili-AI-Enhanced.plugin) |
| 芒果TV去广告 · 开屏摇一摇增强版 | 清理开屏、摇一摇及页面推广，支持导航精简 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FMangoTV-Enhanced.plugin) · [查看文件](plugins/MangoTV-Enhanced.plugin) |
| 菜鸟去广告 · 联动完整版 v3 | 清理开屏与页面广告，需配合两个广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCainiao-Adblock-Full.plugin) · [查看文件](plugins/Cainiao-Adblock-Full.plugin) |
| 广告平台补充拦截器 · DNS优先版 v3 | 补充广告平台域名拦截，无需 MitM | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FAdPlatform-Supplement.plugin) · [查看文件](plugins/AdPlatform-Supplement.plugin) |
| 123云盘去广告 · 精简专用版 v6 | 清理应用内广告开关，需配合两个广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Enhanced.plugin) · [查看文件](plugins/123Pan-Splash-Enhanced.plugin) |
| 123云盘去广告 · 完整版 | 清理应用内广告并拦截常见广告域名，可独立使用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Full.plugin) · [查看文件](plugins/123Pan-Splash-Full.plugin) |
| SideStore 刷新助手 · 兼容版 v2 | 提供 SideStore 设备端点本地回环，兼容 10.7.0.1 / 10.7.0.0，并附端点排查指引 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| SideStore 本机回环 · 官方参数对照测试 | 独立测试版：采用 Loon 官方回环参数，关闭 IPv6 VIF；用于排查 SideStore 0.7 刷新失败，不要与原刷新助手同时启用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Official-Loopback-Test.lpx) · [查看文件](plugins/SideStore-Official-Loopback-Test.lpx) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名和接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |

## 节点订阅

| 订阅 | 功能 | 使用 |
| --- | --- | --- |
| 免费节点（试用） | 至少两项 AI 通过；按国家整理，自动选 AI/流媒体主备 | [一键添加](https://www.nsloon.com/openloon/import?nodelist=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fsubscriptions%2F%E5%85%8D%E8%B4%B9%E8%8A%82%E7%82%B9&name=%E5%85%8D%E8%B4%B9%E8%8A%82%E7%82%B9) · [订阅地址](https://raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/subscriptions/%E5%85%8D%E8%B4%B9%E8%8A%82%E7%82%B9) · [使用说明](docs/Free-Nodes.md) |

## 使用提示

- **哔哩哔哩**：过滤开屏、首页等广告，提供 AI 字幕兼容、导航精简和赞助片段跳过。自动跳过默认关闭，为实验功能，依赖第三方片段数据，效果随视频和客户端版本变化；可能影响播放或字幕。请勿同时启用原版插件。需开启 MitM、MitM over HTTP/2 并信任证书。
- **芒果 TV**：支持开屏、摇一摇及页面广告清理。需开启 MitM、复写并信任证书；更新后完全退出应用再打开。避免与其他芒果 TV 去广告插件重复启用。
- **菜鸟**：联动完整版需同时启用可莉广告平台拦截器和本库的「广告平台补充拦截器」；关闭其他菜鸟去广告插件，避免重复改写。首页及素材清理需要 MitM、复写和受信任的证书。请使用 Loon 分流模式。
- **123 云盘**：精简版需搭配上述两个广告平台拦截器；完整版可独立使用。两版任选其一，接口清理需要 MitM 和受信任的证书。
- **携程**：拦截指定广告域名和接口；接口拦截需要开启 MitM 并信任证书。
- **SideStore**：需要 Loon Build 1007 或更高版本。更新并启用插件后，**断开并重新连接 Loon VPN**，让新的 TUN 路由生效；然后再打开 SideStore 刷新。此版只反射 `10.7.0.1` 与兼容用的 `10.7.0.0` 两个精确 IP，不更改 DNS、代理、MitM 或 IPv6，不主动刷新，也不改变签名期限。若出现 `DeviceEndpointNotInitialized`，请先检查 SideStore `Settings → Connection Config` 中设备 IP 是否为当前实际端点，并在 `Settings → Experimental Features → Network Discovery → Local` 找到带绿勾的 `_remotepairing._tcp.` → `IPv4` 端口，将其填入 `Connection Config` 的 `RemotePairPort`（此端口可能变化），保存后重启 SideStore。注意：Loon 插件不能替 SideStore 自动检测该端口或修复配对文件；不要同时连接其他同类 VPN 隧道。
- **SideStore 官方参数对照测试版**：这是独立诊断插件，**请先关闭原 SideStore 刷新助手**，只启用本测试插件，随后断开并重新连接 Loon VPN。该插件使用 `ipv6-vif = off`、`include-tun = 10.7.0.1/32` 与 `10.7.0.1 = reflect`，会暂时关闭 Loon TUN 的 IPv6 虚拟接口；测试结束后停用并重新连接以恢复原配置。是否能修复 SideStore 0.7 仍需实机验证。

不同应用版本和网络环境可能影响效果。若出现异常，可先停用对应插件排查；部分广告缓存可能需要完全退出应用后才会更新。

## 来源与许可

插件及脚本内保留原作者和引用信息；第三方内容的许可和权利以其来源为准。本仓库使用 [MIT 许可证](LICENSE)。
