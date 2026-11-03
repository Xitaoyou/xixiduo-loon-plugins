# 西西多的 Loon 插件库

个人自用的 Loon 插件合集，按需持续添加。

## 插件列表

| 插件 | 功能 | 安装 |
| --- | --- | --- |
| 哔哩哔哩去广告 · AI 字幕兼容版 | 新增视频底部广告精准过滤，兼顾 AI 字幕；支持导航自定义 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FBilibili-AI-Enhanced.plugin) · [查看文件](plugins/Bilibili-AI-Enhanced.plugin) |
| 芒果TV去广告 · 开屏摇一摇增强版 | 去开屏、摇一摇和视频广告；精简导航、隐藏芒果卡及AI浮窗 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FMangoTV-Enhanced.plugin) · [查看文件](plugins/MangoTV-Enhanced.plugin) |
| 芒果TV去广告 · 奶思原版 | 第三方原版镜像：广告域名拦截、页面及导航清理，规则未经修改 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FMangoTV-Naisi-Original.lpx) · [查看文件](plugins/MangoTV-Naisi-Original.lpx) |
| 123云盘去广告 · 精简版 | 24条补充域名；补拦腾讯素材和新版SDK，搭配可莉广告拦截器 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Enhanced.plugin) · [查看文件](plugins/123Pan-Splash-Enhanced.plugin) |
| 123云盘去广告 · 完整版 | 70条域名规则；补拦腾讯素材和新版SDK，可独立使用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2F123Pan-Splash-Full.plugin) · [查看文件](plugins/123Pan-Splash-Full.plugin) |
| SideStore 刷新助手 | 通过 Loon 本地回环辅助刷新侧载应用 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx) · [查看文件](plugins/SideStore-Refresh.lpx) |
| YouTube 去广告增强版（实验） | 基于可莉原版，补充新版 `player/ad_break` 中插接口拦截；原版首页、Shorts、画中画、字幕等功能继续使用上游脚本 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FYouTube-Enhanced.plugin) · [查看文件](plugins/YouTube-Enhanced.plugin) |
| 携程旅行 · 精准去广告 | 拦截指定广告域名与广告接口 | [一键导入](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FCtrip-Adblock.lpx) · [查看文件](plugins/Ctrip-Adblock.lpx) |

## 芒果TV去广告 · 开屏摇一摇增强版

按芒果 TV iOS 9.4.6 抓包修复**开屏、摇一摇、视频贴片与页面推广**，保留导航精简、芒果卡及 AI 浮窗开关。

**v4 修复根因**：实际开屏接口是 `/json/app/boot`，旧版只匹配 `/json/app/bdboot`，导致开屏广告完整返回。现同时匹配两者，直接返回无广告数据；新增对 `layer.bz.mgtv.com/layer/conf` 的 `shakev2` 摇一摇开关清理，并关闭剩余广告 SDK 开关。

**抓包验证**：`/json/app/boot` 应显示响应头 `X-MangoTV-Adblock: boot-v4`；`/layer/conf` 显示 `shake-v4`。上一份抓包显示顶部频道已从 41 项清理至 4 项，但 App 可能仍使用本地缓存或其他导航数据。脚本「调试日志」可查看底部开关是否实际开启。

**安装**：只启用本版，不与可莉版、奶思版同时运行；确保 Loon MitM、复写及证书有效，更新后完全关闭芒果 TV 再启动。规则基于真实响应测试，实际去广告效果需真机检验。

## 123云盘去广告

**v5 根因（2026-11-03抓包，iOS 3.3.4 Build 3244）**：服务器广告配置实际已经改写成功，但第三方广告在主配置返回之前就下载了素材。`pgdt.ugdtimg.com` 的 1080×1920 推广图片真实返回 200；`sdkquic.e.qq.com/launch` 等新版 SDK 请求未在旧版精准规则中；备用 `api.123panapi.cn/api/user/info` 未被改写，仍返回 `IsShowAdvertisement: true`。

**此次修复**：
- 请求阶段拦截腾讯广告素材及新SDK入口，补充实际抓包命中的 `sdk.zhangyuyidong.cn/sdk/config`、`api.shanghailingye.cn/app/map`、`sdkconf.buluken.com/sdk_config/v3/config`、广告聚合SDK配置等路径。
- 将 `api.123panapi.cn` 加入云盘配置和用户信息改写，避免备用域名漏网。
- 云盘配置成功改写时，响应头含 `X-123Pan-Loon: v5-config`；用户信息改写为 `v5-user`；应用配置改写为 `v5-app`，便于验证。
- **不伪造会员身份**；不屏蔽下载、登录或文件上传，默认继续保留看广告领福利任务。

| 版本 | 专用域名规则 | 使用方式 |
| --- | ---: | --- |
| **精简版** | 24条 | 保留可莉「广告平台拦截器」，只启用精简版 |
| **完整版** | 70条 | 可以不依赖通用广告平台拦截器，只启用完整版 |

**重要**：精简版、完整版二选一；安装/更新后彻底退出 123 云盘再启动。Loon 的 HTTPS 复写需要开启 MitM 并信任证书。若仍有广告，请导出出现广告时的最新请求，核查 `pgdt.ugdtimg.com` 是否仍返回 200，以及 `api.123panapi.cn/api/user/info` 是否具有 `v5-user` 命中标记。配置改写与请求正则通过静态检查，**最终效果需真机验证**。

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
