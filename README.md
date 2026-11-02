# 西西多的 Loon 插件库

个人自用的 Loon 插件合集，按需持续添加。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| 哔哩哔哩去广告 · AI 字幕兼容版 | 新增视频底部广告精准过滤，兼顾 AI 字幕；支持导航自定义 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FBilibili-AI-Enhanced.plugin) · [查看文件](plugins/Bilibili-AI-Enhanced.plugin) |
| 123云盘去广告 · 精简版 | 22条补充域名；需搭配可莉广告平台拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Enhanced.plugin) · [查看文件](plugins/123Pan-Splash-Enhanced.plugin) |
| 123云盘去广告 · 完整版 | 69条域名规则；独立使用，不依赖通用拦截插件 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Full.plugin) · [查看文件](plugins/123Pan-Splash-Full.plugin) |
| SideStore 刷新助手 | 通过 Loon 本地回环辅助刷新侧载应用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| YouTube 去广告增强版（实验） | 基于可莉原版，补充新版 `player/ad_break` 中插接口拦截；原版首页、Shorts、画中画、字幕等功能继续使用上游脚本 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FYouTube-Enhanced.plugin) · [查看文件](plugins/YouTube-Enhanced.plugin) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名与广告接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |

## 123云盘去广告

两版均清理**开屏、插屏、页面横幅**，拦截摇一摇广告请求，并保留登录与文件上传下载。**只启用其中一个。**

| 版本 | 域名规则 | 适合 |
| --- | ---: | --- |
| **精简版（推荐已安装可莉拦截器的用户）** | 22条 | 配合「可莉广告平台拦截器」使用，减少重复规则 |
| **完整版** | 69条 | 不依赖可莉通用拦截器，可独立使用 |

两版的广告接口精准拦截、123云盘服务器广告配置清理和三个功能开关一致；「看广告任务」默认不关闭。开启 Loon MitM 并信任证书后使用，更新后完全退出 123云盘再启动。

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

## 哔哩哔哩：AI 字幕与视频底部广告兼容增强

基于 [可莉原版](https://github.com/Moli-X/Tool/blob/X/Loon/Plugin/Kelee/Bilibili_remove_ads.plugin)（原版配置日期 2026-10-02）。原版「改写视频详情」开启时可能导致 AI 字幕加载失败；关闭后字幕恢复，但视频下方广告也会恢复。

**本版新增「精准清理视频下方广告」**：只删除已识别的 Protobuf 广告字段和推广卡片，不再把整份视频详情解码并重建；其余数据（包括未知字段）原样保留。兼顾 AI 字幕与视频下方广告过滤是设计目标，实际效果需在哔哩哔哩客户端验证。

| 开关 | 默认 | 开启 | 关闭 |
| --- | --- | --- | --- |
| 精准清理视频下方广告 | 开 | 清理已识别广告，尽量保留 AI 字幕 | 视频详情保持原样，广告可能出现 |
| 原版视频详情深度清理 | 关 | 过滤更激进，AI 字幕可能再次失效 | 不运行原版详情重写 |
| 清理互动弹幕 | 关 | 清理互动弹幕，字幕可能受影响 | 保留弹幕及字幕原始数据 |
| 播放器增强 | 关 | 恢复原版播放器优化，可能影响兼容性 | 保持原生播放器 |

**推荐设置**：精准清理视频下方广告＝开；原版视频详情深度清理＝关；清理互动弹幕＝关；播放器增强＝关。不要同时启用精准过滤与原版深度清理，以免重复修改同一响应。首页、开屏、搜索、直播去广告和导航按钮自定义继续保留。

**实现说明**：新增 [video-detail-safe.js](scripts/bilibili/video-detail-safe.js)，支持旧版与新版视频详情、相关推荐接口。仅修改明确广告字段，保留未改写的 Protobuf 字段字节；遇到未知帧格式或解析失败时返回原始响应。已通过合成 Protobuf 样例测试，包括未知字段保留、广告删除、gzip 响应与异常回退；尚需真实客户端验证。

使用前关闭可莉原版插件，启用 Loon MitM 和 MitM over HTTP/2，更新本插件后完全退出哔哩哔哩重新打开。本仓库为第三方修改版，非可莉官方发布。

## 许可证

本仓库使用 [MIT 许可证](LICENSE)。
