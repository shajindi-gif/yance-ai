# V2第七批：评论及建议创建的重复提交保护（2026-10-23）

基线b75aa28，feature/investor-grade-upgrade，起始工作区干净。P1缺口：决定接口已有幂等，但创建评论/建议在响应丢失后重试会新增重复记录。本批在现有接口加入可选client_request_id，保留旧客户端行为。

## 实现契约

0031新增可空UUID列、tenant_id/application_id/client_request_id唯一约束；不回填历史标识。创建时先按租户锁项目，再查同项目标识。相同用户、标准化评论正文、版本及建议摘要相同，返回原记录（沿用201响应）；任一不符409。去重不能绕过写权限/租户校验，不依赖前端防重复点击。请求不带标识仍允许按原语义创建独立评论。当前提交标识不暴露在评论列表。

网页在本页面内用useRef保留签名与UUID；提交失败后原内容重试复用标识；改变内容/项目/关联版本产生新标识；成功后清除。即使服务器已提交但响应丢失，重试不会再生成评论或活动。刷新/跨设备不保留未确认标识，也不声称已实现离线自动保存或跨设备续写。接受建议的版本/来源/额度/审批保护不变。

主要文件：ApplicationComment模型与schemas.py、workflow.py创建接口、0031迁移；website/lib/api.ts、应用详情页；tests/test_v2_comment_idempotency.py及扩展浏览器合同。OpenAPI同步更新。

## 实际验证

macOS、Python3.12.13、PG18+pgvector、Node26.8.1、锁定Next/React，localhost55440；新库yance_v2_comment_idempotency_test；EMAIL_ENABLED=false、LLM_DEFAULT_PROVIDER=mock，纯合成资料。

- 完整后端228 passed，6个第三方弃用警告，13.90秒。2个新增参数场景分别为评论/摘要建议：两线程并发同标识返回同记录，后续重放相同；正文/版本/建议变更409；每项只新增1条评论和1条活动。旧客户端两次无标识仍返回不同记录。
- 浏览器合成合同1 passed（1.7秒）：模拟已保存却丢失响应，输入保留，第二次使用同UUID，列表仅一条评论；继续版本比较/建议接受反馈。全部API为替身、外网阻断，不是浏览器到真实后端的联合验收。
- 类型检查和完整网页构建通过；构建明确NEXT_PUBLIC_API_URL=/api/v1、API_PROXY_TARGET=http://127.0.0.1:9、NEXT_TELEMETRY_DISABLED=1；Ruff通过、Alembic check无差异。
- 从0030合成库升级：9条历史评论保持9条，提交标识全部NULL，未猜测回填；新库从零升0031。
- 合成备份独立恢复：78表2577行，逐表数量及规范化哈希一致。备份权限600、仓库外/private/tmp/yance-v2-idempotency-synthetic.dump；不是生产备份/RTO/RPO结论。

证据audit-evidence/v2-comment-idempotency-20261023。后端复现：新建本机专用库，APP_ENV=test、明确DATABASE_URL和同名YANCE_TEST_DATABASE_ACK，关闭邮件/mock模型，alembic upgrade head后pytest --tb=short；定向tests/test_v2_comment_idempotency.py。网页复验typecheck、上述显式环境build；3023隔离启动后PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3023 npx playwright test e2e/artifact-comparison.spec.ts --reporter=line。未测真实供应商、PG16容器、生产负载或业务质量。本批无测试失败；终端色彩与第三方弃用提示保留。

## 发布与回退

未推送、部署、真实外发/交易/申报，未连接生产。目标发布前须固定候选SHA/镜像，验证PG16、迁移锁窗口/历史评论规模、最新备份恢复及预发布完整业务路径，再单独确认。唯一约束创建需扫描现有表，不能以本机合成速度推断生产无锁风险。

回退保留0031与提交标识，禁止生产downgrade丢去重记录。若回旧API，旧处理逻辑不理解标识，重复保护会退化；应先暂停评论/建议创建入口并优先前向修复，不能仅依赖新网页标识。旧/新worker排空和此前审批/来源回退约束继续生效。

仍待：只读角色交互完善、真实政策/企业专家复核与质量基线、文件/供应商隔离链路、模型预算和副作用账本、PG16发布门槛。资源目录与机构扩展未完成，合成结果不代表真实业务准确率。下一步不依赖外部配置的优先项为角色界面/浏览器到真实隔离API联调；外部配置与样本继续按安全渠道准备。
