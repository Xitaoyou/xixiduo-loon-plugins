# Siri AI 定向代理 · 手动节点轻量版

**目标：**Loon 开启、使用**自动分流**模式、其余流量按你现有的规则处理（如果想默认直连，在主配置把 FINAL 设为 DIRECT）；只有指定的 Apple Intelligence / Siri 服务域名走你手动选择的**固定节点**。

## 一键导入

[在 Loon 中导入插件](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSiriAI-Split-Proxy.plugin)

直接插件地址：

```text
https://raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/plugins/SiriAI-Split-Proxy.plugin
```

## 必须手动完成的设置

1. 打开上方一键导入链接，添加并启用该插件。
2. **进入 Loon 插件的策略/节点配置，给这个插件的 PROXY 策略指定一个已有、可用的固定海外节点**。不可只安装而不选择：若未指定，Loon 可能退回使用 App 全局首个节点。想切换节点，只需修改插件关联的策略。
3. Loon 保持**开启**，运行模式选择**自动分流（Filter）**，**不是全局直连**。如果你希望其他流量默认直连，需要确保主配置中的 FINAL（兜底）为 DIRECT，且没有其他会让普通流量走代理的规则。
4. 测试时在 Loon 的连接/请求记录中查找下表域名，确认其所选出口是指定的海外节点。

**不要配置 url-test / fallback / load-balance 等自动策略组。** 本插件既不要求也不创建策略组，直接指定固定节点即可。

## 本插件的六条规则

| 域名 | 用途 |
| --- | --- |
| `guzzoni.apple.com` | Siri / 听写 |
| `*.smoot.apple.com` | Siri 搜索，也包括 Spotlight、Safari、News、信息、音乐等 Apple 搜索 |
| `apple-relay.cloudflare.com` | Private Cloud Compute (PCC) |
| `apple-relay.fastly-edge.com` | PCC |
| `cp4.cloudflare.com` | PCC |
| `apple-relay.apple.com` | Apple Intelligence 扩展 |

域名以 [Apple 官方企业网络端点列表](https://support.apple.com/en-us/101555) 为依据。请注意 `smoot.apple.com` 为共用搜索域名，其相关 Apple 搜索请求也会被代理；无法靠域名规则只精确识别 Siri 进程。

## 省电设计

- **不包含 [Script]、[Mitm]、[Rewrite]、[General]、定时任务、节点测速、故障切换。**
- 只包含 `[Rule]` 里的 6 条域名匹配规则。闲置时不会主动发起测速或后台检测。
- 固定节点仅在匹配域名且有请求时被使用；Loon 本身的 TUN/VPN 仍然开启，耗电不等于关闭 Loon。
- **不修改**现有 DNS、去广告插件、节点订阅、主配置或其他策略；现有去广告插件如原本需要 MitM，仍按原方式工作。

## 故障排查

- **域名仍走 DIRECT**：检查 Loon 是否自动分流，是否有主配置里的 `DOMAIN-SUFFIX,apple.com,DIRECT` 等覆盖规则，或 TUN 绕过/其它规则优先匹配。根据 Loon 版本和规则位置，主配置的精确域名规则可覆盖插件。
- **域名走的不是所选节点**：在插件页面重新指定 `PROXY` 对应的固定节点；未指定时可能退回全局首个节点。
- **Siri AI 依旧不可用**：检查节点连通性、请求记录、Apple ID/设备地区及服务可用性。网络分流不能解除国行机型自身的功能限制，也不保证苹果所有相关请求都经过这六个域名。
- **插件异常**：先停用本插件再测试即可回滚，不需要更改原有去广告配置。

## 格式依据

- [Loon 官方插件规则和 PROXY 策略说明](https://nsloon.app/docs/Plugin/)
- [Loon 官方 URL Scheme 导入说明](https://nsloon.app/docs/Scheme/)
- [Apple 官方网络端点](https://support.apple.com/en-us/101555)

版本：2026-11-10 · 手动固定节点轻量版（无自动测速）
