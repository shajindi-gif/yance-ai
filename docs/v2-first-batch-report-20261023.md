# V2第一批实现与验收（2026-10-23）

起点：feature/investor-grade-upgrade / 4adefc7；起始两个方案文档未跟踪，已保留。实现限唯一源码目录，本轮未连接生产，未发布，未真实交易/外发/申报。生产版本仍以10月21日记录为历史事实，不在本轮重新断言云端状态。

## 已完成

- 现有企业资料确认、扫描、资格结果、项目、材料生成/退回/编辑/复核、DOCX/XLSX/JSON授权导出通过完整隔离API路径复验，延续现有模块。
- 新增中文资格矩阵、规则级原文展开、画像版本/自述来源提示、幂等补证待办和来源变化提示；矩阵全宽，手机横向滚动限制在表格容器内。
- 就绪检查改为资格状态白名单；当前规则/事实/硬条件原文不一致时要求重新扫描。生成指纹绑定输入，审批和批准稿交付重验。项目修改父行锁保护并发；不删除历史批准记录。
- 新增15项合成单元反例，扩充原完整集成路径断言。浏览器种子显式要求APP_ENV=test、独立库名及ACK，凭据只写仓库外600权限文件；CI新增夹具步骤，避免新用例默认跳过。
- 数据契约：v2-evidence-contract.md；代码映射及依赖：v2-gap-map-20261023.md。

## 实际环境与结果

本机macOS/Apple Silicon，Python3.12.13、PostgreSQL18+pgvector、Node/Next本地锁定依赖、Playwright Chromium。数据库全新初始化，本机127.0.0.1:55440；最终库yance_v2_acceptance_test。API8023、网页3019仅用于隔离验收。合成数据，不含客户备份；LLM_DEFAULT_PROVIDER=mock、EMAIL_ENABLED=false。PG18结果不能冒充生产PG16验证。

- 最终完整后端：197 passed，6个第三方弃用警告，24.34秒；覆盖率79.66%。包含原业务与支付/权限回归，非真实供应商测试。
- 既有5组61条合成评测全部通过。样本未人工业务标注，不代表真实召回、引用语义准确率或资格误判率。
- 两线程真实API：同规则补证仅创建一项；同工作稿并发编辑[201,409]；来源/文件变化阻断旧批准稿下载和提交；viewer403、跨租户404。
- OpenAPI检查通过，Alembic check无新增变更；新库从零升级到0027。
- 前端TypeScript与生产构建通过；最终真实浏览器用例1项通过（2.6秒），含矩阵引用、待办持久化/幂等、生成工作稿、桌面/手机和键盘焦点；截图已人工查看，桌面4列可见。结果见audit-evidence/v2-20261023。

## 可复现命令

所有数据库须显式新建，先确认本机隔离服务；不得把以下URL替换为生产。

```sh
cd /Users/shajindi/yance-backup/yance/yance-ai
export APP_ENV=test
export DATABASE_URL=postgresql+psycopg://yance@127.0.0.1:55440/yance_v2_acceptance_test
export YANCE_TEST_DATABASE_ACK=yance_v2_acceptance_test
export EMAIL_ENABLED=false LLM_DEFAULT_PROVIDER=mock
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest --cov=app --cov-report=term --cov-fail-under=50 --tb=short
.venv/bin/python scripts/export_openapi.py --check
.venv/bin/alembic check
.venv/bin/python evals/run_evals.py run --no-persist
```

浏览器种子应使用独立浏览器库、明确ACK，以`PYTHONPATH=. .venv/bin/python tests/seed_v2_browser.py /private/tmp/yance-v2-browser-fixture.json`创建新夹具。API连接同一库；网页显式设置API_PROXY_TARGET=http://127.0.0.1:8023及NEXT_PUBLIC_API_URL=/api/v1，避免默认生产转发。然后在website运行：

```sh
PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3019 YANCE_V2_FIXTURE=/private/tmp/yance-v2-browser-fixture.json npx playwright test e2e/evidence-workspace.spec.ts --reporter=line
npm run typecheck
NEXT_TELEMETRY_DISABLED=1 npm run build
```

浏览器用例阻断所有非localhost/127.0.0.1请求。夹具含短期合成登录令牌，不提交Git或上传CI失败制品。

## 失败与修正

首轮完整回归189通过1失败：旧测试用日期字符串前10位比较UTC/北京时间，午夜跨日误判；改为带时区的完整时间点相等，未修改真实截止时间逻辑。初轮浏览器夹具误用80分，而现有API契约为0–1；改为0.8并新建夹具，未放宽应用校验。并发附加检查第一次耗尽免费文档额度返回429；将并发验证放入已有编辑步骤，保持计费保护，不清账或修改额度。布局截图暴露桌面原文列过窄，已调整全宽并复验。过程中的类型/脚本语法问题均修复，最终Lint与构建检查为准。

## 仍未执行/阻塞

真实政策/企业样本专家标注与业务质量基线、真实OSS上传与供应商沙箱、PG16候选镜像/新版本灾备恢复、生产性能和外部通知均未执行。完整任务fencing、通知outbox、模型预算压力、全文实时协作、资源目录及企业身份集成仍属后续独立批次。不能把本批补证清单称为已完成这些功能。

## 发布前步骤与回退约束

本批尚未获得新生产发布授权，不在此请求上线。需要先固定候选提交和镜像，在PG16运行CI/浏览器/兼容检查，核验目标环境与新鲜备份可恢复，评估历史批准稿需重生成的用户影响，再提供具体发布确认。

无数据库迁移或历史数据回填；现有付款、密码和历史证据不改。网页可独立回退；旧后端不具备新来源检查，不能声称简单回旧后端仍保留新安全门槛。若必须回退后端，应先维护/阻断批准、提交和工作稿下载路径，保留数据库与账本，优先前向修复。候选不得因跨租户、重复权益或无依据资格关键测试失败而放行。

## 下一阶段需要的外部输入（本批实现不依赖继续等待）

1. 有权使用的真实政策原文/批次与脱敏企业样本，及业务标注、独立复核负责人；样本不可用时真实业务质量继续标为未验证。
2. 现有OSS的bucket、地域、最小权限与隔离测试配置；通过获准的安全配置渠道提供凭据，不在聊天或Git发送密钥。
3. 现有支付宝/微信支付沙箱、开票供应商或人工税票验收流程与负责人；没有沙箱不做真实扣退款或开票。
4. 首批地区、行业及获准试点企业范围；不得把方案中的招募目标当成已有客户。

本批新增配置和CI尚未在远端执行；本地验收结果单独记录。临时API/网页与独立PG实例已停止，合成测试目录保留，不操作生产。
