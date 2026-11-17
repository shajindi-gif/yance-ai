# 问衍策 v1 · 本地候选交付（2026-11-17）

应用候选实现 `195c2c6`，离线CI配置 `9a1ea5e`，审阅入口 [PR #2](https://github.com/shajindi-gif/yance-ai/pull/2)。

本轮基于 `fix/payment-loop-p0` 的 `6ea4750`，工作分支 `feat/workspace-ask-v1`。PR #1 没有合并，本轮不部署、不推送 main、不改支付/订单/权益/价格。生产只读核对得到 `APP_ENV=production`、`LLM_DEFAULT_PROVIDER=qwen`；没有读取密钥值或发起真实模型调用。

## 已实现

- 修复旧报告模型与供应商不一致：改用 `chat_answer` 任务；保留旧自由报告生产禁用门槛。演示接口模型名称与 gpt-4o-mini 一致。
- 五种任务网关、配置路由、超时/5xx兜底、结构化输出与一次重试、原文引文拦截、无内容遥测，以及原有预算预留/结算。流式输出开始后失败不会混接另一个模型；取消与未知用量保守占额度。
- 生产及预发布拒绝 qwen/deepseek 以外的供应商，包括 mock；OpenAI/Claude仅在 development/test/eval 可用。这是技术限制，不代表供应商合同或登记已核验。
- `GET /api/v1/workspace/home`：当前企业、三卡片、最近项目和本人最近对话。卡片排除旧画像、旧政策版本、潜在符合和失效政策；金额无来源时保持未知。
- `POST /api/v1/ask`：租户/编辑角色校验、请求幂等、每日请求限额；规则路径提供工作区记录，检索路径复用混合检索的词法通道，无需真实向量调用。再次检查地域、时效、版本校验和及片段位置；无来源拒答。
- 对话和消息持久化，跨租户、同租户其他用户不能读取私人对话。完成事件在保存成功后返回；未完成保留问题，超时遗留状态显示为中断。
- 首页问答、企业选择、快速4片段/深度8片段、上传资料、四个预设问题、三张卡与最近记录。引文抽屉复用原文呈现，支持固定版本、空白归一化高亮、Escape和焦点返回。
- 五个主导航，旧路由完整保留；任务/运行/报告/团队等位于上下文入口，项目增加执行记录入口。已登录悬浮助手定位问衍策。

## 与草案不同但必要的边界

引文在原文中存在不能证明结论成立。v1 模型路径只展示经过校验的逐字条款，不把自由改写、匹配分数或旧记录包装为资格认定。模型流仍会解析，但结构化答案先在服务端缓冲、校验，然后按已核验单元发送；不承诺1.5秒首token。政策原文片段最多1200字，完整版本可在抽屉查看。快速/深度代表检索片段上限，不是两种已验证的推理精度。

上传真实复用既有接口；完成后明确说明文件入库不等于已进入本次回答。预设问题不是已完成的六个专业工作流。画像发布、客户复核、材料和授权导出仍沿用原工作区，不自动确认为符合。

没有工商供应商合约，不自动补造企业事实或发布画像。没有确认新的额度与定价，不实施“每天10次”或“30天不限次”。不公示虚构备案号、不作未经合同核实的零保留/不用训练承诺。

## 接口与迁移

新增接口：`GET /workspace/home`、`POST /ask`（POST SSE）、`GET /workspace/conversations/{id}`。前端使用fetch读取SSE，因为原生EventSource不能同时发送POST正文和Authorization头。

新增迁移 `20261117_0043`（基线0042），仅新增 `llm_calls`、`conversations`、`messages` 和索引，不回写历史业务记录。结构回退已在一次性库演练；生产有新对话后不能直接降级删除这些表，应用回退应保留数据及0043。

## 配置

`WORKSPACE_ASK_ENABLED=false` 默认关闭。隔离验收显式设true；生产开放仍需独立验收确认。

`LLM_TASK_ROUTES` 为JSON，每个任务可覆盖完整route对象。例如：

```json
{"chat_answer":{"primary":{"provider":"qwen","model":"qwen-plus"},"fallback":{"provider":"deepseek","model":"deepseek-chat"},"temperature":0,"max_tokens":3000,"stream":true}}
```

| 任务 | 默认首选 | 默认备用 | stream |
|---|---|---|---|
| extract_criteria | deepseek/deepseek-chat | qwen/qwen-plus | false |
| judge_eligibility | deepseek/deepseek-chat | qwen/qwen-plus | false |
| chat_answer | qwen/qwen-plus | deepseek/deepseek-chat | true |
| draft_material | qwen/qwen-plus | deepseek/deepseek-chat | true |
| long_document | qwen/qwen-plus | deepseek/deepseek-chat | true |

全部默认 temperature=0、max_tokens=3000，受已有全局预算限制。配置在进程启动时加载，变更需重启，不宣称热切换。development/test/eval 且默认供应商mock时，各任务默认改为mock；可用离线适配器测试兜底。没有更换embedding模型、维度或索引。本轮问答只启用复用检索器的词法通道，真实向量查询及其费用/召回评测尚未验证；不是已经完成语义检索验收。项目执行记录展示真实关联任务，运行轨迹目前仅提供明确标注的工作区入口，不虚构项目归属。

运营仍需核实企业账号及余额、`QWEN_API_KEY`/`DEEPSEEK_API_KEY`、兼容接口对json_schema与stream_options的支持；秘密只放后端配置。无配置直接失败，不静默生成成功结果。

## 本地预览与复现

本轮运行中的本地预览： http://127.0.0.1:53119/dashboard 。使用隔离合成账号，不能拿生产账号测试。截图见本目录ask/source的三种宽度图片。

复现需要本机PostgreSQL+pgvector、已安装项目依赖，并先创建UTF-8一次性库。以下环境变量中的库必须为localhost测试库；不要填生产连接。

```bash
cd /Users/shajindi/yance-backup/yance/yance-ai
export APP_ENV=test LLM_DEFAULT_PROVIDER=mock WORKSPACE_ASK_ENABLED=true
export DATABASE_URL='postgresql+psycopg://shajindi@127.0.0.1:55479/yance_workspace_browser_20261117_test'
export YANCE_TEST_DATABASE_ACK=yance_workspace_browser_20261117_test
.venv/bin/alembic upgrade head
.venv/bin/python scripts/seed_workspace_acceptance.py
.venv/bin/uvicorn tests.workspace_browser_app:app --host 127.0.0.1 --port 58118
# 另一个终端
cd /Users/shajindi/yance-backup/yance/website
API_PROXY_TARGET=http://127.0.0.1:58118 NEXT_PUBLIC_API_URL=/api/v1 npm run dev -- --webpack --port 53119
```

本轮合成账号的本机登录说明另存 `/tmp/yance-workspace-preview-login.txt`（0600，不入Git）。

合成测试令牌仅保存在`/tmp/yance-workspace-browser.json`（0600），不入Git。测试适配器不由生产入口导入，拒绝非test/mock或非本机测试库。完整浏览器测试另使用仓库既有权限/结账资料生成器，见测试报告。

## 尚未验收与发布条件

真实模型调用、供应商区域/保留合同、登记与公示材料、真实政策质量、5人可用性研究、工商接口和新收费方案仍未验收，不能用合成测试代替。没有生产发布权限变更。计划切换前须固定候选版本、取得渠道兼容性与业务复核证据、验证备份并单独确认。

回退：保持问答开关关闭或恢复原网页/API镜像；保留0043和新对话数据，不改历史订单。采集、支付和原工作区入口沿用现有部署。

[差距清单](audit.md) · [测试结果](test-report.md)
