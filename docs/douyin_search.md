# 视频搜索

`GET /api/douyin/web/search_video` 默认使用 `general` 模式：首屏 `offset=0`
请求 `/general/search/stream/`，后续请求 `/general/search/single/`。
需要旧 `/search/item/` 行为时传 `search_mode=legacy`。新模式的返回卡片结构不同于旧接口。

## 调用和续页

```http
GET /api/douyin/web/search_video?keyword=深圳冲锋衣&count=10&offset=0&search_id=0
```

首屏 `search_id` 可不传、为空或为 `0`，不会向上游伪造搜索 ID。
检查外层 `code` 和内层 `data.status_code` 后，由调用方保存内层 `data.search_id`。
该值来自首次业务块的 `log_pb.impr_id`（回退到 `extra.logid`）。
后续始终回传初始搜索 ID，并用上次响应的 `data.cursor` 填入 `offset`：

```http
GET /api/douyin/web/search_video?keyword=深圳冲锋衣&count=10&offset=10&search_id=首次返回的ID
```

服务不存储搜索进度。关键词、筛选条件和 Cookie 会话保持一致；改变查询条件时重新首屏搜索。
`data.has_more=0` 时处理完本页后结束；为 1 时可继续。如果游标不推进，调用方应停止并检查，
不要按返回的视频数量计算 offset。失败重试保持原 offset 和 search_id。
后续响应的 `data.log_pb.impr_id` 是本页日志 ID，不要用它替换初始 search_id。

## 参数

| 参数 | 默认值与说明 |
| --- | --- |
| keyword | 必填，搜索词 |
| offset | 0；续页填响应 cursor |
| count | 20，浏览器样本是 10 |
| search_id | 空；首屏也接受 0，续页必填初始 ID |
| need_filter_settings | 未传时首屏 1、续页 0 |
| sort_type | 0 综合、1 最多点赞、2 最新 |
| publish_time | 0 不限、1 一天、7 一周、180 半年 |
| filter_duration | 空或 0 不限；0-1、1-5、5-10000；新模式不接受原整数分档 |
| content_type | 1 视频；0 全部、2 图文 |
| search_range | 0 全部、1 最近看过、2 未看过、3 关注的人 |
| search_mode | general；legacy 保留旧接口和整数时长参数 |

## 完整结果

外层继续使用 `{code, router, data}`。内层保留上游字段，包括 `cursor`、`has_more`、
`log_pb`、`extra`、筛选设置和所有类型的结果卡片。
首屏内层 `data` 是各业务块数组按返回顺序合并的结果，不过滤非视频卡片或去重，
避免丢失信息；内层 `stream_chunks` 保留所有原始 JSON 块（含 ack、time_cost 控制块）。
同名顶层字段以最后业务块为准，之前各块的元数据仍可在 stream_chunks 找到。
续页保留原始 JSON 字段，并补充调用方传入的 search_id。
视频通常在内层 `data[i].aweme_info`，调用方按 aweme_id 去重保存。

首屏解析基于已提供样本：JSON 对象及十六进制/空白分隔符；HTTP 传输解码交给 httpx。
未收到 result_status=4 的结束业务块、格式不识别或 JSON 截断时返回错误，不将部分首屏当成功页。
非零上游 status_code 原样返回；调用方不能仅检查外层 code=200。

## 会话一致性和限制

使用配置 Cookie/UA，不轮换随机 UA。识别 Chrome/Edge/Firefox 的版本，消除原有硬编码
Chrome 90 请求头与查询参数的冲突；Referer 使用当前关键词。UIFID 从 Cookie 提取并同步到
请求头和查询参数。s_v_web_id 优先使用 Cookie，缺失时生成并按 Cookie/UA 缓存在当前爬虫
实例内（最多 128 个组合）；同一值同步至 Cookie、fp、verifyFp。重启或多 worker 不共享缓存。
msToken 使用现有生成工具，a_bogus 按本次查询重新计算。

这些是应用层请求一致性处理，不模拟浏览器 TLS 指纹，也不保证签名算法持续有效或绕过风控。
保留基础爬虫现有错误重试；不会自动切换接口或绕过 429。下游应串行分页、限制速率和总量，
发生限流时等待或停止。未用真实登录会话进行在线验证。
