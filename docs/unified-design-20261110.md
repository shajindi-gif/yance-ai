# 全站界面整合候选

2026-11-10。设计分支design/unified-workspace-20261110。基于7cdaf86保留现有业务实现，首页结构逐文件取自用户选择恢复的faf50b6，保留680e048的检索错误处理、证据键盘返回及企业工具。此版本交付本地，生产发布待用户看过页面后确认。

## 风格冲突与处理

|证据位置|问题|本轮处理|
|---|---|---|
|website/app/globals.css、design-system.css|两处root与22组同名基础规则重复控制界面|将相同选择器的后置属性合入原定义，统一暖白、墨色、边框及表面变量|
|components/workspace/AppShell.module.css|侧栏、品牌、导航及身份卡多段重复定义，残留浅底白字|合并同选择器定义，使用共享文字及表面变量|
|components/workspace下五个样式文件|重复的白、灰、边框字面量|按语义接入共享变量，保留状态色|
|components/Header.tsx、lib/navigation.ts|政策任务入口分散，同一项目出现不同叫法|官网直接进入查找政策和申报项目，工具入口命名企业工具；工作台统一申报项目、企业资料|
|app/page.tsx、Home.module.css|仓库含用户已回退的首页结构|恢复faf50b6结构，使用当前隔离资格矩阵截图；保留用户行业图片及图外文案|
|app/login/page.tsx|登录介绍只覆盖新质生产力企业|统一为企业政策与资源证据工作台|

Harvey公开首页与Agents页已用Chromium浏览并存档reference截图。实见黑白中性色、大标题、宽留白、单一主操作以及文档产品画面。衍策采用中文系统字体、原品牌蓝和用户图片。参考网址为https://www.harvey.ai/、https://www.harvey.ai/platform/agents 。

## 验证与限制

本机新建yance_design_20261110_test，PostgreSQL端口5435，迁移至0039。API从临时目录启动，避免加载项目私密环境文件；模型默认mock、短信邮件默认关闭。合成夹具存放/tmp，权限600。浏览器仅允许127.0.0.1网络。生产构建与启动均显式配置同源/api/v1及本地API8024。

- npm run lint、npm run typecheck、npm run test:unit通过，6项单元测试。
- NEXT_PUBLIC_API_URL=/api/v1 API_PROXY_TARGET=http://127.0.0.1:8024 npm run build通过。
- 首轮13项浏览器回归11通过2跳过。补充复核夹具后最终构建12通过1跳过；再补充真实隔离订单后针对该跳过项1通过。合计13个不同用例均已执行通过。覆盖真实政策检索、原文、项目评论、未保存保护、客户复核和授权DOCX下载。支付部分包含契约级渠道模拟及真实隔离订单的供应商未配置恢复，未执行真实交易。
- 全部47个页面文件已盘点，其中42个页面实际浏览，HTTP200且无桌面整页溢出。5种动态详情缺少本轮对应测试实体或管理员角色，待验证。清单在route-coverage.json。页面渲染通过不能作为全部业务功能通过。
- 首页、检索、项目详情、登录、订单在390/768/1440三种宽度截图，最终样本无横向溢出。final前缀为实际生产构建且等待核心内容加载完成，after前缀曾包含加载态，不作为最终界面依据。
- 首次改前采集在截图时超时。已另启动faf50b6临时副本，使用同一隔离合成资料补齐baseline前缀对照。历史副本用webpack开发构建，候选用生产构建，两者不作性能比较。临时基线首次Turbopack无法解析外部依赖软链接，改用webpack成功。
- 本轮未执行Safari/Firefox完整兼容、全站axe及性能测量。五类动态详情、所有管理角色和页面全部异常分支仍需后续专项验收。旧业务页面还含局部内联样式，其逐项组件化尚未完成。

## 预览、证据与恢复

当前本地候选http://127.0.0.1:3038/ ，政策/discover，项目从/applications进入合成项目，订单/orders，工具/intelligence。生产构建重启命令在website目录执行 PORT=3038 HOSTNAME=127.0.0.1 API_PROXY_TARGET=http://127.0.0.1:8024 node .next/standalone/server.js 。API需要上述隔离库持续运行。不得把该开发环境作为生产配置模板。

对照图为audit-evidence/unified-design-20261110/journey-comparison.png。baseline与final同视口截图、参考截图及覆盖清单在同目录。恢复使用独立分支切回既有工作分支，无数据库变更需撤销。生产继续使用用户选择的faf50b6。本轮尚未全面完成所有页面局部样式清理和全部角色验收，后续应依据覆盖清单继续。
