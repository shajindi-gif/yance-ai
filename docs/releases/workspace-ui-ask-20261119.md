# workspace-ui-ask-20261119 交付对照

生产 API：`opportunity-20261119-rank01` + Ask 补丁挂载  
网站：`website-20261119-ask01`  
Ask 开关：`WORKSPACE_ASK_ENABLED=true`（可回滚）

## 能力对照

| 能力 | 优化前 | 优化后 | 仍劝退点 |
|---|---|---|---|
| 问衍策 | 生产关；首屏「尚未开放」 | 已开；破冰 4 预设；引用/拒答验收通过；reading 日期缺口可摘录 | 日限额 100；多数语料日期未齐 → reading 前缀 |
| 工作台首屏 | 标题空、路径散 | 「选企业·问一句·看机会」三路径 + Ask 主任务 | 无企业须先建档（有意） |
| AppShell | 「证据工作台」重复 | 品牌「衍策」；顶栏工作区名；页脚「可审计」 | 次要导航仍偏多 |
| 机会列表 | 仅匹配% | 实效分 + 同城/窗口/规则/弱匹配标签 | 旧扫描无 `rank_features` 时标签少 |
| 企业画像 | 单页长表 | 4 步、每步保存、省市联动、缺口提示、一键发布 | 未接工商 API |
| 模型 | 文档分散 | `docs/workspace-ask-v1/llm-ops-checklist.md` | OpenAI/Claude 密钥可能存在但生产路由拒绝 |

## 验收摘要

- 合成账号：提问 → SSE `retrieval/token/citations/done`；引用含 `policy_quote`；无依据拒答。
- 根因修复：`_SOFT_CONTEXT` 对齐 `applicability.py` 日期缺口文案；hybrid `evidence_ready=False` 避免空检索。
- 排名：`tests/test_report_ranking.py` 全绿；生产仍跑 rank01（不回退）。
- 截图：`docs/releases/shots/workspace-ask-desktop-20261119.png`、`workspace-ask-mobile-20261119.png`

## 激活 / 回滚

激活已执行（env + mount）。回滚：

```bash
bash /opt/yance/releases/workspace-ask-20261119/rollback.sh
# 网站回滚到 website-20261118-02：去掉 zzzzzzzzzzzz-website-20261119-ask01.conf 后 daemon-reload + restart
```

## Git

- `aebc29f` feat(workspace): icebreaker Ask UX, profile steps, usefulness tags
- `145eb0f` fix(ask): align soft context with live date-gap issue strings
