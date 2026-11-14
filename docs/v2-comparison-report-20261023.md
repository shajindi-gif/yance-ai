# V2第三批：工作稿版本对比（2026-10-23）

基线fcdec49，feature/investor-grade-upgrade，起始工作区干净。继续落实S2材料审阅协作；无后端、数据库、支付或生产改动。

## 差距与实现

P1：现有 ApplicationArtifact 保存不可变版本，人工编辑/生成创建新版本，父项目锁保护并发编辑，但工作稿页面没有比较视图。现在在现有工作稿页加入历史版本选择，对照最新同类工作稿：逐顶层字段显示新旧内容，摘要/资格/材料/证据使用中文名称；来源快照结构变化单独提示。折叠区域使用原生details、select与焦点轮廓，手机改为单列。

文件：website/components/workspace/ArtifactComparison.tsx、ArtifactComparison.module.css、website/lib/artifact-diff.ts；入口website/app/applications/[applicationId]/page.tsx。复用已鉴权项目详情的 generated 数据，无新增请求、缓存、导出或权限入口，不改变材料/批准状态。React文本渲染，不解释HTML，不调用模型。

结构比较忽略对象键顺序，保留数组顺序、字段删除和null差别；任意未知内容字段仍会显示差异。仅提示来源快照变化，不自动推断条款影响。对比的是当前用户已经可以读取的保存版本，不把内容一致当作审批或证据有效性证明。没有两个同类版本时明确提示。暂为最新稿对任意历史稿，非任意两稿/逐字合并工具。

## 实际验证

本机macOS、Node26.8.1、锁定Next16.3.8/React、Playwright Chromium。纯合成夹具，不含客户资料。新增4项算法测试通过，TypeScript通过，完整网页生产构建通过。新增真实浏览器合同测试1项通过（1.4秒）：历史版本切换、来源变化、脚本文本不执行、390px手机无整页横向溢出、无写请求；所有非localhost/127.0.0.1请求被拒绝，所有API响应为合成替身。

这不是后端集成/真实业务验收。第二批220项后端回归结果仅作为历史基线，本批未重复执行；后端和数据库完全未改。也未做真实供应商测试、生产等效PG16或性能测量。

复现：website目录运行 `node --experimental-strip-types --test tests/artifact-diff.test.mjs`、`npm run typecheck`；构建必须显式使用 `NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:9 NEXT_TELEMETRY_DISABLED=1 npm run build`。启动本机3023后，执行 `PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3023 npx playwright test e2e/artifact-comparison.spec.ts --reporter=line`。证据位于audit-evidence/v2-comparison-20261023。

首轮浏览器超时：构建继承本机.env.local中的生产API地址，外网防护正确阻断请求，未到达生产。固定同源API环境重新构建后通过，未放宽拦截。Node直接加载TS测试产生模块类型提示；浏览器测试存在终端色彩环境提示，均非失败。

## 后续与回退

本批无迁移和供应商配置。网页可独立回退到fcdec49，保留后端证据与审批保护；仍需具体候选、预发布完整路径验收后另行申请生产发布。未部署、未推送、未外发或真实交易。

下一步是版本绑定批注、明确接受/拒绝建议与审计事件。现有ApplicationComment只绑定项目，不能冒称版本级批注已完成。按现有模型估计该纵向扩展需2–4工程人日（新增兼容字段/并发与授权测试/页面），不承诺完成日期。模型预算、真实样本质量、OSS及支付/开票/邮件沙箱仍保留原阻塞，不用合成页面替代业务验收。
