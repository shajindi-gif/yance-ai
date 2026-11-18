# Yance 网站改造方案（Phase 1）与实施记录

日期：2026-11-18。分支：`design/website-enterprise-20261118`。

## 1. 品牌

中文名继续使用衍策引擎 AI，英文辅助名 Yance AI。

对外定位写成：

**中国科技企业的政策智能工作台。**

不使用“自动决策平台”。现有产品负责发现、核对、留痕和准备材料，认定与获批仍由主管部门和企业复核完成。

首页主句：

**让每一家创新企业，找到属于自己的政策机会。看清每项条件的依据。**

副文说明覆盖的是已收录目录，而不是承诺全国完整覆盖。

## 2. 视觉

沿用现有令牌：`--paper`、`--ink`、`--teal`、`--line`。不引入新字体文件，中文继续走系统字体栈（PingFang SC、微软雅黑）。

营销页增加的只是网格、状态标签和卡片，不用粒子、大渐变或新依赖。工作区组件保持原结构，避免支付和匹配流程回归。

## 3. 信息架构

公开导航：

- 查找政策 → `/discover`（未登录进入登录页，并回到该页）
- 解决方案 → `/solutions`
- 园区服务 → `/parks`
- 申报项目 → `/applications`
- 企业工具 → `/intelligence`
- 价格 → `/pricing`
- 关于我们 → `/about`
- 登录、免费开始（注册）

行业方案是展示层，工作流都回到已有页面：

`/companies` → `/discover` → `/opportunities` → `/applications`

## 4. 页面清单

| 优先级 | 页面 | 做法 |
| --- | --- | --- |
| P0 | 首页、导航、页脚、移动菜单 | 改文案与布局，保留 e2e 要求的标题、受众、场景和反馈声明 |
| P1 | `/discover` | 增加基于已加载数据的城市与支持类型筛选；登录回跳 |
| P1 | `/solutions` 与 11 个行业页 | 新营销页，链到真实产品 |
| P2 | 政策覆盖 | 分类说明，不写数量 |
| P3 | sitemap、标题与描述 | 只加入公开方案页 |

不改：`/pricing` 标题与产品目录组件、`/checkout`、`/login` 表单、`/orders`。

## 5. 组件

- `website/lib/solutions.ts`：行业文案与真实链接
- `website/components/marketing/SolutionView.tsx`：方案页布局
- 首页继续用 `website/app/page.tsx` 与 `Home.module.css`
- 不新增 npm 依赖

## 6. 转化路径

1. 首页主按钮：注册并进入企业档案（`/login?register=1&next=/companies`）
2. 次按钮：政策知识库说明（`/policy-knowledge-base`），避免在未登录时假装能搜到全库
3. 查找政策：`/discover`
4. 价格：`/pricing`，价格仍由接口返回
5. 企业演示：`mailto:yanceai@163.com`，主题为预约企业演示

空状态仍由现有工作区组件负责。没有企业档案时，发现页继续引导先创建企业。

## 7. 风险

| 风险 | 控制 |
| --- | --- |
| 虚构覆盖数量 | 首页写明数量未公开，并链接知识库页 |
| 行业页被理解成补贴承诺 | 每页声明适用性以核对结果为准 |
| 未提交的采集代码被提交 | 提交时只加入 `website/` 与本轮 `docs/YANCE_*.md` |
| e2e 文案回归 | 保留指定标题、三个受众、三个场景和反馈句 |
| 筛选改变匹配结果 | 筛选只作用于浏览器里已经返回的目录，不改扫描 API |

## 8. 2026-11-18 已执行的检查

- `npm run typecheck`、`npm run lint` 通过。
- `npx next build --webpack` 通过。默认 `next build` 因本机缺少 Turbopack 原生绑定失败，这是环境限制，不是页面编译错误。构建列出 `/solutions` 与 11 个静态方案页。
- 本地 webpack 开发服务器上手动打开：首页、注册回跳 `/login?register=1&next=/companies`、`/solutions/investors`。390px 宽时页面不横向溢出，汉堡菜单可打开，最后一项仍是“免费开始”。企业演示链接为 `mailto:yanceai@163.com`。
- Playwright 首页用例未跑完：本机没有 Chromium 浏览器二进制。未做登录后的真实政策扫描，未测支付。

不部署生产，不跑数据库迁移。未新增 npm 依赖。
