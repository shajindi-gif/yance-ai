# 政策机会报告交付发布 · 2026-11-18

**已上线。** 用户授权「做了然后部署」后，于北京时间 2026-11-18 切换 API/worker 至 `report-20261118-01`。

## 版本

- 源码：`2cd6cdb1e6bbc2ab7c11d97ec98748fc36e5fbf8`
- 应用版本：`report-20261118-01`
- 数据库：保持 `20261117_0043`（本轮无迁移）
- 网页：保持 `website-20261118-02` / `c489512…`；`release.json.api_source` 已更新
- `WORKSPACE_ASK_ENABLED=false` 未开放

## 范围

仅叠加 7 个报告交付相关文件（结构化 ReportCard、引用忠实度门禁、购买/付款校验、MISSING 仍保留 verified quote）。未纳入 Ask / 政策采集脏文件，未改价格或历史订单。

## 验收

- 本机隔离库：注册→扫描→购买→下载 + `content_json.opportunities[*]` 断言通过
- 引用忠实度评测集 / 无来源句门禁单测通过
- 候选镜像补丁 SHA256 与本机一致；候选 citation gate 通过；Trivy HIGH/CRITICAL ignore-unfixed 通过
- 正式：`/api/v1/system/version` 为上述源码与版本；四进程 healthy；官网与采集 active；首页/定价 200

## 回退

```bash
sudo bash /opt/yance/releases/report-20261118-01/activate.sh rollback
```

只恢复切换前四个应用进程镜像；数据库保持 0043，不覆盖交易。
