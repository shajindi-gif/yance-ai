# 六套系统骨架

## 产品系统

GitHub Issue → PRD → Branch/PR → CI → Release → Changelog。模板和流程在 `.github/`、`docs/product/`。

## 技术系统

FastAPI 通过 Nginx 提供 API；本地 Compose 使用自带 pgvector，生产 Compose 连接 RDS 和 OSS。环境变量隔离 Dev/Prod，CI 执行 lint、迁移、测试、评测和镜像构建。

## 数据系统

- Source of record：PostgreSQL
- 原始文档：私有 OSS，租户前缀隔离
- 向量：第一版 pgvector，维度 1536
- 评测：版本化 JSONL golden cases
- 行为数据：`analytics_events`
- 数据处理状态：`documents.status`

数据生命周期、保留期限、删除请求、灾备演练仍需在正式获客前按业务和法规确定。

## AI 系统

`LLMProvider` 屏蔽 Qwen/DeepSeek/OpenAI/Claude 差异；`VectorStore` 屏蔽 pgvector/Qdrant 差异；`agent_runs` 记录模型、token、延迟和错误。默认 mock，未配置密钥时不会意外调用付费模型。

## 商业系统

Order、Payment、Invoice 只提供领域状态与 API 骨架。真实支付必须补：服务端签名、幂等键、异步回调验签、金额复核、退款、对账、商户配置和合规审计。

## 安全运营系统

JWT + RBAC、租户查询约束、私有 OSS、最小权限 RAM、Nginx TLS/限流、JSON 日志、审计日志表、GitHub 受保护环境、RDS 白名单和云备份。下一阶段应加入 KMS、RLS、WAF、告警、SAST/依赖扫描和自动恢复演练。

