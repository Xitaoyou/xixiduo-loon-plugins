# 西西多的 Loon 插件库

个人自用的 Loon 插件合集，按需持续添加。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| 哔哩哔哩去广告 · AI 字幕兼容版 | 修复 AI 字幕加载失败；保留主要去广告功能，支持自定义导航按钮与兼容性开关 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FBilibili-AI-Enhanced.plugin) · [查看文件](plugins/Bilibili-AI-Enhanced.plugin) |
| SideStore 刷新助手 | 通过 Loon 本地回环辅助刷新侧载应用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| YouTube 去广告增强版（实验） | 基于可莉原版，补充新版 `player/ad_break` 中插接口拦截；原版首页、Shorts、画中画、字幕等功能继续使用上游脚本 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FYouTube-Enhanced.plugin) · [查看文件](plugins/YouTube-Enhanced.plugin) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名与广告接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |

## 使用说明

**SideStore 刷新助手**：需要 Loon Build 1007 或更高版本、已完成 SideStore 配对并连接 Wi-Fi。导入并启用插件后，断开 LocalDevVPN，连接 Loon，打开 SideStore 的「My Apps」并点击剩余天数刷新。插件不负责签名或自动刷新，也不会延长签名有效期；应用仍需定期刷新。不同系统和 SideStore 版本可能影响兼容性，失败时可关闭插件并切回 LocalDevVPN。若局域网设备使用 `10.7.0.1`，插件可能影响对其访问。

**携程旅行 · 精准去广告**：导入并启用插件。广告接口规则需要在 Loon 开启 MitM，并在设备上安装和信任 Loon 证书；规则仅针对 `m.ctrip.com` 启用 MitM。插件拦截特定广告域名和接口，不保证移除所有广告；携程更新后效果可能变化，如遇异常可先关闭插件排查。插件规则来自用户提供的文件，原作者标记为 Custom Loon rules，携程图标来自 App Store。

**YouTube 去广告增强版**：基于 [可莉原版](https://github.com/Moli-X/Tool/blob/X/Loon/Plugin/Kelee/YouTube_remove_ads.plugin)（原作者 Maasea、VirgilClyne、Choler、DivineEngine、app2smile），保留原有脚本引用与设置。新增拦截 `youtubei/v1/player/ad_break`，属于实验性兼容修补；**暂停广告尚未确认可过滤**，也不保证全部中插广告被消除。请关闭旧版 YouTube 去广告插件避免冲突，开启 Loon MitM、MitM over HTTP/2、QUIC 回退保护，安装并信任证书。若播放卡顿，禁用增强版并反馈脱敏日志。此项目并非可莉官方发布，原脚本版权归原作者，原版更新不会自动同步插件规则。
## 哔哩哔哩去广告 · AI 字幕兼容版

基于 [可莉原版](https://github.com/Moli-X/Tool/blob/X/Loon/Plugin/Kelee/Bilibili_remove_ads.plugin)（原版配置日期：2026-10-02），针对原版可能导致 **AI 字幕无法加载** 的问题进行兼容性调整。用户反馈新版默认配置已恢复 AI 字幕加载。

### 与可莉原版有什么不同？

1. **优先保护 AI 字幕**：默认不改写弹幕字幕、视频详情及播放器的相关响应，降低字幕加载失败的风险。
2. **尽量保留去广告**：开屏、首页信息流、搜索、直播等原版过滤继续保留；视频详情的部分推广和互动弹幕可能恢复。
3. **增加独立开关**：可选择是否隐藏底栏发布、会员购、动态、消息、直播及顶部游戏中心，也可指定保留哪些顶部频道。
4. **按需恢复强力清理**：视频详情深度去广告、互动弹幕清理、播放器增强可单独开启；功能更强，但可能再次影响 AI 字幕。
5. **保留原版功能**：评论净化、评论加载优化、空降助手、日志等级等继续提供。

### 默认设置与取舍

| 设置 | 默认 | 开启时 | 关闭时 |
| --- | --- | --- | --- |
| 清理互动弹幕 | 关 | 清理互动弹幕，AI 字幕可能异常 | 保护 AI 字幕，可能保留互动弹幕 |
| 视频详情深度去广告 | 关 | 更彻底清理详情页推广，字幕可能异常 | 详情页兼容性更好，可能出现少量推广 |
| 播放器增强 | 关 | 恢复原版播放器优化，可能影响字幕 | 保持原生播放器行为 |
| 精简顶部频道 | 关 | 仅保留指定频道 | 保留原有频道 |
| 隐藏底部发布、会员购 | 开 | 隐藏对应入口 | 显示对应入口 |
| 隐藏底部动态、消息、直播 | 关 | 隐藏对应入口 | 显示对应入口 |
| 隐藏顶部游戏中心 | 开 | 隐藏入口 | 显示入口 |
| 空降助手 | 关 | 跳过第三方标记的视频内广告，可能误跳 | 不自动跳过 |

### 安装和注意事项

使用上方「一键导入」，**关闭原版可莉哔哩哔哩插件，避免重复改写**；启用 Loon MitM 和 MitM over HTTP/2，安装并信任证书。更新后完全退出哔哩哔哩再打开。若 AI 字幕再次异常，先确认三个兼容性开关（互动弹幕清理、视频详情深度去广告、播放器增强）均为关闭状态。

此版本由本仓库维护，并非可莉官方更新；原版脚本仍由可莉上游提供，更新兼容性可能随哔哩哔哩版本变化。

## 许可证

本仓库使用 [MIT 许可证](LICENSE)。
