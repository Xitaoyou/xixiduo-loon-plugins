# 西西多的 Loon 插件库

个人自用的 Loon 插件合集。选择需要的插件，点击「一键导入」后在 Loon 中启用。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| 哔哩哔哩去广告 · AI 字幕+自动空降版 | 修复原版插件AI字幕丢失的问题，增加支持自动空降恰饭广告的功能，过滤开屏广告，首页信息流广告和视频下方广告；支持导航精简 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FBilibili-AI-Enhanced.plugin) · [查看文件](plugins/Bilibili-AI-Enhanced.plugin) |
| 芒果TV去广告 · 开屏摇一摇增强版 | 清理开屏、摇一摇及页面推广，支持导航精简 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FMangoTV-Enhanced.plugin) · [查看文件](plugins/MangoTV-Enhanced.plugin) |
| 菜鸟去广告 · 联动完整版 v3 | 清理开屏与页面广告，需配合两个广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCainiao-Adblock-Full.plugin) · [查看文件](plugins/Cainiao-Adblock-Full.plugin) |
| 广告平台补充拦截器 · DNS优先版 v3 | 补充广告平台域名拦截，无需 MitM | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FAdPlatform-Supplement.plugin) · [查看文件](plugins/AdPlatform-Supplement.plugin) |
| 123云盘去广告 · 精简专用版 v6 | 清理应用内广告开关，需配合两个广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Enhanced.plugin) · [查看文件](plugins/123Pan-Splash-Enhanced.plugin) |
| 123云盘去广告 · 完整版 | 清理应用内广告并拦截常见广告域名，可独立使用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Full.plugin) · [查看文件](plugins/123Pan-Splash-Full.plugin) |
| SideStore 刷新助手 | 提供 SideStore 本地回环，辅助刷新侧载应用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名和接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |

## 使用提示

- **哔哩哔哩**：过滤开屏、首页等广告，提供 AI 字幕兼容、导航精简和赞助片段跳过。自动跳过默认关闭，为实验功能，依赖第三方片段数据，效果随视频和客户端版本变化；可能影响播放或字幕。请勿同时启用原版插件。需开启 MitM、MitM over HTTP/2 并信任证书。
- **芒果 TV**：支持开屏、摇一摇及页面广告清理。需开启 MitM、复写并信任证书；更新后完全退出应用再打开。避免与其他芒果 TV 去广告插件重复启用。
- **菜鸟**：联动完整版需同时启用可莉广告平台拦截器和本库的「广告平台补充拦截器」；关闭其他菜鸟去广告插件，避免重复改写。首页及素材清理需要 MitM、复写和受信任的证书。请使用 Loon 分流模式。
- **123 云盘**：精简版需搭配上述两个广告平台拦截器；完整版可独立使用。两版任选其一，接口清理需要 MitM 和受信任的证书。
- **携程**：拦截指定广告域名和接口；接口拦截需要开启 MitM 并信任证书。
- **SideStore**：需要 Loon Build 1007 或更高版本。保持 Loon 和插件连接，在 SideStore 中刷新；本插件不改变签名期限，也不主动执行自动刷新。

不同应用版本和网络环境可能影响效果。若出现异常，可先停用对应插件排查；部分广告缓存可能需要完全退出应用后才会更新。

## 来源与许可

插件及脚本内保留原作者和引用信息；第三方内容的许可和权利以其来源为准。本仓库使用 [MIT 许可证](LICENSE)。
