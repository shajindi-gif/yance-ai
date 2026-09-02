# 安全审计

## 结论

当前不满足企业生产安全基线。最严重风险来自商业授权绕过、潜在跨租户访问、未转义 HTML→PDF、上传管线缺少安全控制，以及公开安全/隐私声明无法由代码或数据室证据支持。

本报告不是渗透测试或合规认证；未扫描线上资产、云账号、数据库、OSS、Cloudflare 或第三方供应商。它是代码和仓库证据审计。任何“已启用”的基础设施控制都需要现场证据才能确认。

## 资产与信任边界

### 高价值资产

- 企业身份、统一信用代码、联系人和组织成员；
- 财务、研发、人员、知识产权和申报资料；
- 政策原文、知识库、规则、Prompt、评测集；
- 资格判断、申报草稿、交付物和人工修订；
- JWT、模型、OSS、支付、数据库与部署密钥；
- 订单、支付、权益、发票和收入数据；
- 跨租户平台运营权限。

### 信任边界

Browser → Next.js → FastAPI → PostgreSQL/OSS → LLM/OCR/payment providers。当前每个边界都主要依赖应用代码约定，没有完整的 defense-in-depth、数据分类和控制证据。

## P0 风险

### SEC-P0-00 仓库内硬编码公司财务标识

`app/core/config.py` 给公司税号、开户行、银行账号和银行卡号设置了非空默认值，并由付款接口返回。即使部分信息可能出现在商业文件中，也不应作为代码默认配置或公开 API 的无条件响应。Phase 1 必须迁移到受控环境配置/Secrets Manager，限制 finance/admin 权限，清理 Git history 风险并轮换任何可用于收付款的标识；审计文档不复制具体值。

### SEC-P0-01 商业授权绕过

任何普通 member 都能调用 demo payment/task pay 并获得 paid/entitlement。攻击后果包括免费获取付费交付物、污染 MRR/收入、生成虚假订单和发票、掩盖真实支付问题。

### SEC-P0-02 租户和平台权限混淆

- tenant Owner 被用于潜在全局 Admin；
- `/tasks/admin/all` 查询没有 tenant filter；
- policy evaluate 可读取任意 ID 的 tenant-private policy；
- 没有 PostgreSQL RLS 或统一 scoped repository；
- 没有平台管理员身份、审批或 break-glass 审计。

### SEC-P0-03 HTML/PDF 注入与 SSRF/LFI

企业、政策、发票和 metadata 值未经 `html.escape` 进入 WeasyPrint。HTML renderer 可能解析 `<img src>`、CSS URL 等外部/本地资源。攻击者可通过企业名称、政策内容、发票字段或导入资料触发网络请求、读取 worker 可见文件或造成资源耗尽。

### SEC-P0-04 不实安全与隐私声明

安全页明确宣称：

- 腾讯云香港、HSTS、TLS 1.3；
- 数据库敏感字段 AES-256；
- 所有查询强制 tenant_id；
- 所有写操作和异常审计 ≥180 天；
- 每日快照 30 天、每月灾备演练；
- 模型供应商 zero retention、输出敏感过滤；
- 定期第三方渗透和代码审计。

仓库无法证明其中多数控制，部分被代码直接反证。隐私页还说 Cookie 维持登录，但实际使用 localStorage bearer token。此问题会带来虚假陈述、合同承诺、PIPL/跨境处理和企业安全问卷风险，应作为上线阻断项。

## 身份认证与会话

### 已有控制

- 使用 pwdlib 推荐密码哈希；
- JWT 有过期时间；
- principal 从数据库重新加载 active user 和当前 role；
- bootstrap/provision 使用常量时间 token 比较。

### 缺口

| 优先级 | 缺口 | 修复 |
|---|---|---|
| P1 | JWT 在 localStorage | 同源 HttpOnly Secure SameSite cookie 或 BFF session |
| P1 | login 无 rate limit/锁定 | Redis/edge 组合限流、指数退避、告警、验证码策略 |
| P1 | 注册限流是每进程内存 dict | 共享限流，可信代理 IP 解析，有界 key TTL |
| P1 | 无 refresh、撤销、session、jti | 短 access + rotated refresh，session store 和 revoke |
| P1 | 无重置/变更密码、邮箱验证、邀请 | 完整 account lifecycle，单次 token 和审计 |
| P1 | 无 MFA/SSO/SCIM | 企业方案至少支持 TOTP/WebAuthn；后续 SAML/OIDC |
| P1 | tenant active 未检查 | principal 同时验证 User/Tenant 状态 |
| P2 | JWT 无 iss/aud/kid | key rotation、issuer/audience、算法固定和 JWKS 策略 |

## 授权与多租户

当前 `tenant_id` 设计是良好起点，但“每个查询都手写 filter”不等于强隔离。建议：

1. request/session 设置不可由客户端覆盖的 tenant context；
2. repository API 默认 tenant scoped，不提供裸 Session 给业务层；
3. PostgreSQL RLS 覆盖 tenant-owned 表；
4. global policy 采用明确 visibility 枚举，而不是 `tenant_id IS NULL` 的隐含规则；
5. platform admin 使用独立角色/表/认证域，所有跨租户访问 reason-required + audit；
6. 建立自动化矩阵：每个对象、每个 verb、每个角色、own/other/global。

## 输入、文件与内容安全

### 文档上传 P1

现有 presigned upload 只检查对象存在，checksum 由客户端提供但不验证。缺少：

- 文件大小上限、Content-Length 约束和配额；
- MIME/magic byte/扩展名 allowlist；
- malware scan、宏/脚本、压缩炸弹和多媒体解析限制；
- OSS quarantine → scan → accepted 三段 bucket/key；
- OCR/parser sandbox，无网络、只读文件系统、CPU/内存/时间限制；
- 加密、保留、删除、下载授权和 legal hold。

### API 输入 P1/P2

- JSON properties/metadata/form_data 没有大小、深度和字段 allowlist；可能导致日志、数据库和 prompt 污染。
- receipt_url 是任意字符串；未来读取时会形成 SSRF。
- Product amount、status、provider 等重要字段缺服务端 allowlist/状态机。
- 公开 `/test-embed` 无认证和 rate limit，可消耗付费模型额度。

## LLM 安全

| 优先级 | 风险 | 当前状态 | 控制 |
|---|---|---|---|
| P1 | Prompt injection | 政策正文/查询直接拼 Prompt | 不可信数据边界、指令隔离、检测、工具 allowlist |
| P1 | 敏感数据外发 | 无字段分类/脱敏/供应商 policy | Model Gateway、tenant policy、regional routing、DPA |
| P1 | 数据泄露到日志/raw | raw response 和 error 可能保存 | structured redaction、encrypted restricted payload store |
| P1 | 越权检索 | global/private 语义冲突 | ACL filter 必须在 retrieval 层强制 |
| P1 | 不安全自动决策 | benchmark 未达标仍可 ELIGIBLE | human approval、risk tier、发布 Gate |
| P2 | 成本/DoS | 无 tenant quota/budget | rate limit、token cap、cost budget、circuit breaker |

## 支付与财务安全

最低控制：

- Order price 来自服务端 versioned Price，不接收客户端金额；
- provider webhook 保存不可变原始事件 hash，唯一 event ID 幂等；
- 校验商户、app、seller、金额、币种、订单、状态和时间；
- Order/Payment/Entitlement 变更以事务 + outbox 原子处理；
- 人工银行核销需要 platform finance role、双人审批或阈值审批、凭证安全存储；
- 退款、chargeback、撤销 entitlement、日对账和差异告警；
- “内部对账 PDF”不能称为正式税务发票。

## Secrets 与供应链

本次只对高风险模式输出命中文件名，没有在审计文档复制 secret value。未发现被跟踪的私钥块；`.env.local` 被忽略。发现公司财务标识作为配置默认值被提交，且根级 `.env.example` / `yance-ai/.env.example` 因宽泛 ignore 规则没有进入 Git 跟踪。仍需补充：

- 全 Git history secret scan，并对任何命中完成 rotate；
- secrets manager、短期凭据、环境隔离、最小权限和访问审计；
- Dependabot/Renovate、lockfile review、SCA、SAST、container scan、SBOM、签名镜像；
- CI action pin 到 commit SHA，保护 main、强制 review 和 environment approval；
- 生产镜像 non-root、read-only FS、drop capabilities、egress policy。

## 数据保护与合规

需要先做数据流图和处理活动登记，再决定可对外声明的法规范围。至少包括：

- 数据分类：企业公开、机密、个人信息、敏感个人信息、支付、安全秘密；
- 处理目的、合法性基础、最小化、保留期和删除；
- 香港/大陆/海外模型供应商的数据地域和跨境传输机制；
- subprocessor 清单、DPA、供应商保留/训练策略；
- 数据主体访问、更正、导出、删除、撤回和账号关闭的真实流程；
- 安全事件响应、通知时限、证据保全和客户沟通；
- 日志和备份中的删除传播及恢复后再删除机制。

不要把“遵循 PIPL/GDPR/PDPO”作为无条件一句话。应由法律顾问根据实际业务地域和数据流出具结论。

## 安全验证计划

### 发布前 P0 Gate

- demo payment 不可达；支付/租户/PDF/AI Gate 的回归测试通过；
- 对外声明逐条关联证据；
- 恶意 HTML/URL/大文件/跨租户用例通过；
- staging DAST、dependency/container/secret scan 无未接受 Critical/High；
- 独立渗透测试覆盖 auth、tenant、upload、payment、LLM/RAG。

### 持续控制

- 每 PR：SAST/SCA/secret/IaC/container；
- 每 release：tenant matrix、payment webhook replay、LLM security eval；
- 每月：权限和 secret review、restore smoke；
- 每季度：incident tabletop、供应商与数据流 review；
- 每年或重大架构变更：独立渗透测试。频率必须按实际执行后再公开。
