# 网页独立发布：web-20261020-01

2026-10-20，基线 a31f157e7fe789237ed1b5dc276388b1aaad0e71，工作分支 feature/investor-grade-upgrade。

用户要求“用户们能用到最新的网页”，本次发布范围仅 website。后端审计修复、0026/0027 迁移、生产交易与历史数据均不在本次范围。

## 已执行的发布前验证

- 本机 Node 26.8.1 / Next 16.3.8：`npm run typecheck` 和 `npm run build` 通过。
- Chromium，127.0.0.1，无网络节流，独立 PostgreSQL 18 合成库 yance_web_release_test；`PLAYWRIGHT_EXTERNAL_SERVER=1 PLAYWRIGHT_BASE_URL=http://127.0.0.1:3018 PLAYWRIGHT_API_BASE_URL=http://127.0.0.1:8018/api/v1 NEXT_PUBLIC_API_URL=http://127.0.0.1:8018/api/v1 npm run test:e2e`：7 passed (5.2s)。
- 覆盖登录失败恢复、受支持时的会话撤销、定价加载、移动端基本操作、区县保存刷新、资料控件、DEMO DOCX，以及旧能力响应下的画像保存和本机退出。
- 旧接口兼容测试是合同模拟；真实生产客户流程、真实付款和发票未进行写入测试。
- 生产只读核对：Ubuntu / Node 22.23.2，yance-website 服务端口3000；现有 Next16.3.4；API健康正常；auth/config仅返回 email_login_enabled=true，没有新能力标志。

## 兼容范围

修正页脚链接，升级 Next16.3.8及依赖锁。新增能力须服务端明确声明才显示：区县、取消任务、退出所有设备。当前生产将保留“退出当前设备”，不虚称已撤销其他设备。浏览器 API 默认采用同源路径，生产使用既有公开 API 地址。

## 发布和回退步骤

1. 将仅网页改动及本记录形成固定Git提交，推送功能分支，不推main，避免触发旧版全栈自动部署。
2. 从该提交 git archive website，校验包摘要，放到 /opt/yance/releases/website-web-20261020-01。不得手改运行源码。
3. 仅服务器内部继承既有网页环境文件，不输出其内容；Linux执行 npm ci、typecheck、build、audit。
4. 新构建先监听127.0.0.1:3001；核对页面、静态资源、release.json及只读API。旧网页继续服务。
5. 服务切换到固定新目录，保留旧目录及原服务文件；启动失败或正式域名异常立即恢复原服务。无数据库迁移，不需要数据回滚。
6. 正式域名确认release.json和页面/资源/只读API；浏览器检查定价和登录。记录实际SHA、摘要、构建与线上结果。

后端整批发布仍须满足 docs/release-runbook.md 中的独立门槛。本次网页上线不代表全部审计问题已解决。
