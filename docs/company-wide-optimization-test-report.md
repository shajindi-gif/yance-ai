# 全链路优化验收记录

> 2026-10-28发布状态更新：业务实现1753fa9已随固定发布源码bd0ef29正式上线，数据库0033；此文的“本轮未部署”描述保留为当时本地验收历史。当前状态、恢复证据与已接受的历史结构例外见[正式发布记录](full-release-20261028.md)。

执行日期：2026-10-27至28，Asia/Shanghai。候选源码 **1753fa9**，基线f3c3612。代码已推原功能分支，main未变更；本轮未部署生产、未操作生产订单/反馈/客户资料。

## 环境与测试边界

本机macOS、Python3.12.13、PostgreSQL18+pgvector、Node26.8.1、Next16.4.3、Playwright1.63.0 Chromium。API127.0.0.1:8027、网页127.0.0.1:3027，显式同源转发；独立PG端口55447。使用test/full/browser2/browser3/migration/restore等新建`yance_companywide_*_test`数据库，禁止默认连接和生产名称；邮件关闭、模型默认mock，支付/模型/OSS密钥显式置空。

真实本地接口/数据库测试不等于真实供应商或真实政策质量验收。合同模拟明确标注；截图均为合成资料。夹具凭据只在Git外权限600文件保存，报告不包含令牌/客户内容。自动审批曾因额度限制未执行受保护命令，恢复后已按原方式执行，未绕过审批。

## 已实际执行

|验证|结果|范围与限制|
|---|---|---|
|首次反例|3项按预期失败|人工编辑误扣429、服务端可售属性缺失、空白反馈被接受；修复后三项通过|
|新建空库后端全量|240通过，32.98秒，6条第三方弃用警告；覆盖率81%|当时完整套件；此后新增两个安全/可靠性反例，最新六项针对性回归全部通过，不把两轮拼成一次242项全量|
|最新针对性回归|6通过|人工预算耗尽可编辑/接受建议；新生成仍429；未验收商品拒绝新单；历史未付订单不能新建支付意图；反馈并发幂等与管理处理；硬门槛变化返回409无半成品；同企业viewer反馈私人隔离|
|前端单元|6通过|版本比较4项＋安全回跳/结构化错误2项；已纳入CI。Node提示TS模块按ESM解析，不是测试失败|
|类型检查/构建|通过|42个路由，显式转发本机API，无新增运行依赖|
|最终整轮浏览器|25通过，14.7秒|真实注册登录/撤销、区县资料保存刷新、矩阵来源与补证、人工版本、客户复核和DOCX导出、只读角色403、反馈闭环、旧接口兼容、定价、手机焦点/无溢出等|
|反馈单独复查|2项通过，2.6秒|真实入库后主动丢弃响应，原请求号重试仅一条；平台处理后用户看到状态；恶意next回dashboard。截图滚动位置修正不改变页面代码|
|Ruff/compileall/OpenAPI|通过|app/tests/alembic及新增验证脚本；OpenAPI新增契约快照已更新|
|Alembic check|通过|0033后No new upgrade operations detected；一个head|
|兼容迁移|通过|0032→0033，78张表原有字段与数据摘要不变（排除必变的alembic_version）|
|旧应用/新库|通过|归档f3c3612及当前生产后端源码e58a7c4均在合成新库读历史699元paid订单、提交不带请求号的反馈，新增列为NULL；没有运行生产代码副本或访问生产DB|
|独立备份恢复|通过|299,963字节合成库备份→另一个新库，79表/42行摘要一致。备份0.219秒、恢复0.296秒，仅小型本机样本，不是生产RTO/RPO；序列/外部对象未单独验证|
|正式网页基线|十页及手机只读通过|检查时仍web-20261026-01，公开能力无V2；只读基线不代表本轮新功能已上线|
|源码差异检查|通过|git diff --check；新增源码未命中私钥、访问密钥或JWT模式。不是全仓独立安全认证|

固定1753fa9的[Linux/PostgreSQL16候选验证](https://github.com/shajindi-gif/yance-ai/actions/runs/40585516496)已成功：**242项后端全量通过，33.64秒，覆盖率81%，2条第三方警告**；迁移/模型/OpenAPI、五类评测、Node22前端单元/类型/构建及打包均成功，运行依赖审计0漏洞。headSha=1753fa98b3d62506bf6d48754436ca944b1de088。此记录验证的是固定代码，没有生产访问或部署。详见ci-result.json和ci-summary.txt。

## 两条实际闭环

产品：独立合成企业资料保存/确认，政策/企业事实矩阵，原文引用与补证清单，持久项目及工作稿，人工版本/建议与过期保护，客户自主复核、授权DOCX导出，viewer直接写接口403。企业事实/政策为合成资料，不能当真实政策覆盖或获批证明。

客户支持：真实密码登录回到反馈页→POST入库后故障注入丢失响应→同UUID重试→一条记录→平台管理员处理→提交者刷新看到已处理。另一租户看不到；同租户不同用户也只看本人历史。旧后台无feedback_revision时不调用历史API、不发送请求号，保留原提交并说明进度不可用。

商业：目录及下单共用可售规则，未验收SKU拒绝新单；历史未付订单没有既有支付意图时不能新增在线支付意图，已有在途意图/回调继续按原状态机处理；历史订单/金额不回写。真实供应商与真实交付质量未验收，不称完整商业运营已就绪。

## 评测：合成契约基线，不是业务准确率

复用现有版本化五类评测，全部`data_classification=synthetic`、`review_status=unreviewed`，由确定性目标/scorer执行；没有客户真实业务真值或独立专家复核。61/61完成且通过，错误0：

|类型|版本/样本|本轮可证明的内容|
|---|---|---|
|检索|2026.09.1 / 2|合成词法检索契约，不是真实语义检索召回率|
|资格|2026.10.1 / 53|合成规则判定契约；其中既有AI起草案例未独立复核，不报告真实误判/漏判率|
|引用|2026.09.1 / 2|精确文本片段检查，不是语义支持率|
|幻觉/拒答|2026.09.1 / 2|已给证据上的确定性主张门槛，不是实际模型拒答合理性|
|材料|2026.09.1 / 2|确定性工作稿渲染契约，不代表任意正式申报书质量|

真实检索召回、引用语义支持率、资格误判/漏判、拒答合理性、任务完成率、p95延迟、真实模型/支持成本：本轮没有足够数据，均标未测。客户自主确认可作体验标签，不能替代独立质量真值。各SKU内容验收和真实评测仍是开放收费/扩大范围的门槛。

发布阈值：所有关键租户/角色、交易重放、错误权益、证据失效、人工错误扣额、反馈幂等等反例必须零失败；类型/构建/迁移与恢复必须通过。保留既有确定性评测阈值，不降低阈值去适配失败，不用总体平均分抵消关键错误。真实业务阈值需先建立获准样本基线，当前不虚构。

## 命令与复现

从`yance-ai`执行（DATABASE_URL须指向新建本机测试库；供应商配置置空，不能换成生产URL）：

```sh
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:55447/yance_companywide_full_test
export YANCE_TEST_DATABASE_ACK=yance_companywide_full_test
export EMAIL_ENABLED=false LLM_DEFAULT_PROVIDER=mock
.venv/bin/alembic upgrade head
.venv/bin/alembic check
.venv/bin/pytest --cov=app --cov-fail-under=50 --tb=no
.venv/bin/pytest tests/test_company_wide_closure.py -q --tb=no
.venv/bin/ruff check app tests alembic
.venv/bin/python -m compileall -q app
.venv/bin/python scripts/export_openapi.py --check
.venv/bin/python evals/run_evals.py run --no-persist
```

浏览器使用单独新库：`PYTHONPATH=. .venv/bin/python tests/seed_company_wide_browser.py /private/tmp/<private-fixture>.json`。只在APP_ENV=test、显式DB ACK、Git外文件位置允许执行，凭据权限600。API和网页分别绑定8027/3027，网页构建及启动显式`API_PROXY_TARGET=http://127.0.0.1:8027 NEXT_PUBLIC_API_URL=/api/v1`。Next start在standalone配置下有推荐使用standalone/server.js的提示，本次本机实际完成运行，不改变生产启动规范。

从website执行：

```sh
npm run test:unit
npm run typecheck
API_PROXY_TARGET=http://127.0.0.1:8027 NEXT_PUBLIC_API_URL=/api/v1 npm run build
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3027 PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8027/api/v1 PLAYWRIGHT_EXTERNAL_SERVER=1 YANCE_ROLES_FIXTURE=/private/tmp/<private-fixture>.json YANCE_V2_FIXTURE=/private/tmp/<private-fixture>.json npx playwright test e2e/audit-journey.spec.ts e2e/artifact-comparison.spec.ts e2e/evidence-workspace.spec.ts e2e/frontend-redesign.spec.ts e2e/workspace-roles.spec.ts e2e/legacy-api.spec.ts e2e/legacy-workspace.spec.ts e2e/audience-feedback.spec.ts e2e/pricing-system.spec.ts e2e/company-wide-closure.spec.ts
```

恢复演练：归档旧代码，在仅本机*_test库0032先运行`verify_feedback_compatibility.py seed`；`verify_additive_snapshot.py record`保存旧列摘要；升级0033后verify；旧代码运行compatibility verify。随后pg_dump -Fc→新建库pg_restore --single-transaction，再运行既有`verify_database_snapshot.py`。新增脚本只接受显式本机测试库；不提供可覆盖生产的自动命令。

## 失败历史、限制与证据

首次全量233过/6失败，因反例库不是空白统计基线，且发票夹具选择了任意首个非零SKU；已用新库并固定POLICY_REPORT，后续240通过。首次整轮浏览器24过/1失败，角色测试假定共享项目总计固定2稿；改为检查相对新增版本与具体建议关联版本，在新库最终25通过。未清空原库或删除失败业务记录。

本轮未执行真实支付/退款、真实税票、OSS、真实邮件、外发、申报、生产备份恢复、真实客户访谈/评价、完整PDF分页/中文字体跨系统渲染或真实来源/企业质量评测。此前安全备份/生产回退记录是历史证据，不当本轮生产演练。独立渗透、认证和合规承诺也未验证。

证据目录：`docs/audit-evidence/company-wide-20261027/`，含本地摘要、最终25项用例、评测元数据、兼容/恢复摘要与[手机反馈截图](audit-evidence/company-wide-20261027/feedback-mobile.png)。没有凭据、真实客户数据或原始私密测试日志。


## 2026-10-28 交付与清理

固定候选1753fa9的Linux/PG16验证成功。本机API8027、网页3027及本轮PG55447已停止；合成库、备份与权限受限夹具保留，未清库。旧证据截图未用本轮结果覆盖。交付文档与证据的后续提交不改变候选应用代码，不需要把纯文档提交误称新的运行版本。本轮工程交付完成，尚未执行生产发布与前述外部业务验收。
