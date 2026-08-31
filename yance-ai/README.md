# yance.ai Backend MVP

可在本地和阿里云部署的 API-first、多租户后端。当前版本是上线骨架，不包含政策采集器、完整 RAG 编排、真实支付回调或前端页面。

## 已包含

- FastAPI、SQLAlchemy 2、Alembic、PostgreSQL 16、pgvector
- JWT 登录、首次初始化、受密钥保护的客户租户开通、`owner/admin/member/viewer` RBAC
- tenant/company/document/policy/policy-rule/opportunity/application API
- 私有 OSS 的预签名直传和对象存在性确认
- orders/payments/invoices 商业系统骨架
- Qwen、DeepSeek、OpenAI、Claude Provider 抽象和默认 mock
- 可替换 `VectorStore` 接口，第一版实现 pgvector，未来可接 Qdrant
- 产品分析事件、结构化请求日志、Agent Run 数据模型
- Golden Cases 与确定性评测入口
- 本地/生产 Docker Compose、Nginx、GitHub CI/CD 样例
- 产品流程、安全运营、数据与 AI 架构资料

## 五分钟本地启动

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

另开终端：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

开发环境 API 文档：`http://localhost:8000/docs`。

首次创建租户：

```bash
curl -X POST http://localhost:8000/api/v1/auth/bootstrap \
  -H 'Content-Type: application/json' \
  -H 'X-Bootstrap-Token: change-bootstrap-token' \
  -d '{"tenant_name":"Yance AI","tenant_slug":"yance-ai","owner_email":"owner@example.com","owner_name":"Owner","owner_password":"ReplaceThisPassword123_"}'
```

返回的 `access_token` 用作 `Authorization: Bearer ...`。初始化接口全系统只能成功一次。
后续客户租户由可信后台调用 `/api/v1/auth/provision-tenant`，并携带只保存在服务端的
`X-Tenant-Provisioning-Token`；禁止从浏览器前端直接调用。

## API 一览

| 路径 | 作用 |
|---|---|
| `GET /health` | 进程健康 |
| `GET /health/ready` | 数据库就绪 |
| `/api/v1/auth/*` | 初始化、登录、当前用户 |
| `/api/v1/tenant`, `/users` | 租户与成员 |
| `/api/v1/companies` | 企业档案 |
| `/api/v1/documents/presign-upload` | OSS 预签名上传 |
| `/api/v1/policies`, `/policy-rules` | 政策与规则 |
| `/api/v1/opportunities`, `/applications` | 商机与申报流程 |
| `/api/v1/orders`, `/payments`, `/invoices` | 商业系统骨架 |
| `/api/v1/analytics/events`, `/agent-runs` | 产品与 AI 可观测性 |

## 多租户边界

JWT 同时携带用户、租户和角色；每个业务查询都强制包含 `tenant_id`，创建时由服务端写入租户，不接受客户端指定。对象存储 Key 固定以 `tenants/{tenant_id}/` 开头。第一版属于应用层隔离；上线多团队开发前应再增加 PostgreSQL RLS 和跨租户自动化测试。

## 目录

```text
app/                  FastAPI 应用、模型、API、服务抽象
alembic/              数据库迁移
evals/                Golden cases 与 runner
tests/                单元测试
nginx/                HTTP 与 HTTPS 配置
ops/                  systemd 等运维文件
docs/                 产品/架构/发布/安全资料
.github/               Issue、PR、CI/CD
明日部署手册.md          明天照做的完整步骤
部署前检查清单.md        开始前逐项确认
上线验收清单.md          上线后逐项验收
```

## 生产注意

- 不提交 `.env.production`、私钥、客户文件或真实 Golden Cases。
- RDS 与 ECS 放在同地域、同 VPC，只使用 RDS 内网地址。
- OSS Bucket 必须私有，并开启阻止公共访问。
- OSS 预签名上传使用公网 Endpoint，ECS 的对象检查使用内网 Endpoint；前端直传需配置 Bucket CORS。
- 生产关闭 Swagger；接口文档只在开发环境开放。
- 支付和开票 API 目前只建状态记录，未接支付宝/微信/税务平台，不能用于真实扣款。
- 首次上线前必须完成三份中文清单和 RDS 快照。

详细操作见 [明日部署手册.md](./明日部署手册.md)。
