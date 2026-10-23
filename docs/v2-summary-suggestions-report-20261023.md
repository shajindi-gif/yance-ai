# V2第五批：人工摘要建议与决定（2026-10-23）

基线52572a7，feature/investor-grade-upgrade，起始工作区干净。P1差距：版本批注已有，但不能保存并处理具体修改建议。现在允许版本批注附完整替换摘要，成员显式接受/拒绝，仍复用现有项目、稿件、额度与审计模块。

## 契约与实现

ApplicationComment新增可空proposed_summary、resolution_json（0030）；旧评论和旧客户端不受要求回填。建议必须关联本租户/本项目稿件，正文与摘要有长度和空白检查。列表展示建议内容、处理状态；接受按钮说明会使用一次文档额度，新稿仍须人工复核。只允许完整摘要替换，不能修改资格、原文或证明；不调用模型、不生成假证据。

决定API `/applications/{id}/comments/{comment_id}/decision` 使用现有write_principal。项目行锁串行化决定与已有编辑：同一决定重试返回原结果，相反决定409；接受必须是最新版本、允许编辑的项目状态、来源指纹与校验和当前有效。变化409并保留未处理建议。创建新draft、用量、决定记录与活动日志同一事务提交，额度不足回滚；拒绝不生成新稿或扣额度。接受不是批准或申报。建议可由现有可编辑成员处理，审批仍由原owner/admin规则控制。

文件：workflow.py决定API/评论，models.py/schema与0030迁移，website应用详情/api客户端，tests/test_v2_summary_suggestions.py及扩展浏览器合同。OpenAPI合同已更新。未实现段落级修订、自动合并、任意字段建议、自动rebase或实时协作；评论/建议创建仍沿用每次提交新增语义，不声称创建接口具备重试去重。

## 实测与证据边界

macOS、Python3.12.13、PG18+pgvector localhost55440、Node26.8.1、Next锁定版本，独立新库yance_v2_suggestions_final_test，纯合成资料；EMAIL_ENABLED=false、LLM_DEFAULT_PROVIDER=mock。

- 完整后端222 passed，6个第三方弃用警告，15.07秒；Ruff、Alembic check通过，新库从零升0030；未重测覆盖率或真实业务质量。
- 新集成反例先以真实缺政策项目验证409；再显式替换来源就绪判断，仅隔离测试事务：两并发接受得到同一结果、仅新增一稿/一条文档用量、新稿draft、旧版建议409、相反决定409、跨租户404、拒绝成功。该替身不代表真实政策资格通过；来源变化校验沿用前批实测，不伪称本用例是完整真实政策建议验收。
- 首轮221通过1失败，原因是缺政策合成夹具无法通过真实来源校验；保持应用门槛，将测试拆清来源阻断与就绪替身事务语义，定向复验后在新库重跑全套通过，原库保留。
- 完整网页构建、TypeScript通过。合成浏览器1 passed（2.1秒）：版本比较、注入文本安全、移动端、版本评论，以及建议输入和接受后“新稿仍须人工复核”反馈。API均为合同替身，禁止外网，不是浏览器到真实后端的全链路验收。
- 合成备份恢复：78表2270行规范化哈希和数量一致，备份600权限仓库外/private/tmp/yance-v2-suggestions-synthetic.dump。不是生产恢复/性能/RTO/RPO结论。

复现：yance-ai内对新专用库设置APP_ENV=test、明确DATABASE_URL及同名YANCE_TEST_DATABASE_ACK，再alembic upgrade head、python -m pytest --tb=short、alembic check、ruff check app tests及0030文件。网页typecheck；构建显式NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:9 NEXT_TELEMETRY_DISABLED=1。隔离3023运行PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3023 npx playwright test e2e/artifact-comparison.spec.ts --reporter=line。证据在audit-evidence/v2-suggestions-20261023。

## 发布与后续

未推送或部署、未连接生产、未真实交易/外发/申报。迁移仅加可空字段，应用回退保留0030与决定历史，不能生产downgrade丢审计；旧UI不展示决定，回退时暂停建议处理入口，优先前向修复。旧/新worker排空要求继续沿用第二批。发布前仍需固定候选SHA/镜像、PG16、真实政策/企业验收、供应商沙箱、目标新鲜备份恢复与窗口，再另行确认。

后续优先补真实来源的建议全链路和额度失败恢复用例、用户角色界面禁用、创建请求去重。其后模型预算/资源目录、业务标注基线及OSS等仍待完成；资源目录不填造合作方。当前估算真实来源建议/额度回归与UI角色1–2工程人日，需真实政策样本和业务复核，不承诺日期。既有付款与批准安全门槛保留。
