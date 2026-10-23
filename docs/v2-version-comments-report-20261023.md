# V2第四批：版本级批注（2026-10-23）

基线609ff1b，工作分支feature/investor-grade-upgrade，起始工作区干净。落实S2的一部分：项目动态页可选择“项目整体”或具体工作稿版本发表评论，评论列表显示关联版本。没有替换编辑器或新增供应商。

## 差距与实现

P1：ApplicationComment原只关联项目，审阅人无法标明针对哪版意见。新增nullable artifact_id，后端同时校验租户、项目与稿件归属，允许批注历史版本但不会移到新版本。未指定版本保持旧接口语义，不推断回填历史评论。旧版客户端提交body仍可用。项目评论不是审批，提交评论不批准/拒绝材料、不改证据或导出权限。

顺带修复comment_added活动在flush之前读取默认UUID导致comment_id可能为None的追溯缺口；先持久化分配ID，再同一事务记录comment_id和artifact_id。每次提交仍按既有评论语义新增一条，未实现请求级重试去重。

涉及：app/models/models.py ApplicationComment、schemas.py ApplicationCommentCreate、workflow.py评论写入/项目详情返回，website/lib/api.ts和applications/[applicationId]/page.tsx。OpenAPI新增可选artifact_id并更新合同。网页使用原生选择器和React文本渲染，继续现有保存/失败反馈。只读成员仍由服务端拒绝，本批未声称已完成所有只读角色界面禁用。

## 迁移与回退

0029在0028上只新增application_comments.artifact_id及外键，不重写订单、客户密码或原评论。关联稿件删除采用RESTRICT，防止删除稿件后悄然把版本意见变成项目意见；未来任何材料清理/租户删除流程须显式评估该引用约束，不提供自动删除绕过。历史NULL表示项目整体/未记录版本，不能称为已知某版。

发布仍需固定候选SHA/镜像、PG16预发布、最新目标备份恢复、旧进程排空与业务负责人验收后单独确认。保留第二批worker升级约束；应用回退保留0029列和绑定历史，不在生产downgrade（会丢关联）。旧API不会展示版本绑定，因此回退时应暂停售后批注入口，优先前向修复，不能把未展示解释为关联不存在。无生产操作。

## 实际测试与局限

本机macOS、Python3.12.13、PG18+pgvector、Node26.8.1与锁定网页依赖；APP_ENV=test，localhost55440，独立新库yance_v2_comments_test，纯合成数据，EMAIL_ENABLED=false、LLM_DEFAULT_PROVIDER=mock。

- 完整后端221 passed，6个第三方弃用警告，13.38秒；本批未重复统计覆盖率或业务质量评测。
- 新增集成测试：旧版关联不随新稿变化、跨项目404、跨租户404、空白422、旧项目评论兼容、活动记录ID正确、viewer403；项目详情能读回对应artifact_id。
- 新库从零迁移0029，Alembic check无差异，Ruff通过，OpenAPI已更新。
- 旧0028合成恢复库显式插入1条旧格式评论再升0029，条数与内容语义保留，artifact_id仍NULL；不把空表迁移称为历史数据验收。
- 完整网页构建/TypeScript通过。扩展浏览器合同用例1 passed（1.7秒）：原版本比较/脚本文本/手机布局检查，加选择v1发表评论、刷新数据后显示v1。所有API为合成替身，外网被阻断；这不是浏览器到真实后端的集成验收。
- 新库备份恢复至yance_v2_comments_restore_test：78张表、2241行，逐表规范化哈希与数量一致。备份只含合成资料，权限600，仓库外/private/tmp/yance-v2-comments-synthetic.dump。不是生产备份或RTO/RPO证明。

命令：yance-ai内显式设置上述APP_ENV、DATABASE_URL、YANCE_TEST_DATABASE_ACK等于新库名后执行alembic upgrade head、python -m pytest --tb=short、alembic check；Ruff检查app/tests/本批迁移，python scripts/export_openapi.py。完整测试依赖全新专用库，不能复用全局计数夹具或清生产库。

网页：npm run typecheck；NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:9 NEXT_TELEMETRY_DISABLED=1 npm run build；隔离启动3023后以PLAYWRIGHT_EXTERNAL_SERVER=1、PLAYWRIGHT_BASE_URL=http://127.0.0.1:3023运行npx playwright test e2e/artifact-comparison.spec.ts --reporter=line。真实API写入、真实邮件、交易、PG16容器和生产验证未执行。测试证据见audit-evidence/v2-comments-20261023。

建议接受/拒绝的字段级建议对象与审计、模型预算、资源目录及真实样本评测仍未完成。新增版本关联不等于实时协作、精确段落批注或完整修订系统。继续沿用第三批对后续建议流程2–4工程人日的估算范围，需基于实际字段权限/冲突策略再细化，不承诺日期。
