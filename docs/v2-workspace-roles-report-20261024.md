# V2第八批：工作台角色与真实隔离浏览器联调（2026-10-24）

基线b028a46，feature/investor-grade-upgrade，起始工作区干净。本批补P1角色交互与网页到真实隔离API的验收，不改供应商、支付、数据库或迁移（仍0031）。未连接生产，未推送或部署，未外发/交易/申报。

## 发现与改动

项目页原仅按项目状态禁用操作，没有按成员角色提供只读反馈；auth/me原返回User.role，而真正服务端鉴权按Membership.role。两者不一致时界面会误判权限（不是已证明越权，服务端原有检查仍有效）。现在/me复制输出模型并覆盖当前成员角色，不修改账户持久化role，返回字段结构不变。

项目页与资料/项目加载并行获取当前成员角色；owner/admin/member可编辑，owner/admin可批准和退回工作稿，viewer或未知角色禁用写操作并说明只读。状态转换/材料状态/关联/补证/生成/编辑/评论/建议处理与Agent动作继续服从服务端；下载和版本比较保留阅读入口。角色获取失败不能默认获得编辑权限。已打开页面后角色被撤销仍依赖服务端即时鉴权，本批未实现权限变更推送。

对应auth.py /me、website应用详情页、test_v2_current_role.py；扩展seed_v2_browser.py添加账户role=owner但成员role=viewer的合成用户；令牌只写仓库外600权限夹具。新增workspace-roles.spec.ts不模拟业务API，连接本机FastAPI和合成数据库。关闭该用例追踪/录像/截图以避免登录令牌进入失败制品。CI为新用例单独创建项目夹具，避免与旧矩阵用例共享稿件版本。

## 实际验收

macOS、Python3.12.13、PG18+pgvector、Node26.8.1、锁定Next/React、Chromium。全套新库yance_v2_roles_regression_test，浏览器独立库yance_v2_roles_api_test，127.0.0.1:55440；API8024、网页3024。EMAIL_ENABLED=false、LLM_DEFAULT_PROVIDER=mock，纯合成政策/企业/用户；禁止非localhost/127.0.0.1浏览器访问。无真实政策质量结论。

- 完整后端229 passed，6个第三方弃用警告，14.19秒。新增反例：账户owner、成员viewer时/me返回viewer，DB账户仍owner。
- 网页完整构建和TypeScript通过；Ruff通过，OpenAPI --check通过（字段合同无变）。
- **真实隔离API浏览器1 passed（2.1秒）**：owner生成v1、编辑成v2、对v1提出建议、接受旧建议409、拒绝成功；viewer读取同项目/证据、版本比较可用；补证/生成/保存/审批/评论禁用；绕过界面直接POST评论403；真实GET核对2个工作稿、1条评论与拒绝决定。
- 合成夹具同时使用真实鉴权、数据库、来源检查和额度服务；没有API响应替身。仍不是生产、真实客户或供应商沙箱验收，未覆盖所有角色/每个按钮/全部导出格式。

首轮类型检查发现重复disabled属性，已修正并重建。首轮浏览器等待“工作稿”精确名称超时，实际标签含计数；改为匹配标签前缀。合成viewer邮箱使用example.invalid被EmailStr拒绝，改为example.com并新建夹具，未放宽邮箱校验/改旧记录。最终结果以上为准。调试本机HTTP检查首次继承代理导致非JSON；后改trust_env=False直连本机。未把失败或代理响应算通过。

证据audit-evidence/v2-workspace-roles-20261024；不提交夹具/token、API错误堆栈或浏览器认证制品。复现：新库设置APP_ENV=test、DATABASE_URL、同名YANCE_TEST_DATABASE_ACK，关闭邮件/mock模型，alembic upgrade head、pytest --tb=short。浏览器另建库，PYTHONPATH=. python tests/seed_v2_browser.py /private/tmp/安全夹具.json；API显式连接同库8024；网页构建和启动均明确NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8024。PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3024 YANCE_ROLES_FIXTURE=该夹具绝对路径 npx playwright test e2e/workspace-roles.spec.ts --reporter=line。

## 发布/回退与剩余

无新增迁移，不重复备份恢复/迁移往返；上一批0031合成恢复记录不冒充本轮复跑。PG16、CI远端运行、目标环境、生产恢复与真实供应商未验证。CI配置只修改本地文件，未运行远端。发布仍需固定SHA/镜像、预发布真实来源和目标备份恢复证据，再单独确认。

本批网页可回退；后端回退会恢复/me旧角色语义，可能再次与当前鉴权不一致，应保持只读提示或优先前向修复，不能撤销服务端Membership检查。保留全部0031数据和前批worker排空/审批约束。

下一阶段核心缺口：模型预算与副作用恢复、真实业务样本与质量基线、文件和供应商隔离链路、资源目录/机构扩展。当前完成的是合成项目真实代码联调，不是整个V2或生产已更新。
