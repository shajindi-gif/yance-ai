# 实际测试与限制（2026-11-17）

## 环境与隔离

macOS arm64，Python3.12虚拟环境、PostgreSQL18+pgvector、Next16.4.3、Node26。独立UTF-8数据库分别承担完整后端回归和浏览器验收；不使用生产库。模型为mock/离线适配器，后者仅从合成片段返回逐字引用；不代表真实Qwen/DeepSeek的准确率、延迟或可用性。未调用支付、模型、短信、邮件或发票真实供应商。

## 已执行命令和结果

- `APP_ENV=test LLM_DEFAULT_PROVIDER=mock DATABASE_URL=<本机独立库> YANCE_TEST_DATABASE_ACK=<同库名> .venv/bin/pytest`：**486 passed**（29.22秒，6条依赖弃用警告）。最终片段长度限制之后补跑 `pytest tests/test_workspace_ask_v1.py tests/test_v2_llm_budget.py`：**16 passed**。日志分别保存在 `/tmp/yance-workspace-delivery-pytest.log`、`/tmp/yance-workspace-targeted-delivery.log`。
- `.venv/bin/ruff check app tests scripts/seed_workspace_acceptance.py alembic/versions/20261117_0043_workspace_ask.py`：通过。
- 隔离库 `alembic upgrade head`、`alembic downgrade 20261113_0042`、`alembic upgrade head`、`alembic check`：通过，最后返回“No new upgrade operations detected”。这是一次性库结构演练，不是生产数据回退方案。
- `python scripts/export_openapi.py --check`：通过，新增契约已导出。
- `npm run lint`、`npm run typecheck`：通过。
- `npm run test:unit`：**10 passed**，包括分片SSE、断流拒绝、五导航/旧路由和中文空白/Unicode引用定位。
- `API_PROXY_TARGET=http://127.0.0.1:58118 NEXT_PUBLIC_API_URL=/api/v1 npm run build -- --webpack`：通过。默认Turbopack在本机只有WASM绑定时失败，未将该失败写成通过；Webpack使用同一Next版本，CI仍使用原生构建。
- 浏览器结果在本轮最终验收结束后记录于下方；初始配置/夹具错误均未视作业务验收通过。

## 浏览器复现

先按README启动本地API及候选网页，并用仓库的 `tests/seed_v2_browser.py`、`tests/seed_company_wide_browser.py`、`tests/seed_checkout_browser.py` 在同一专用浏览器库生成受限临时文件。不能与完整pytest的累计数据混用。

```bash
cd /Users/shajindi/yance-backup/yance/website
PLAYWRIGHT_EXTERNAL_SERVER=1 \
PLAYWRIGHT_BASE_URL=http://127.0.0.1:53119 \
PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:58118/api/v1 \
YANCE_ASK_FIXTURE=/tmp/yance-workspace-browser.json \
YANCE_V2_FIXTURE=/tmp/yance-workspace-v2.json \
YANCE_ROLES_FIXTURE=/tmp/yance-workspace-roles.json \
YANCE_CHECKOUT_FIXTURE=/tmp/yance-workspace-checkout.json \
npm run test:e2e
```

新用例用真实本地API/数据库走问答、SSE、保存、打开固定版本原文、关闭并恢复焦点、五项主导航、旧任务/运行路由、项目执行记录，覆盖390/768/1440px。外网请求被阻断。已有套件另外覆盖版本评论、双角色、授权导出、反馈入库、订单恢复及失效会话。

## 评测与实际限制

- 本轮16项关键后端用例为工程人员编写的合成离线反例/契约测试，不是独立业务标注。覆盖超时兜底、401不兜底、部分流失败不混接、配额拒绝、模型生产限制、Schema重试、伪造引文及无依据改写剔除、双租户、只读角色、请求重放、时效/地域/损坏快照拦截、失败保留问题。
- 没有真实业务真值或5名客户研究，资格准确率、漏判/误判、真实召回、真实模型首token/成本均**未执行**，不填造分数。引用字面存在测试不等于语义支持率评测。
- `home-latency.json` 为 `seed_investor_demo` 的一个合成租户、本机TestClient+PG18、5次预热100次采样；p95以JSON为准。低于300ms仅说明这一数据规模和本机链路，不证明公网或大规模性能。
- 供应商真实json_schema/stream_options能力、账户余额、合同数据区域及保留设置未执行核验，真实开放前必须补齐。
- 早期完整pytest复用了先前合成库，触发旧全局统计断言；换全新库后486项通过。早期浏览器漏配API端口、混入pytest测试商品及自然过期会话导致失败，均保留为诊断事实，并使用新专用库/有效会话重跑。

## 最终浏览器结果

**54 passed（1.6分钟），0失败、0跳过**。最终日志 `/tmp/yance-workspace-e2e-final-pass.log`。包含Chromium主要旅程及Firefox/WebKit的公开页面和工作区烟测；不是所有真实设备、原生Safari或Edge的完整兼容承诺。新增3个宽度的问答及原文抽屉测试均通过，自动axe扫描无违规（原有9个页面/视口样本加3个问答原文抽屉样本）。截图为隔离合成数据，均显著标注。

复核/导出用例会把项目推进到已批准，重复运行必须生成新的一次性项目，不能把已批准项目重置为草稿。本轮以新的roles-final夹具完成最终全量通过，没有削弱业务校验。最终执行命令中的roles与checkout文件分别使用 `/tmp/yance-workspace-roles-final.json` 和 `/tmp/yance-workspace-checkout-fresh.json`。

应用候选 `195c2c6`，离线CI配置 `9a1ea5e`；PR #2，以未合并PR #1的分支为基线。GitHub上的新一轮CI结果独立于上述本地验收，不把本地通过描述为远端CI通过。

验收环境恢复记录：等待期间合成登录会话和待支付订单自然过期，实际页面正确阻止继续付款；重新签发本地合成会话并创建新测试订单，没有重置旧订单状态。多次完整运行还触发隔离库的注册限流；在该一次性库清理临时 `auth_rate_limit` 后重跑。没有调整生产或应用的限流阈值。
