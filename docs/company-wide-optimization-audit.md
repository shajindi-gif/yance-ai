# 全链路产品审计：2026-10-27

源码基线f3c3612，分支feature/investor-grade-upgrade，启动时工作树干净。源码唯一目录为本仓库。适用AGENTS只有website/AGENTS.md；已读README、V2方案/执行指令、客户复核契约、定价/反馈与最新发布记录、测试/回退文档及实际代码。后续候选由提交固定。本轮无生产写入或部署授权。

## 证据与环境

- 实测：当前正式域名release仍web-20261026-01，十个公开页面和手机版只读检查通过，公开能力无application_workspace_revision。见audit-evidence/company-wide-20261027/production-baseline/result.json；只是公开页面/匿名API样本，不能代替客户业务、生产DB或供应商验收。
- 发布记录：网页运行源码e549923，后端e58a7c4；本轮未SSH重新读取生产后端或DB。生产DB revision不得凭旧文档当最新实测。
- 本地代码：已有V2证据矩阵、版本关联评论、人工建议、租约fencing、LLM预留预算与通知outbox，迁移基线head=20261024_0032。它们不因本轮前端上线记录而成为生产已部署事实。
- 独立环境：新建本机PostgreSQL18+pgvector，端口55447，APP_ENV=test、明确DB ACK、邮件关闭、默认mock模型；测试数据均为合成。生产以旧发布记录PG16为线索，不能声称本机PG18等价验证。
- 本轮没有真实用户访谈、付费意愿、成本账单或独立业务标注，不提供业务准确率或毛利结论。

证据等级：运行实测 / 代码确认未运行 / 公开自述未核实 / 待验证 / 工具或权限受限。每个条目最终运行结果见测试报告；测试通过不自动代表生产已修复。

## 依赖与数据流

浏览器Next.js → 同源/api/v1 → FastAPI认证和Membership → 租户资源与PostgreSQL。

企业资料Company/ProfileVersion → Policy/Version/Chunk/EligibilityRule → PolicyScan/Opportunity/EligibilityResult/Evidence → Application/GapTask/Comment → ApplicationArtifact/Review → 授权DOCX/PDF导出。

Product → 服务器Order金额及资源绑定 → 支付供应商意图 → 签名/商户/金额验证 → PaymentEvent → Entitlement → 资源交付；Invoice为申请/付款凭证与人工正式开票流程。Plan/PriceVersion/Subscription/UsageRecord是另一个未完成收费验收的订阅基础，不等同于已开通399/999月费。

上传 → 私有OSS → 解析/OCR/文档审核 → 企业事实；关键词/pgvector检索与LLMRouter/预算可选；数据库worker处理Agent、取消、fencing和通知outbox。OSS/真实模型/邮件/支付/开票依赖必须单独验收，不能用mock代替。当前材料生成是deterministic-evidence-v1，并非任意政策的完整正式申报书。

## 环节映射

|环节/页面|主要API与权限|模型/执行/交付|已有验证与限制|
|---|---|---|---|
|官网/定价|GET products、auth/config公开|Product、能力声明；不触发任务|本轮公开基线实测；案例明确合成，暂无授权评价|
|登录/引导|auth注册/密码/邮箱、会话撤销；未配置邮箱降级|User/Membership/SessionVersion、Company|已有auth测试；返回来源页面存在断点，本轮修复|
|企业资料|companies/profile/publish，租户+角色|Company/ProfileVersion/事实确认|已有核心工作流、区县、证据测试；事实由客户确认|
|政策/机会|policies、policy-scans、opportunities；服务端可见性和地域时效|Policy/Version/Chunk/Rule、EligibilityResult/Evidence|已有边界/时效/检索/引用反例；真实来源覆盖与独立质量待验证|
|项目/补证|applications、eligibility-matrix、gap-tasks；write角色|Application/任务/活动|已有V2实测记录；本轮在新库重验|
|材料/复核/导出|artifact编辑/建议/decision/export；角色与版本保护|Artifact/Comment/Review、DOCX|已有来源/并发/旧批准失效保护；人工修订混入生成额度已复现|
|任务|agent-runs/steps/cancel、policy-scans；服务端上下文|Harness、租约fencing、预算、outbox|通用诊断/材料任务仍501；不能承诺已接通|
|订单/支付|orders、provider checkout/notify；角色+资源绑定|Order/Payment/Event/Entitlement|重复乱序合同已有测试；真实供应商沙箱未验收|
|发票/账单|invoices、billing；owner/admin及平台运营|Invoice/UsageRecord/PriceVersion|人工开票流程存在；税票真实处理和续费待验收|
|反馈/管理|POST feedback、admin feedback；本人身份/平台管理员|Feedback、处理状态|原仅提交与后台处理，用户不可查进度；本轮补闭环及隔离测试|
|设置/资源|enterprise导出/控制/资源介绍|ApiKey/Retention/Export；供给未核验|不宣称实际清理、SSO、MFA或可用资源库存|

## 问题登记

### CW-001 P0：人工工作被计入生成额度

证据：运行实测，tests/test_company_wide_closure.py人工修订反例；workflow.edit_application_artifact和decide_application_suggestion原调用consume_usage(generated_documents)。
复现：有效合成项目先生成1稿，设生成预算1，再人工编辑。预期可保存人工版本，实际429 quota_exceeded；接受人工建议同样受影响。影响：客户无法补正文稿，并混淆生成权益。建议：保留版本、来源、权限、并发及审计，人工操作不新增生成计量；生成/重新生成继续扣额。验收：预算耗尽仍可人工编辑/接受建议，重复接受不重复生成；新生成仍429。历史用量不回写。

### CW-002 P0：未验收商品只有前端提示，服务端仍可新购

证据：代码确认及反例，commerce.create_order仅检查Product.active；通用诊断/材料任务入口501。定价页禁用不能阻止API下单。
复现：对有效资源直接POST orders，产品POLICY_DIAGNOSIS/APPLICATION_PLAN；预期服务端拒绝新订单，原代码可创建订单并走支付入口。没有执行真实扣款，不断言已发生交易损失。建议：目录和新订单共用可售判断；未结历史订单不得新增不受控支付意图，已有在途意图/回调和权益继续保留。验收：直接API409、不创建支付记录、不调用供应商，历史已付订单可读，报告订单金额仍由服务器确定。新商品默认不可售。

### CW-003 P1：反馈没有用户可见处理闭环，重试可重复入库

证据：代码/运行实测，analytics.create_feedback原无幂等字段和GET历史；空白两字符入库成功。反例先失败，再修复。
复现：发送空白内容，或并发相同提交；预期拒绝空白且带同一请求号只入库一次，原代码不满足。管理处理后用户无查询入口。建议：兼容新增可空请求号，服务端隔离本人历史，前端能力协商、重试号复用和刷新状态。验收：真实DB入库→管理员处理→本人看到状态；两个租户/不同角色与非平台管理员拒绝；重复/冲突分别幂等/409。

### CW-004 P1：登录后丢失用户任务位置

证据：login所有成功路径固定dashboard，feedback提示手动回来，checkout匿名跳注册未保存产品/企业参数。代码确认，新增验证。
预期：用户回到原项目/反馈/购买步骤，注册仍经过引导；实际需重新寻找入口。建议：仅允许已知站内路由的安全next，保留查询，拒绝外部/协议相对/反斜线与控制字符地址。验收：真实登录回反馈，未登录项目回原项目；恶意next回dashboard，不能造成开放重定向。

### CW-005 P1：结构化API错误变成[object Object]

证据：lib/api.ts使用new Error(error.detail || fallback)，服务端配额/新购限制返回对象。代码确认。预期可理解的提示，实际对象被字符串化，用户不知道下一步。建议：集中解析message/额度/校验msg，不输出validation input。验收：消息可读、未知结构回退、不泄露输入值；不改变服务端状态。

### CW-006 P1：生产与本地能力存在版本差

证据：本轮正式域名公开能力未声明V2；本地auth/config有revision2，迁移至0032；生产DB未重新读取。保持兼容模式，不能按截图推销完整V2。依赖：独立后端发布、备份恢复与迁移验收，需新授权。本轮只形成具体发布前方案。

### CW-007 P1，外部依赖：真实交付质量与供应商验收不足

99元企业简报实际可验收内容、299/699独立交付、OSS/邮件/支付/税票沙箱、真实政策/企业评测与成本基线仍需获准样本或配置。政策资料应优先利用服务器既有采集来源，经授权范围检查；不要求衍策提供人工业务复核人，不默认访问全部客户资料。缺失时保留阻断，不伪造接口/评价/毛利。

## 十四类岗位审查落点

|职责|本轮结论/动作|
|---|---|
|经营战略|保留广泛企业服务范围，以单企业真实交付为切入；不追加无人维护系统|
|产品/运营|围绕任务入口→返回→编辑→导出→反馈，修复核心断点|
|用户研究|暂无获准访谈样本，场景为假设；历史反馈只在授权范围处理|
|设计/内容/无障碍|保留原创设计，新增可读状态、明确焦点和失败恢复，手机验证|
|前后端/架构|沿用模块化单体、既有API与组件；新增字段可兼容|
|AI/数据/知识|保留确定性硬条件与来源门槛，真实业务质量不外推|
|Agent|复跑租约、取消、预算、重复执行测试，501能力不包装销售|
|安全/隐私|本人反馈与服务端新购保护；既有角色和租户边界不放宽|
|QA/SRE|新库、版本固定、恢复与旧应用共存测试；生产不变|
|增长/品牌|现有受众与示例口径保留；新购状态来自后台，未开放订阅不报价收款|
|销售/伙伴|明确不可售能力；历史订单保留，供应商和资源未知时阻断|
|客户成功|真实DB验证提交→处理→用户查进度，公开评价另行授权|
|财务/收入运营|修正人工额度，保留历史账本；真实税票/成本待验证|
|内部运营/知识|交付四份一致文档、迁移/应用回退步骤和负责人动作|

## 2026-10-28 修复与复核结果

CW-001至005已完成本地实现和对应回归；具体证据见测试报告，不代表生产已修复。新增CW-008（P1）：硬门槛变为NOT_ELIGIBLE后人工保存原先可能抛未处理ValueError，现返回409且不创建半成品版本，新增反例通过。

当前候选1753fa9：新购保护同时覆盖新订单和没有既有意图的在线支付入口；保留既有支付意图、回调和权益，存量待交付仍需履约/对账。人工工作不新增生成计量，真正生成仍受原额度限制。反馈可选UUID/唯一约束/用户锁保证同账号同请求号幂等，冲突409；本人历史按tenant和user过滤，平台处理留状态审计。旧后台由能力声明降级，旧客户端可不传UUID。

代码位置：workflow.edit_application_artifact/decide_application_suggestion；services/commerce/availability.py；commerce.create_order；payments._checkout_payment；analytics.list_my_feedback/create_feedback；auth.auth_config；Feedback/FeedbackCreate；0033迁移；website反馈/登录/引导/核心入口与lib/api-errors.ts、return-path.ts。

尚未验证或延期：订单创建本身的跨请求幂等与报告购买时快照/存量再次购买定义，需要逐SKU交付验收，不把支付结算幂等当同一功能；真实99/299/699交付质量、供应商、企业样本、成本、资源供给及P2仍受真实数据/配置约束。企业主体、备案与隐私文本的外部真实性/法律有效性未独立核对，不新增法律或认证结论。


候选1753fa9的定位（行号以此提交为准）：

|问题|文件与行号|运行证据|
|---|---|---|
|CW-001/008|yance-ai/app/api/routes/workflow.py:1391、:1558|test_company_wide_closure人工修订/硬门槛反例，现有来源与建议测试|
|CW-002|yance-ai/app/api/routes/commerce.py:43、payments.py:27、services/commerce/availability.py:4|新单409、旧未付单不能新建意图、付款重放及历史订单回归|
|CW-003|yance-ai/app/api/routes/analytics.py:26、:45，models/models.py的Feedback，0033迁移|并发幂等、双租户与同企业viewer隔离、真实浏览器入库/处理|
|CW-004|website/lib/return-path.ts:4，app/login/page.tsx的LoginContent|安全回跳单元及真实登录/恶意next浏览器|
|CW-005|website/lib/api-errors.ts:2，lib/api.ts的request|错误结构/输入脱敏单元及现有表单/交易入口回归|
