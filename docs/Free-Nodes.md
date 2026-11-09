# 免费节点订阅（试用）

作者：西西多。独立节点订阅，不改动现有分流、DNS、去广告插件或机场订阅。

## 添加到 Loon

[一键添加节点订阅](https://www.nsloon.com/openloon/import?nodelist=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fsubscriptions%2Ffree-nodes.txt)（在安装 Loon 的 iPhone 上打开）。只添加独立订阅，不替换配置。

在 Loon 的配置中找到「订阅节点」，新增订阅，名称填「免费节点（试用）」，地址粘贴：

```text
https://raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/subscriptions/free-nodes.txt
```

本订阅已是 Loon 标准节点格式，不需要启用额外的资源解析器。建议使用最新版 Loon。

添加后手动更新一次，再对少量节点测速、试连。把需要的节点加入你已有的代理策略组即可。平时只去广告时，保持原来的规则模式和各用途策略组的 DIRECT 选择；不需要使用这些节点。

不要把此地址当作完整配置导入，也不要替换当前配置。订阅更新后能否自动进入既有策略组，取决于该组是否引用此订阅或使用相应节点筛选。

## 自动更新

- GitHub Actions 计划每 6 小时拉取、解密、过滤并生成订阅，无需开启电脑。
- 在 Loon 的订阅自动更新设置中选择每天一次（若版本使用统一更新设置，则在统一设置中开启）。GitHub 更新与手机拉取是两个独立步骤。
- 可在仓库 Actions → Update free nodes → Run workflow 手动触发生成。
- 源站失败、解密失败、少于 5 个兼容节点或节点数量下降超过 75% 时，任务报错并保留上次发布内容。
- [生成状态](../subscriptions/free-nodes.json)记录最后生成时间与数量，不能代表节点可用率。
- GitHub 定时任务可能延迟；公共仓库连续 60 天没有活动时，定时任务可能自动停用，需在 Actions 中重新启用。

## 范围与限制

公开来源：[pixelor/ecfg](https://github.com/pixelor/ecfg)，备用为 APK 使用的公开 CDN，仅获取 `ecfg6_en`；不访问会员接口，不使用 APK 内的 Gitee 访问令牌，不接入个人机场信息。

试用版仅转换 `vmess://` 与 `hy2://`，排除可识别的受限名称标记，并进一步过滤不支持的传输、未知 Hy2 参数、非 AEAD VMess、要求跳过 TLS 证书验证的条目。VMess 仅接受 TCP/WS，TLS 使用证书验证；带其他必需设置的条目保守跳过。此筛选不能替代来源授权核实。

按协议、服务器、端口、凭据和输出连接参数去重，生成稳定名称。只发布节点行，不接收上游规则、脚本、DNS 或 Host 配置。

**生成成功不等于节点连通。** 本项目不批量试连服务器，不保证速度、地区、服务解锁或持续可用性。公开订阅中的连接信息人人可见，来源为第三方公共节点，适合备用测试。

手机只需偶尔下载订阅，不运行解密脚本。不要把全部节点放进高频自动测速组，以免增加流量与耗电。

转换器与测试见 [scripts/free-nodes](../scripts/free-nodes)，MIT 许可仅适用于本仓库代码，不代表拥有上游节点或其使用授权。

参考：[Loon 节点格式](https://nsloon.app/docs/Node/)、[Loon 订阅](https://nsloon.app/docs/Node/subscription/)、[GitHub 定时任务说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
