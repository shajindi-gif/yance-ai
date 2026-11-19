# 问衍策 · 模型服务验收清单（运营可见）

更新日期：2026-11-19  
生产基线：`opportunity-20261119-rank01`（Ask 开关见下）

## 1. 生产允许的供应商

| 供应商 | 环境变量 | 默认 Base URL | 常用模型 | 生产 |
|---|---|---|---|---|
| Qwen / 百炼兼容 | `QWEN_API_KEY` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | 允许 |
| DeepSeek | `DEEPSEEK_API_KEY` | `https://api.deepseek.com` | `deepseek-chat` | 允许 |
| OpenAI | `OPENAI_API_KEY` | — | — | **拒绝** |
| Anthropic/Claude | `ANTHROPIC_API_KEY` | — | — | **拒绝** |
| mock | — | — | — | **拒绝** |

默认：`LLM_DEFAULT_PROVIDER=qwen`。任务路由可由 `LLM_TASK_ROUTES` JSON 覆盖。

## 2. 默认任务路由与用途边界

| 任务 | 首选 | 备用 | 允许用途 | 禁止 |
|---|---|---|---|---|
| `chat_answer` | qwen-plus | deepseek-chat | 问衍策：组织已检索片段 | 编资格、假引用、金额承诺 |
| `draft_material` / `long_document` | qwen-plus | deepseek-chat | 材料草稿润色 | 当作资格结论 |
| `extract_criteria` / `judge_eligibility` | deepseek-chat | qwen-plus | 仅辅助抽取 | **不得单独上线裁决资格** |

资格结论唯一事实源：确定性引擎 + 可逐字核对的引用。Ask 输出必须过 `verify_quotes`；无来源 / 引文不符 → 拒答。

## 3. 问衍策开关与限额

| 项 | 变量 / 字段 | 说明 |
|---|---|---|
| 总开关 | `WORKSPACE_ASK_ENABLED` | `false` 时 `POST /api/v1/ask` → 503 |
| 日请求上限 | `llm_daily_call_limit`（默认 100） | 按租户用户计 |
| 输出 token 限额 | `llm_daily_output_token_limit`（见 config） | 预算门禁 |
| 前端状态 | `GET /api/v1/workspace/home` → `ask_enabled` | 控制发送按钮 |

密钥检查（只读、不打印值）：

```bash
docker exec yance-prod-api-1 printenv \
  | grep -E '^(WORKSPACE_ASK_ENABLED|LLM_DEFAULT_PROVIDER|QWEN_API_KEY|DEEPSEEK_API_KEY)=' \
  | sed -E 's/(KEY)=.*/\1=***SET***/'
```

期望：`QWEN_API_KEY` / `DEEPSEEK_API_KEY` 均为 `***SET***`；缺密钥时 Ask/stream 应失败明确，不得静默假成功。

## 4. 启用与回滚（配置热补丁）

激活（验收通过后）：

```bash
# 在当前 release 的 production.env + release.override.json 将
# WORKSPACE_ASK_ENABLED=false → true，然后 recreate api（必要时 agent-worker）
# 详见 docs/releases/workspace-ask-activate-20261119.md
```

回滚：

```bash
# 将 WORKSPACE_ASK_ENABLED 改回 false 并 recreate api
# 前端无需回滚即可显示「问答尚未开放」旁路到检索/画像
```

## 5. 失败降级

1. Qwen 失败 → gateway 按任务路由尝试 DeepSeek（若已配置）。
2. 两侧均失败 / 预算超限 → SSE `error`，对话标 failed；草稿问题可重试（同 `request_id` 不重复计费）。
3. 无检索命中 → 固定拒答文案，不调用模型编造。
4. 仅有未复核采集片段 → 回答前缀标明「采集原文，不是资格认定」。

## 6. Embedding

保留既有 Cloudflare / BGE 路径。问衍策 v1 以词法 / 混合检索为主；**不借机更换 embedding 维度**。
