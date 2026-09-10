# 精选栏目连续拉取

本地端点：`GET /api/douyin/web/fetch_module_feed`。
上游端点：`POST https://www.douyin.com/aweme/v2/web/module/feed/`，参数在 URL 中，请求体为空。

## 抓包确认的规律

用户提供的六份 `fetch(...)` 请求依次使用 `refresh_index=5,6,7,8,9,10`。
这些文件不包含服务端响应 JSON，不能据此确定列表字段和结束标志。

| 参数 | 六份抓包中的行为 | 连续拉取填写方式 |
| --- | --- | --- |
| `module_id` | 固定 `3003101` | 同一栏目保持不变 |
| `tag_id` | 固定 `300215` | 同一栏目保持不变 |
| `count` | 固定 `20` | 建议先使用 20；不保证实际返回数量 |
| `refresh_index` | 每次增加 1 | 成功处理一批后加 1，失败重试不变 |
| `pull_type` | 固定 `2` | 此下拉场景保持 2 |
| `filterGids` / `presented_ids` | 全部为空 | 保持默认空值，不自行累计作品 ID |
| `refer_id` / `refer_type` | 空字符串 / `10` | 保持默认值 |
| `webid` / `install_time` | 保持不变 | 使用同一浏览器会话的值；不要每次生成或填写当前时间 |
| `fp` / `verifyFp` | 相同且固定，与 Cookie 的 `s_v_web_id` 一致 | 由 Cookie 提取，或通过 `verify_fp` 显式指定同一值 |
| `uifid` | 保持不变 | 由配置 Cookie 的 `UIFID` 提取 |
| `msToken` | 六次请求出现三个不同值 | 由代码动态获取，不当作分页游标 |
| `a_bogus` | 每次变化 | 按当前 POST 查询参数重新计算 |
| `x-secsdk-csrf-token` | 保持不变 | 如需传入，使用同一会话的请求头值 |

`webid` 和 `install_time` 未填写时不上送；现有抓包全部包含这两个字段，
因此“可选”仅表示本地接口允许省略，不代表已验证上游不需要。
指纹优先级为：`verify_fp` 参数 → `s_v_web_id` 参数 → Cookie 的 `s_v_web_id` → 自动生成。
选定值同步写入本次上游请求的 Cookie `s_v_web_id`、查询参数 `fp` 和 `verifyFp`，不修改配置文件。
自动生成的指纹按原始配置 Cookie、User-Agent 和 webid 的组合缓存，同一组合连续翻页复用。
缓存属于当前爬虫实例，最多保留 128 个组合，超过后淘汰最早插入项；服务重启、不同 worker、
配置 Cookie/User-Agent 或 webid 改变时不保证沿用。需要跨进程稳定时，请显式传入指纹或放入配置 Cookie。
该回退保证请求中的指纹一致，不保证自动生成的指纹一定被抖音接受。
不要将抓包中的会话凭据提交到代码或文档。

## 续取示例

以下示例从已观察到的序号 6 开始；不是证明首次加载从 6 开始。
本地默认值 1 仍保留兼容，但首次加载的实际序号和 pull_type 尚无抓包确认。

```http
GET /api/douyin/web/fetch_module_feed?module_id=3003101&tag_id=300215&count=20&refresh_index=6&pull_type=2
GET /api/douyin/web/fetch_module_feed?module_id=3003101&tag_id=300215&count=20&refresh_index=7&pull_type=2
GET /api/douyin/web/fetch_module_feed?module_id=3003101&tag_id=300215&count=20&refresh_index=8&pull_type=2
```

实际使用时，给上述请求附上相同的 `webid`、`install_time` 及所需的会话参数。
服务不保存调用方的翻页进度，也不自动累加序号：调用方应串行请求，检查上游业务结果，
去重保存成功后再推进序号。网络或 HTTP 错误重试当前序号；不要因本地包装的 `code=200`
就认定上游业务一定成功。

按作品 ID 去重，并为采集任务设置数量/时间上限和连续无新增批次上限。
没有响应样本前，不假定 `has_more`、`cursor` 或特定列表字段一定存在。
该请求序号的递增规律不保证 Feed 稳定排序、无重复或能遍历整个栏目。
