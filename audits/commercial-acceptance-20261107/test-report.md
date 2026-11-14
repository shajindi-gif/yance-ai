# 命令、环境和证据

macOS Apple Silicon，Python3.12.13，Node26，Next16.4.3，Playwright1.63.0。本机PostgreSQL18在127.0.0.1:55432，新建yance_acceptance_1107_test、yance_suite_1107_test、yance_metrics_1107_test及yance_restore_1107_test。未使用已有业务库跑测试。

临时run.py从Settings(_env_file=None)生成默认配置，清空继承环境，覆盖APP_ENV=test、专用DATABASE_URL和YANCE_TEST_DATABASE_ACK，供应商凭据为空、邮件短信关闭、LLM mock。使用127.0.0.1:8047 API，网页构建API_PROXY_TARGET=http://127.0.0.1:8047，浏览器候选端口3047。临时token夹具权限0600，保存在/private/tmp，未提交到报告。

|执行|结果|证据|
|---|---|---|
|npm run lint|通过|evidence/lint.log|
|npm run typecheck|通过|evidence/typecheck.log|
|npm run test:unit|通过，计数见日志|evidence/unit.log|
|API_PROXY_TARGET本机 npm run build|通过|evidence/build.log|
|alembic upgrade head（全新库）|到0038通过|evidence/migration.log、migration-suite.log|
|pytest tests -o addopts='' -q --junitxml=…|455通过、1失败、6警告，41.57秒；此前一轮同项失败|evidence/backend-repeat.log、backend.xml|
|pytest tests/test_admin_analytics.py（另全新库）|1通过|evidence/metrics-recheck.log|
|Playwright login-payment-ux + evidence-workspace，提供合成夹具|7通过，13.1秒|evidence/journey.log|
|Playwright frontend-redesign、artifact-comparison、workspace-roles、audit-journey、legacy-api、documents|14通过，14秒|evidence/workspace.log|
|Playwright remediation，提供真实本地API及角色夹具|4通过，13.4秒|evidence/remediation-complete.log|
|最初公开浏览器及无障碍混合批次|9通过、2跳过、1失败。两个跳过在后续提供夹具后通过；Firefox启动失败仍未解决|evidence/browser.log|
|npm audit --omit=dev --json|运行依赖已知漏洞0|evidence/npm-audit.json|
|park_policy cli eval run|21工程题通过，3题未评分；A/B blocked|evidence/eval.json、eval.log|
|合成库pg_dump/pg_restore新库|恢复0038，orders17、deliverables16|evidence/restore.log|
|生产SSH聚合只读、正式站匿名GET|成功|evidence/production-counts.log、production-detail.log、production-visual.json|

上述浏览器批次有重叠，不汇总成唯一用例数或总体通过率。axe附件与本次页面截图另见evidence；最初Playwright临时目录被后续批次替换，Firefox启动失败只有保留日志，无页面截图。业务报告文字、中文字体、真实文件分页及所有角色完整连续旅程仍未完成逐页人工验收。

本地备份恢复为合成数据库，未包含生产原文持久盘、交易或客户数据。生产PG16恢复与旧应用/新库共存、回退条件只参考历史文档，未在本轮演练，RTO/RPO不作承诺。渠道沙箱、真实资金与开票、真实短信邮件、实际供应商故障和真实用户RUM、真实客户研究未执行，需相应外部配置、授权数据和预算。园区撤销路径未执行，列为阻断园区试点的验证缺口。

复现步骤应先创建新的带test后缀数据库并迁移。不要在本轮已用过的库上重复运行依赖全局计数的测试。测试失败C05即为全量与单文件相互影响的可复现证据，未通过删生产数据或修改断言消除。

## Lighthouse手机复测

Lighthouse13.6.0，本机生产构建首页、移动端默认模拟网络和CPU，2次样本。详细设置见evidence/performance-summary.json。

|样本|性能|无障碍|最佳实践|SEO|LCP|TBT|CLS|
|---|---:|---:|---:|---:|---:|---:|---:|
|1|50|98|100|100|7.82s|1291ms|0.000|
|2|95|98|100|100|2.84s|66ms|0.000|

单次Lighthouse无障碍98与axe样本零违规同时保留，二者覆盖和评分不同。真实用户p75 INP未测，TBT不替代INP。LCP2.5秒、CLS0.1为项目目标，实际发布阈值需结合真实设备与线上样本。
