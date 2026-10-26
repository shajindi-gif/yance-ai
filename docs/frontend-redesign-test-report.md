> 2026-10-25 发布兼容补充：生产仍是e58a7c4后端，因此增加能力协商；本机全新库15项浏览器回归及2项后端声明测试通过，旧版已备份并恢复运行验证。详见 [本次网页发布记录](website-release-20261025.md)。

# 前端改版测试报告

日期：2026-10-25（Asia/Shanghai）。基线源码 d13349c；最终候选由包含本报告的 Git 提交固定。生产未连接或变更，未推送远端。代码变化限于前端与本地测试/文档，没有后端业务或迁移改动。

## 环境与实际结果

macOS / Node26.8.1 / Next16.3.8 / Python3.12.13 / 本机 PostgreSQL18+pgvector。网页127.0.0.1:3024，同源转发127.0.0.1:8024；测试库 `yance_redesign_test`、`yance_redesign_regression_test`、`yance_redesign_browser2_test`。本机PG18与生产大版本并不等价，不能代替PG16候选验收。

|验证|实际结果|范围|
|---|---|---|
|类型检查、Next生产构建|通过|同源本机API；无新运行依赖|
|工作稿比较单元测试|4通过|键序、缺失/null、引用和来源变化|
|整轮浏览器回归|13通过，8.7秒|真实登录/退出、画像保存、资料控件、真实定价、旧接口合同、版本评论、只读角色、移动菜单、15个工作区路由、复核导出等|
|最后表单标签修改后的相关复测|3通过，2.6秒|真实登录/撤销、手机焦点/溢出、登录与注册字段可访问名称；其中1项是新增用例|
|不同浏览器用例合计|14项已执行通过|13项整轮加1项新增；不是声称最后一次运行14项整轮|
|后端完整回归|236通过，12.17秒；6条第三方弃用警告|新建迁移库，权限、证据、交易保护、版本与导出等已有测试|
|新增合成种子脚本Ruff|通过|复用既有数据库和输出位置保护|
|敏感信息扫描|通过，无命中|对待提交实际差异扫描，保留正文、仅去除差异定位头；日志只保留脱敏输出|
|画面/测量|8个页面视窗样本|首页、项目、定价、登录，各桌面1440×1000/手机390×844|
|核心色对比|5组超过4.5:1|正文12.68、次文5.45、主按钮5.91、成功5.40、警告5.20；不代表整站WCAG认证|

真实隔离浏览器流程包括：客户角色把有原文证据的合成项目从草稿推进到复核，批准最新工作稿并获得200 DOCX下载；下载后项目仍是review，未对外申报。另一项目中owner编辑新稿，接受旧稿建议被409阻止，拒绝建议留痕；viewer即便账号历史role为owner，按当前membership仍只读，直接POST评论403。导出规则保持现有服务端契约，没有为测试放松条件。

模拟边界：版本比较/UI响应丢失测试使用合同模拟；定价只注入首次503，恢复后读取本机真实目录；旧认证能力响应是合同模拟。资料上传控件可见不代表OSS真实上传已接通。所有企业/政策/账号均为合成，截图不含客户资料；令牌文件在Git外受限保存，不进入报告。

## 测量及前后画面

以下为一次样本、无CPU/网络节流、已启动本机服务器的Chromium观察值。LCP/CLS记录到截图时点，不是生产现场指标、最终完整生命周期或p95。`response_start_ms`为从导航起算的响应开始，不能误称网络TTFB。两轮样本存在缓存、时序和合成记录差异，不据此声称普遍性能提升。

|页面 / 视窗|LCP观察值ms：前→后|CLS：前→后|最终页面横向溢出|
|---|---|---|---|
|home / desktop|132 → 100|0.0000 → 0.0000|无|
|application / desktop|276 → 124|0.0016 → 0.0013|无|
|pricing / desktop|80 → 32|0.1188 → 0.0000|无|
|login / desktop|68 → 64|0.0000 → 0.0000|无|
|home / mobile|64 → 44|0.0000 → 0.0000|无|
|application / mobile|104 → 116|0.0000 → 0.0000|无|
|pricing / mobile|280 → 24|0.3254 → 0.0000|无|
|login / mobile|60 → 56|0.0000 → 0.0000|无|

定价加载占位修正后本次CLS样本为0；项目手机LCP从104到116，保留变化，不用总体平均数掩盖。真实设备、移动网络/低端CPU、长时间观察和大规模数据尚未测量。

|页面|改版前|改版后|
|---|---|---|
|首页桌面|[前](audit-evidence/frontend-redesign/before/home-desktop.png)|[后](audit-evidence/frontend-redesign/after/home-desktop.png)|
|首页手机|[前](audit-evidence/frontend-redesign/before/home-mobile.png)|[后](audit-evidence/frontend-redesign/after/home-mobile.png)|
|项目桌面|[前](audit-evidence/frontend-redesign/before/application-desktop.png)|[后](audit-evidence/frontend-redesign/after/application-desktop.png)|
|项目手机|[前](audit-evidence/frontend-redesign/before/application-mobile.png)|[后](audit-evidence/frontend-redesign/after/application-mobile.png)|
|定价桌面|[前](audit-evidence/frontend-redesign/before/pricing-desktop.png)|[后](audit-evidence/frontend-redesign/after/pricing-desktop.png)|
|登录手机|[前](audit-evidence/frontend-redesign/before/login-mobile.png)|[后](audit-evidence/frontend-redesign/after/login-mobile.png)|

## 实际命令与复现

必须先创建、迁移全新本机测试库，不能指向生产。下列环境变量在实际运行时显式设置：APP_ENV=test、EMAIL_ENABLED=false、LLM_DEFAULT_PROVIDER=mock、DATABASE_URL和与库名一致的YANCE_TEST_DATABASE_ACK。凭据不写命令历史或报告。

```sh
# 在 yance-ai/，使用全新 yance_redesign_regression_test
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest --tb=short
.venv/bin/ruff check tests/seed_frontend_redesign.py
# 在专用浏览器测试库准备合成项目；不要重用已修改的角色/复核场景
.venv/bin/python tests/seed_frontend_redesign.py /private/tmp/yance-redesign-fixture-final.json

# 在 website/，构建并运行，仅本机目标
NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8024 NEXT_TELEMETRY_DISABLED=1 npm run build
API_PROXY_TARGET=http://127.0.0.1:8024 npm run start -- --hostname 127.0.0.1 --port 3024
npm run typecheck
node --experimental-strip-types --test tests/artifact-diff.test.mjs

# 实际整轮13项命令（新增标签用例之前）
PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3024 PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8024/api/v1 YANCE_ROLES_FIXTURE=/private/tmp/yance-redesign-fixture-final.json npm run test:e2e -- e2e/frontend-redesign.spec.ts e2e/artifact-comparison.spec.ts e2e/workspace-roles.spec.ts e2e/audit-journey.spec.ts e2e/legacy-api.spec.ts e2e/documents.spec.ts
# 最后表单标签修改后，仅针对相关3项复测
PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3024 PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8024/api/v1 npm run test:e2e -- e2e/audit-journey.spec.ts e2e/frontend-redesign.spec.ts --grep 'password login|mobile login|visible Chinese'
# 画面采集；短期会话过期须重新生成，不能放宽认证
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3024 YANCE_ROLES_FIXTURE=/private/tmp/yance-redesign-capture-fixture.json YANCE_CAPTURE_OUT=../docs/audit-evidence/frontend-redesign/after node scripts/capture-redesign.mjs
```

原始脱敏输出在 `audit-evidence/frontend-redesign/`。浏览器联调使用本机API；新测试、截图及角色测试限制回环目标/拦截外部请求。旧测试的目标显式配置为本机，不提供任何生产凭据。

## 失败、修复和限制

初轮12项有4项失败：手机工作稿按钮换列撑宽页面（已修）、产品图在服务启动后加入未被路由识别（重新构建带图验证）、框架route announcer使alert选择不唯一（限定业务alert）、抽屉初始焦点位置（调整并复测）。修复后5项针对性通过。

随后13项有3项注册相关失败：反复使用同一隔离库达到原有每IP每小时5次限流，返回429。保留原库/规则，另建 `yance_redesign_browser2_test` 运行13项全部通过。没有清空旧业务记录或放宽安全门槛。跨用户继续工作后，短期合成令牌正常过期，截图曾401；重新生成合成会话后完成最终8个视窗样本。

未执行：四家参考站桌面/手机实际视觉检查（浏览器超时/Mac锁定）、Safari/Firefox/真实手机和读屏、全站逐项WCAG检查、真实客户数据质量评估、真实OSS/支付/开票/邮件、生产Linux/Node22/PG16构建、生产灰度/备份恢复与回退。没有把这些项目写为通过。本轮没有改数据库schema，沿用既有0032；历史恢复报告不作为本轮生产恢复证据。

## 2026-10-26 服务对象与反馈候选

类型检查、42路由构建通过；4项新增场景/反馈与4项既有定价浏览器合同共8项通过（6.2秒）。隔离API使用合成响应，无生产反馈写入；真实反馈入库和管理员处理未执行。截图、命令与限制见[本批报告](audience-feedback-20261026.md)。未部署。
