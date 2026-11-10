# 京东去广告 · 开屏浮窗精简增强版

## 功能与适用范围

- **开屏广告**：识别 `start`、`startup` 和含开屏配置特征的京东主 API 响应，清空广告图与每日显示次数。
- **悬浮广告**：删除首页的 `float`、`bottomXview`、`photoCeiling`、`tabBarAtmosphere` 等营销挂件和广告浮层。
- **营销弹窗**：移除已知 `commonPopup`、`commonPopup_dynamic`、`commonWindows`、`commonTips` 字段。
- **页面精简**：过滤部分推广 `mId` 楼层（订单、物流、我的），不按整域名屏蔽 API。
- **可选工具栏精简**：默认关闭。开启后将“我的”页工具入口限定为脚本中的保留列表；可能隐藏日常入口。

支持旧版明文 JSON 和部分新版 Base64 编码 JSON 响应。只处理 `https://api.m.jd.com/client.action`，跳过超大响应（2MB 以上），未识别到广告字段时原样放行。所有修改在 Loon 设备本地完成，不会上传用户数据。

## 安装

[点此一键导入 Loon](https://www.nsloon.com/openloon/import?plugin=https%3A%2F%2Fraw.githubusercontent.com%2FXitaoyou%2Fxixiduo-loon-plugins%2Fmain%2Fplugins%2FJD-Clean-Enhanced.lpx)

或直接在 Loon 插件列表添加：

```text
https://raw.githubusercontent.com/Xitaoyou/xixiduo-loon-plugins/main/plugins/JD-Clean-Enhanced.lpx
```

需要 Loon 3.5.1 (983)+ 新版脚本语法、已启用 Rewrite/脚本、MitM 并信任 CA 证书。更新插件后完全结束京东 App 再重新启动，必要时清除应用广告缓存。

## 插件设置（默认值）

| 参数 | 默认 | 效果 |
| --- | --- | --- |
| 过滤开屏广告 | 开 | 清理开屏图、显示次数 |
| 过滤悬浮广告 | 开 | 清理首页悬浮和活动挂件 |
| 过滤营销弹窗 | 开 | 移除常见促销弹层 |
| 精简推广楼层 | 开 | 精简订单、物流和我的页面营销楼层 |
| 极简工具入口 | **关** | 隐藏一部分“我的”页功能快捷入口（按需开启） |

## 注意事项与排查

1. **不要同时启用原版 `JD_remove_ads.lpx`** 或其他京东响应改写插件，以免“第一条 Response Script 命中”导致规则冲突。
2. 京东经常调整广告字段和请求格式，具体广告能否彻底消失需要针对**实际 App 版本**实机检查。某些原生/缓存弹窗可能仍然出现。
3. 如果订单、物流、搜索或商品页面内容异常，先关闭「精简推广楼层」，再尝试关闭「过滤悬浮广告」定位；无需关闭整个 Loon。
4. 不对 `api.m.jd.com` 整域名 REJECT，不删除商品图、支付或账号信息。

## 来源

参考 [zbsdsb/loon-adblock-plugins](https://github.com/zbsdsb/loon-adblock-plugins) 的京东新协议 Base64 兼容思路（其仓库声明 MIT），同时参考 RuCu6、Maasea、kelee 的既有去广告理念。此插件和响应脚本是独立适配实现，不是可莉原插件的逐行复制；原插件地址为 [kelee.one/Tool/Loon/Lpx/JD_remove_ads.lpx](https://kelee.one/Tool/Loon/Lpx/JD_remove_ads.lpx)。

