# Phase 0 Changelog — Backup + Audit

日期：2026-09-02

基线提交：`8cdf0e6`

工作分支：`feature/investor-grade-upgrade`

## Git 安全

- 审计开始时 `main` 相对 `origin/main` ahead 5；
- 未提交内容只有本轮创建的 `docs/investor-readiness/`；
- 创建保护分支 `backup/pre-investor-grade-upgrade-20260902`；
- 创建并切换 `feature/investor-grade-upgrade`；
- 未执行 reset、checkout 丢弃、clean、删除或历史重写。

备份分支固定的是开始审计时的 Git 提交。未跟踪审计文档保留在工作树，并在 feature branch 作为 Phase 0 交付提交。

## Phase 0 输出

- `00_CURRENT_STATE.md`：当前真值与 P0；
- `01_ARCHITECTURE_AUDIT.md`：系统边界和架构风险；
- `02_PRODUCT_AUDIT.md`：产品闭环；
- `03_FRONTEND_AUDIT.md`：Next.js、真实性和体验；
- `04_BACKEND_AUDIT.md`：API、支付、任务和数据边界；
- `05_AGENT_RAG_AUDIT.md`：Agent/RAG/Eval；
- `06_SECURITY_AUDIT.md`：威胁与安全 Gate；
- `07_DATA_MODEL_AUDIT.md`：schema、migration 和多租户；
- `08_PRODUCTION_RISK.md`：P0–P3 风险登记；
- `09_INVESTOR_DUE_DILIGENCE_GAPS.md`：数据室和尽调缺口；
- `10_UPGRADE_ROADMAP.md`：12 周/中期成熟度路线；
- `11_AGENT_WORKFLOW_AUDIT.md`：14 步 Golden Journey；
- `12_AGENT_ARCHITECTURE_RAG_EVAL_SPEC.md`：Harness/RAG/Policy/Eval 规格；
- `13_ENTERPRISE_SAAS_READINESS_AUDIT.md`：第 11–40 节专项差距；
- `14_PHASED_IMPLEMENTATION_PLAN.md`：正式 Phase 0–11 工程计划；
- 本文件：Phase 0 执行证据。

## 实际验证结果

| 命令/检查 | 结果 | 备注 |
|---|---|---|
| `npm ci` | PASS | 安装 27 packages；审计提示 3 High |
| `npm run build` | PASS with warning | Next.js 14.2.35；25 routes；Google Fonts 优化失败 |
| standalone artifact | FAIL | `.next/standalone` 不存在，Dockerfile 与 Next config 不一致 |
| `npm audit --omit=dev` | FAIL | Next.js、PostCSS、nanoid：3 High |
| Python env | PASS | Python 3.12.13，72 packages |
| `.venv/bin/pytest --cov=app` | PASS, weak | 5 passed；总覆盖率 45%；核心路径低覆盖 |
| `.venv/bin/ruff check .` | FAIL | 290 errors |
| `evals/run_evals.py` | 2/2 structural only | 只验证 case keys，不代表模型准确率 |
| benchmark V2.1 | FAIL | 硬编码个人 `env.prod` 绝对路径 |
| `alembic heads/history` | PARTIAL | 单一 head `20260817_0008`，链可解析 |
| base→head migration | NOT RUN | 本机 PostgreSQL 无响应，Docker daemon 未运行 |

## 新确认的阻断项

1. 公司财务标识作为后端配置默认值提交并可由付款接口返回；
2. 根 `.env.example` 和后端 example 因 ignore 规则没有进入 Git 跟踪；
3. 前端 Dockerfile 需要 standalone，但构建配置不生成该产物；
4. 前端生产依赖有 3 个 High，自动建议包含 breaking framework upgrade；
5. root GitHub Actions 不存在，嵌套 `yance-ai/.github/workflows` 不会作为仓库 workflow 运行；
6. Ruff、benchmark、migration verification 都不能作为当前 release evidence；
7. demo payment、Mock Agent 和 seed paid/invoice 会污染商业/投资人指标。

## 未修改内容

- 无业务代码修改；
- 无数据库 migration；
- 无生产 API、支付、LLM 或云资源调用；
- 无 UI 重设计；
- 无真实客户或指标数据生成。

## Phase 1 准入

Phase 1 从 P0 Stability & Security 开始。首个 implementation plan 必须先列出支付/权益、租户、migration drift、PDF/HTML、资格硬门槛、secret/财务配置和声明真实性涉及的精确文件与测试；在 P0=0 前不进入 Design System。
