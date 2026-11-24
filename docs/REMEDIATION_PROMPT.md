# Yance.ai 验收问题修复指令（Remediation Prompt）

> 依据：[`docs/acceptance/2026-11-24-4adefc7.md`](acceptance/2026-11-24-4adefc7.md)（下称"验收报告"）。
> 用法：把下面「指令正文」整段交给能读写仓库、能执行命令的 AI 代理，在仓库根目录运行。

---

## 指令正文

你是负责修复上线阻塞问题的资深工程师。验收报告列出了 ACC-01 到 ACC-21 共 21 个问题，请按下面的顺序逐个修复，每修一个就提交一次，提交信息以对应编号开头，例如 `fix(ACC-02): ...`。

### 0. 铁律

1. **不碰生产**：不连接生产服务器或数据库，不读取 `.env.prod`，不部署，不发起真实支付。需要在生产上执行的步骤，写进最后的"人工操作清单"，交给人来做。
2. **不伪造**：不编造复核人、评测结果或准确率；不为了让测试变绿而跳过、删除或放宽已有测试。
3. **先证明问题，再修复**：`docs/acceptance/evidence-2026-11-24/` 下的测试目前是"测试通过 = 漏洞存在"。修复时先把断言反过来，确认它失败；修好后再确认它通过；最后移入 `yance-ai/tests/`，作为永久的回归测试。
4. **改动范围最小**：每个问题只改必要的代码，不顺手重构，不改无关文件。
5. **Next.js 规则**：前端改动前先读 `website/AGENTS.md`，Next.js 的用法以 `website/node_modules/next/dist/docs/` 为准，不要凭记忆写。
6. **门禁全绿**：每批修复结束后完整跑一遍第 2 节的门禁，全部通过才能进入下一批。
7. 只在当前分支提交；不合并、不建 PR、不推送到 main。

### 1. 环境准备

本地需要一个启用了 pgvector 的 PostgreSQL 16 一次性数据库。环境变量与 `.github/workflows/ci.yml` 的 backend job 保持一致：

```bash
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://yance@localhost:5432/yance_ci
export YANCE_TEST_DATABASE_ACK=yance_ci
export JWT_SECRET=ci-only-secret-at-least-32-characters
export API_KEY_PEPPER=ci-only-api-key-pepper-at-least-32-characters
export BOOTSTRAP_TOKEN=ci-only-bootstrap-token
export TENANT_PROVISIONING_TOKEN=ci-only-tenant-provisioning-token
```

### 2. 每批结束必须全绿的门禁

```bash
# 后端：在 yance-ai/ 目录下
ruff check app tests alembic
python -m compileall -q app
python scripts/export_openapi.py --check          # 改了接口就重新生成快照并提交
alembic upgrade head && alembic downgrade base && alembic upgrade head && alembic check
pytest --cov=app --cov-fail-under=50              # 通过数必须 ≥ 182，覆盖率不能低于 79%
pip-audit -l                                      # 必须为 0
python evals/run_evals.py run --no-persist

# 前端：在 website/ 目录下
npm ci
npm audit --omit=dev --audit-level=high           # 必须为 0
npx tsc --noEmit
npm run lint                                      # ACC-20 完成之后才有这一步
npm run build
npx playwright test --trace off                   # 后端启动方式参照 ci.yml 的 browser-e2e job
```

---

### 第一批：融资前必须修（P1）

**ACC-01｜升级 Next.js**
- 在 `website/` 下执行 `npm install next@16.4.6 --save-exact`，同时提交 `package-lock.json`。
- 验收标准：`npm audit --omit=dev` 结果为 0，构建通过，7 个 Playwright 测试全部通过。

**ACC-03｜升级 pypdf**
- 把 `yance-ai/constraints-release.txt` 中的 `pypdf==6.21.1` 改为 `pypdf==6.21.4`。
- 把 `yance-ai/pyproject.toml` 中的下限改为 `pypdf>=6.21.4,<7.0`。
- 验收标准：按 CI 方式安装后 `pip-audit -l` 为 0，`test_document_*` 全部通过。

**ACC-02｜登录暴力破解防护**

涉及 `yance-ai/app/services/auth_rate_limit.py` 和 `yance-ai/app/api/routes/auth.py` 中的 `login`。

- 新增按账号的失败计数：键用 `loginfail-acct:{小写邮箱}`，阈值建议 15 分钟 10 次；IP 计数保留不变。
- 登录前同时检查 IP 和账号两个计数，任一超限就返回 429。
- 登录失败时，两个计数都加一。
- 登录成功时，只清除**该账号**的计数，**不再清除 IP 计数**。这是本问题的根因。
- 在代码注释里写明取舍：按账号锁定可能被人恶意利用来锁住别人的账号，所以阈值不要设得太低，并且返回的提示信息不能泄露账号是否存在。
- 回归测试：把 `test_acc_login_bruteforce.py::test_failed_login_limit_is_bypassed_by_interleaving_own_success` 的断言反过来，要求 60 次猜测中一定出现 429；另外新增一条测试，确认攻击者用自己的账号登录成功后，受害者账号的计数不会被清零。

**ACC-07｜消除登录时间差**（与 ACC-02 在同一处改动）
- 查不到用户时，也拿一个模块加载时预先计算好的假哈希跑一次 `verify_password`，让两种情况耗时一致。
- 回归测试：把 `test_user_enumeration_timing` 改为要求两种情况的耗时比小于 2。

**ACC-04｜客户端 IP 识别必须正确**
- 在 `app/main.py` 的 `request_completed` 日志里加上 `client_ip=request.client.host`，方便上线后核对。
- 在 `app/core/config.py` 的生产校验里增加一条：`forwarded_allow_ips` 不能是默认值 `127.0.0.1`。生产环境中 nginx 运行在独立容器里，必须显式列出它的地址或网段。
- 补测试覆盖这条新校验。
- 把以下内容写进 `docs/release-runbook.md` 和人工操作清单："上线后用两个不同的公网 IP 各请求一次，日志中的 `client_ip` 必须是这两个真实 IP，而不是 nginx 的地址。"

**ACC-05｜异地备份**

改造 `yance-ai/ops/backup.sh`：

- 新增环境变量 `YANCE_BACKUP_OFFSITE_URI`。设置了就把 `.dump.gz` 和对应的 `.sha256` 上传过去（用 `ossutil` 或 `rclone`），上传后回读校验 sha256。
- 没设置时脚本以非零状态退出。只有显式设置 `YANCE_BACKUP_OFFSITE_DISABLED=true` 才允许跳过，并输出警告。
- 新增 `yance-ai/ops/restore_drill.sh`：把最新备份恢复到一个临时库，逐表比对行数，打印耗时。

更新 `docs/production-readiness/BACKUP_RESTORE_RUNBOOK.md`：写明当前 RPO 是 24 小时；推荐的升级路径是开启 WAL 归档或迁移到托管 RDS（附时间点恢复）。开通 OSS bucket、配置 cron 都属于人工操作，写进清单，不要自己执行。

**ACC-06｜评测集如实修复（禁止编造）**

数据集位于 `yance-ai/evals/datasets/eligibility_real/`。

1. 修正 `dataset.json`：
   - `data_classification` 改为 `public`（政策原文是公开信息）。
   - 按 `eligibility_eval/dataset.json` 的结构补上 `thresholds`。
   - `review_status` 改回 `unreviewed`，因为没有真实的复核人记录。
2. 修正用词：把案例中的期望值统一成引擎实际使用的词，例如 `INSUFFICIENT` 改为 `MISSING`，`request_missing_facts` 改为 `collect_missing_information`。只改用词，不改判断结论。
3. 处理标注错误：对于规则和标注互相矛盾的案例（例如 `real-zj-fail-rev-mid-025`，题目里的增速条件没有建模成规则），**不要替领域专家决定正确答案**。把这些案例逐一列进 `evals/datasets/eligibility_real/REVIEW_QUEUE.md`，写清楚矛盾在哪里，等专家判定。
4. 修改 dataset 版本号和 case 的 `dataset_version`（loader 会拒绝"版本号相同但内容变了"的数据集），并重新计算 `case_sha256`。
5. 在 `evals/run_evals.py` 或 CI 中加一个步骤专门运行这个数据集，**只报告分数，不作为门禁**。把实际得分写进修复报告。
6. 检查 `README.md`、`INVESTOR_READY_REPORT.md` 和 `docs/data-room/`，凡是提到准确率的地方，统一写成"无经复核的准确率数据"。

---

### 第二批：本季度修复（P2）

**ACC-08｜Agent 租约 fencing**
- 位置：`yance-ai/app/services/agents/harness.py`。
- `claim_next` 成功后，把 `worker_id` 记到 harness 实例上（或放进 contextvar）。
- `_checkpoint` 在已经加了 `FOR UPDATE` 的那行数据上，额外校验 `run.lease_owner == 当前 worker`。不一致时抛出新的 `LeaseLost` 异常。
- `execute` 捕获 `LeaseLost` 后只回滚，不记录失败、不重试。
- 所有调用 `_checkpoint` 的地方都要能拿到 worker 标识。
- 回归测试：把 `test_acc_lease_fencing.py` 的断言反过来，要求抛出 `LeaseLost`。

**ACC-09｜CSP 安全策略**
- 读完 Next.js 16 文档里关于 CSP 和 nonce 的说明后，再在 `website/` 中实现。
- 至少包含：`default-src 'self'`、`frame-ancestors 'none'`、`object-src 'none'`、`base-uri 'self'`；`connect-src` 只放行 API 域名。
- 先用 `Content-Security-Policy-Report-Only` 跑一遍 Playwright，确认控制台没有违规报告，再切换为正式生效的策略。
- 令牌改存 httpOnly cookie 的工作量较大，本轮不做，在修复报告中列为后续项。

**ACC-10｜检索扩展性**
- 新增一个 Alembic 迁移：
  - 启用 `pg_trgm`，对 `policy_chunks.content` 建 GIN trigram 索引。
  - 对 `policy_chunks.embedding` 建 `hnsw (embedding vector_cosine_ops)` 索引（维度 1024，pgvector ≥0.5 支持）。
  - 索引要用 `CONCURRENTLY` 创建，放在 `autocommit_block` 里。
  - 降级脚本中删除这两个索引。
- 修改 `app/services/policies/retrieval.py`：关键词通道不再只取"最新 500 条"，改为在 SQL 里用 trigram 相似度或 `ILIKE` 筛选并排序，再取前 100。
- 新增测试：插入超过 600 个文本块，确认最早插入的那条政策仍能被关键词通道检索到。
- 把 `INVESTOR_READY_REPORT.md` 中"PostgreSQL full-text ranking"的说法改成与实现一致的描述；同时把已经过时的"process-local rate limits"改为"数据库共享限流"。

**ACC-11｜定时运行安全审计**
- 给 `.github/workflows/ci.yml` 增加 `schedule: - cron: "23 1 * * *"`，在定时触发时只运行 `python-dependency-audit` 和前端 `npm audit`。
- 失败通知依赖 GitHub 默认机制即可。

**ACC-12｜缺少 `APP_ENV` 时默认失败即拒绝**
- 在 `yance-ai/Dockerfile` 的运行阶段加 `ENV APP_ENV=production`，这样镜像默认就是生产模式，会触发生产校验。
- 确认开发环境的 `docker-compose.dev.yml`（通过 `.env` 读取，内容来自 `.env.example`）和 CI 都显式设置了 `APP_ENV`，不受影响。
- 新增测试：不设置任何密钥、只设 `APP_ENV=production` 时，配置加载必须报错。

**ACC-13｜付费匹配报告不再给默认分**
- 位置：`yance-ai/app/services/report/matcher.py`。
- 凡是"政策没有该要求时给默认分"的维度，一律改为 0 分，并在 `score_breakdown` 中标记 `"not_evaluated"`。
- PDF 中对应位置显示"未评估"。
- 同步更新相关测试，并在修复报告里说明分数分布的变化。

**ACC-14｜数据删除操作手册**
- 新建 `docs/production-readiness/DATA_DELETION_RUNBOOK.md`，按顺序写清楚：核实申请人身份 → 导出数据（如用户需要）→ 删除数据库中该租户的数据（按外键顺序给出可执行的 SQL 模板）→ 删除 OSS 对象 → 处理备份中的数据（等保留期到期自然过期，并写明期限）→ 回复用户并留存记录。
- 代码层面不新增删除 worker。

---

### 第三批：顺手修（P3）

| 编号 | 改动 | 验证 |
|---|---|---|
| ACC-15 | 删除 `alembic/versions/20260809_0003_alipay_invoice.py` 第 80 行重复的 `op.drop_column("invoices", "total_amount")`；在 CI 中加一步 `alembic downgrade base && alembic upgrade head` | 完整往返通过 |
| ACC-16 | `app/services/oss.py`：OSS 未配置时，依赖注入函数抛出 `HTTPException(503)`，而不是 `RuntimeError` | 新增测试：未配置时调用 `/documents/{id}/complete` 返回 503 |
| ACC-17 | `wechat.verify_notify_signature`：时间戳与当前时间相差超过 300 秒，或无法解析，都拒绝 | 新增单元测试 |
| ACC-18 | `url_fetcher._validated_addresses`：显式拒绝 `64:ff9b::/96` 和 `64:ff9b:1::/48` | 补充测试用例 |
| ACC-19 | `policy_engine/evaluator.py`：证据关卡判定失败时，把 `evidence_source` 改为"模型提议，未核验" | 补充测试用例 |
| ACC-20 | 按 Next.js 16 文档为 `website/` 配置 ESLint（flat config + `eslint-config-next`），在 `package.json` 中加 `lint` 脚本，并加进 CI 的 frontend job；修复由此报出的错误 | `npm run lint` 通过 |
| ACC-21 | 删除 `yance-ai/app/services/vectorstores/`，并确认全仓库没有任何引用 | 测试和门禁全绿 |

---

### 3. 交付物

**① 修复报告** `docs/acceptance/remediation-<日期>.md`，包含：
- 每个 ACC 编号的状态：`已修复` / `部分修复` / `需人工`，附提交 SHA 和验证命令的输出摘要。
- 门禁结果，与验收报告第 5 节逐项对照。
- 测试数量和覆盖率的前后对比。
- ACC-06 真实数据集的实际得分，以及 `REVIEW_QUEUE.md` 中待专家判定的案例数量。

**② 人工操作清单**，放在修复报告末尾，每一项写清楚命令和预期结果：
1. 构建并部署修复后的前端和后端镜像（需要人工批准）。
2. 生产环境的 `.env.prod` 设置 `FORWARDED_ALLOW_IPS`，然后用两个不同公网 IP 核对 `client_ip`（ACC-04）。
3. 开通异地 OSS bucket 和 RAM 权限，配置 `YANCE_BACKUP_OFFSITE_URI` 和 cron；执行一次 `restore_drill.sh` 并记录 RTO（ACC-05）。
4. 安排领域专家处理 `REVIEW_QUEUE.md`，签字后由人把 `review_status` 改为 `reviewed` 并填写 `reviewed_by` 和 `reviewed_at`（ACC-06）。
5. 在生产数据库上评估 HNSW 索引的创建耗时，安排在低峰期执行迁移（ACC-10）。

**③ 复验**：全部完成后，按 `docs/ACCEPTANCE_REVIEW_PROMPT.md` 重新做一次验收，结论更新到新的验收报告中。

现在开始。先完成第 1 节的环境准备，再从 ACC-01 开始。每完成一个编号，输出一行进度：`ACC-xx ✅ 提交 <sha>，验证：<命令> → <结果>`。
