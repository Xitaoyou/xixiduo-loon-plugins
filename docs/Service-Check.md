# 常用服务检测（Loon 测试版）

作者：西西多。检测规则改写自 chen08209/FlClash 的 core/service_check.go、core/service_rules.go，采用 GPL-3.0-only，完整许可证见 COPYING。此版本并非 FlClash 官方发布。

## 安装和运行

1. 在仓库主页点击「常用服务检测」的一键导入，在 Loon 中确认添加。
2. 启用插件，脚本会从 GitHub 自动下载，无需复制本地脚本。
3. 在插件设置中选检测范围：core 是 GitHub、ChatGPT、Claude、Gemini；all 是全部 13 项。
4. 检测路径保持 current：按当前 Loon 规则分别访问各服务。也可设为 DIRECT，或填现有节点/策略组的准确名称，强制全部探测走该路径。错误的节点名可能失败或由 Loon 回退，插件无法核实真实出站。
5. 在脚本列表的通用脚本入口手动运行「检测常用服务」，查看结果。请求超时默认 10 秒，全部检查可能需要更长时间，脚本总预算 100 秒。

插件不新增分流规则、不改当前节点、不需要解密其他 App 的流量，也不需要账号、API Key 或 Cookie。只有手动执行时才发起请求。结果是执行当时的探测状态，非持续监控。

## 与 FlClash 的关系

- 保留服务探测地址和主要判断：Google、GitHub、YouTube Premium、ChatGPT、Claude、Gemini、Netflix、Disney+、Prime Video、Spotify、TikTok、Discord、哔哩哔哩番剧。
- ChatGPT 检查 iOS 入口、trace 和地区合规提示；Claude 通过 trace 地区与上游地区表推断；Gemini 提取页面地区标记。地区表可能过时，需要维护。
- 未能识别页面时显示「未能判定」，不会因收到任意 HTTP 200 就把 AI 标为可用。某些简单连通检查仍按上游使用 HTTP 状态判断。
- Netflix 优先检查其 CDN API，必要时回退到标题页；这不是用账号实际播放电影。Disney+ 使用上游公开浏览器客户端标记进行临时设备握手，令牌仅本次内存使用。
- 每轮最多 4 项服务同时运行。移植版不执行上游的超时自动重试；可手动重测，避免额外请求。
- Loon 请求接口通常先接收完整响应，不能像 FlClash 的 Go 内核那样流式截断；Gemini、Prime Video 页面可能较大。为减少流量，默认只检测 4 个核心服务。
- Loon 不提供同样的出站链路和内核路由版本信息，因此报告仅注明请求指定的路径，不声称知道实际节点。也不能向 Loon 原生仪表盘添加 FlClash 样式的卡片。

## 结果含义

「可达/规则通过」是端点可达或上游地区规则通过，不能保证账号可以登录、发起聊天、购买 Premium 或完整播放。地区不支持、访问受限、运营商受限、超时、检测失败和未能判定分别显示。延迟为相应主探测请求的回调耗时，包含响应接收；多步检测的延迟不是整个检测总耗时，也不是模型回答速度。

与 FlClash 相比，HTTP 指纹、出口、Cookie、DNS、重定向行为及 Loon 已有复写可能改变响应，所以不能保证相同结果。

## 验证和恢复

已运行 node --check 和 10 组模拟场景，覆盖 13 项正常返回、当前路由/强制直连、运营商/地区限制、超时、未知内容、Netflix 回退及并发上限。未在真实 iOS/Loon 环境验证；若检测异常，停用插件即可，不影响原分流配置。

参考源码：https://github.com/chen08209/FlClash/blob/main/core/service_rules.go
