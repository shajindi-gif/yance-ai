# 客户自行复核口径落实与验证（2026-10-24）

基线dfbbec4。按用户本轮明确说明修正业务前提，不要求衍策公司提供业务复核人员，也不要求已在服务器的政策原文必须另存本机。权威契约见customer-review-contract.md，总方案与执行提示同步更新。

新生成材料说明企业资料由客户提供、由客户本人或授权团队复核；客户确认不是政府认定或获批，衍策不提供人工业务审核。矩阵/项目页明确相同主体，客户团队管理员按既有权限决定稿件；未扩大member/viewer权限或允许确认绕过来源、时效、规则、额度检查。新工作稿disclaimer在DOCX/XLSX/JSON中保留，PDF说明明确客户复核。历史稿内容与批准记录不回写，现行导出模板的一般说明使用最新口径。

政策原文与知识库来源“服务器采集”、企业资料“客户提供”为用户确认的业务流程，本轮未连接服务器核验采集质量/完整性，未访问生产客户资料。采集入库不直接等于来源有效；客户确认标签仅为客户自评，不冒充独立专家评测。后续优先核对既有服务器采集来源元数据与管道，再按客户授权使用脱敏样本，不再将公司提供复核负责人列为开发前置。

本机macOS、Python3.12.13、PG18+pgvector、Node26.8.1与锁定网页依赖。独立新库yance_customer_review_test，APP_ENV=test、同名ACK、EMAIL_ENABLED=false、LLM_DEFAULT_PROVIDER=mock；无真实模型、邮件、交易或客户资料。

实际结果：完整后端236 passed，6个第三方弃用警告，25.22秒；Ruff、网页TypeScript和完整构建通过。新增断言覆盖真实材料生成返回的客户复核说明及DOCX/XLSX/JSON保留；已有PDF生成回归通过，未新增PDF视觉排版检查或浏览器检查。证据audit-evidence/customer-review-20261024。无新增迁移，仍0032；本批未重复恢复/PG16/供应商验证，沿用各批次历史记录，不称本轮执行。

复现：新建隔离库并明确APP_ENV=test、DATABASE_URL、同名YANCE_TEST_DATABASE_ACK，关闭邮件/mock模型，alembic upgrade head后pytest --tb=short；网页typecheck与显式NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:9 NEXT_TELEMETRY_DISABLED=1 build。

本批未生产连接/部署、未推送/外发/交易，无生产数据变更。可独立回退文案与模板代码，历史材料不改；不要通过回退删除此前审批、来源和幂等门槛。所有前批迁移/worker回退约束保留。外部依赖仍为隔离供应商配置、客户授权资料/实际客户反馈及生产等效发布验收，不包含公司人工审核服务承诺。
