import type { Metadata } from 'next';

export const metadata: Metadata = { title: '安全合规 | 衍策引擎AI' };

export default function SecurityPage() {
  return (
    <>
      <section className="page-banner" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)' }}>
        <div className="container">
          <h1>安全现状与责任边界</h1>
          <p>仅陈述当前代码和测试能够证明的控制；部署级能力以客户环境验收结果为准。</p>
        </div>
      </section>
      <section className="section">
        <div className="container container-narrow">
          <div className="legal-doc">
            <p className="legal-date">最近更新日期：2026 年 9 月 3 日</p>

            <h2>1. 当前已实现</h2>
            <ul>
              <li><strong>身份认证</strong>：密码使用 Argon2 哈希；访问令牌具有可配置有效期。</li>
              <li><strong>租户边界</strong>：业务 API 按 tenant_id 查询，并验证用户与租户均处于启用状态。</li>
              <li><strong>角色权限</strong>：区分 Owner、Admin、Member、Viewer；Owner 权限不能由 Admin 授予。</li>
              <li><strong>文档入口</strong>：限制文件类型与大小，并在完成上传时核对对象实际大小。</li>
              <li><strong>文档渲染</strong>：转义非可信内容，并禁止 PDF 渲染器访问外部网络和本地文件。</li>
              <li><strong>支付结算</strong>：校验供应商签名、商户字段、金额、币种和租户，并对回调事件去重。</li>
            </ul>

            <h2>2. 配置与日志</h2>
            <ul>
              <li>生产密钥必须通过环境配置注入，仓库仅提供无真实凭据的示例文件。</li>
              <li>API 日志包含 request_id 和请求耗时；默认不记录文档正文、令牌或支付回调原文。</li>
              <li>TLS、WAF、数据库与对象存储加密属于部署环境控制，须在目标环境单独验收。</li>
            </ul>

            <h2>3. 当前限制</h2>
            <ul>
              <li>尚未完成独立渗透测试、SOC 2、ISO 27001 或其他正式安全认证。</li>
              <li>尚未提供 SSO、SCIM、MFA、数据库 RLS 和完整平台管理员控制面。</li>
              <li>尚未建立可对外承诺的备份保留、RPO/RTO、灾备演练和日志保留 SLA。</li>
              <li>尚未宣称数据库字段级加密或模型供应商零数据保留；相关能力需以实际合同和部署配置为准。</li>
            </ul>

            <h2>4. AI 与专业判断</h2>
            <ul>
              <li>模型输出不能替代政策原文、主管部门意见或专业顾问判断。</li>
              <li>资格判断在证据不足或硬门槛不满足时会降级，并保留人工复核入口。</li>
              <li>启用第三方模型前，客户应确认数据处理区域、保留政策与合同条款。</li>
            </ul>

            <h2>5. 漏洞报告</h2>
            <p>请勿公开披露疑似漏洞。请通过 yanceai@163.com 私下联系，并从复现材料中移除凭据和客户数据。</p>
          </div>
        </div>
      </section>
    </>
  );
}
