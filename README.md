# 西西多的 Loon 插件库

个人自用的 Loon 插件合集，按需持续添加。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| SideStore 刷新助手 | 通过 Loon 本地回环辅助刷新侧载应用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| YouTube 去广告增强版（实验） | 基于可莉原版，补充新版 `player/ad_break` 中插接口拦截；原版首页、Shorts、画中画、字幕等功能继续使用上游脚本 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FYouTube-Enhanced.plugin) · [查看文件](plugins/YouTube-Enhanced.plugin) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名与广告接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |

## 使用说明

**SideStore 刷新助手**：需要 Loon Build 1007 或更高版本、已完成 SideStore 配对并连接 Wi-Fi。导入并启用插件后，断开 LocalDevVPN，连接 Loon，打开 SideStore 的「My Apps」并点击剩余天数刷新。插件不负责签名或自动刷新，也不会延长签名有效期；应用仍需定期刷新。不同系统和 SideStore 版本可能影响兼容性，失败时可关闭插件并切回 LocalDevVPN。若局域网设备使用 `10.7.0.1`，插件可能影响对其访问。

**携程旅行 · 精准去广告**：导入并启用插件。广告接口规则需要在 Loon 开启 MitM，并在设备上安装和信任 Loon 证书；规则仅针对 `m.ctrip.com` 启用 MitM。插件拦截特定广告域名和接口，不保证移除所有广告；携程更新后效果可能变化，如遇异常可先关闭插件排查。插件规则来自用户提供的文件，原作者标记为 Custom Loon rules，携程图标来自 App Store。

**YouTube 去广告增强版**：基于 [可莉原版](https://github.com/Moli-X/Tool/blob/X/Loon/Plugin/Kelee/YouTube_remove_ads.plugin)（原作者 Maasea、VirgilClyne、Choler、DivineEngine、app2smile），保留原有脚本引用与设置。新增拦截 `youtubei/v1/player/ad_break`，属于实验性兼容修补；**暂停广告尚未确认可过滤**，也不保证全部中插广告被消除。请关闭旧版 YouTube 去广告插件避免冲突，开启 Loon MitM、MitM over HTTP/2、QUIC 回退保护，安装并信任证书。若播放卡顿，禁用增强版并反馈脱敏日志。此项目并非可莉官方发布，原脚本版权归原作者，原版更新不会自动同步插件规则。\n\n## 许可证

本仓库使用 [MIT 许可证](LICENSE)。
