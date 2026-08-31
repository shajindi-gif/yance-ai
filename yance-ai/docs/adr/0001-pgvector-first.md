# ADR-0001：第一版使用 pgvector，预留 VectorStore

状态：Accepted，2026-08-09

第一版数据规模和团队规模尚未证明需要独立 Qdrant。将结构化数据和向量放在 RDS PostgreSQL 可减少一套生产系统、备份与权限面。代码通过 `VectorStore` 接口隔离实现；当向量规模、检索延迟、过滤能力或独立扩缩容形成真实瓶颈时，再实现 Qdrant adapter 并双写迁移。

