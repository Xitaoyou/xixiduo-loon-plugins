# 西西多的 Loon 插件库

个人自用的 Loon 插件合集，后续会按需添加其他插件。作者：西西多。

## 插件目录

### SideStore 刷新助手

通过 Loon 的本地回环功能处理 SideStore 发往 `10.7.0.1` 的流量，方便在连接 Loon 时刷新侧载应用。该插件已在作者设备上测试可用；不同 iOS、SideStore 和 Loon 版本可能有不同表现。

- [一键导入 Loon](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FSideStore-Refresh.lpx)
- [查看插件文件](plugins/SideStore-Refresh.lpx)
- [插件原始链接](https://raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/plugins/SideStore-Refresh.lpx)

**要求：** Loon Build 1007 或更高版本，已完成 SideStore 和设备配对，并保持 Loon 连接。按照 SideStore 的要求连接 Wi-Fi。

**使用方法：**

1. 在 iPhone 或 iPad 上点击「一键导入 Loon」，在 Loon 中确认导入并启用插件。
2. 断开 LocalDevVPN，连接 Loon 并确保插件已启用。
3. 打开 SideStore，在「My Apps」中点击应用旁的剩余天数进行刷新，确认天数更新。
4. 如刷新失败，可检查版本、配对和网络；必要时关闭插件并切回 LocalDevVPN。

插件提供本地回环，不负责签名或自动刷新，也不会延长签名有效期。SideStore 和侧载应用仍需在到期前定期刷新。若局域网设备使用 `10.7.0.1`，该插件可能影响对其访问，可暂时关闭插件。

## 许可证

本仓库使用 [MIT 许可证](LICENSE)。
