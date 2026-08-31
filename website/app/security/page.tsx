import type { Metadata } from 'next';

export const metadata: Metadata = { title: '安全合规 | 衍策引擎AI' };

export default function SecurityPage() {
  return (
    <>
      <section className="page-banner" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)' }}>
        <div className="container">
          <h1>安全合规</h1>
          <p>衍策引擎AI 在架构设计、数据传输、存储与访问控制上采取多层防御。</p>
        </div>
      </section>
      <section className="section">
        <div className="container container-narrow">
          <div className="legal-doc">
            <p className="legal-date">最近更新日期：2026 年 8 月 13 日</p>

            <h2>1. 部署架构</h2>
            <ul>
              <li>基础设施：腾讯云轻量应用服务器（中国香港地域），无需境内 ICP 备案；</li>
              <li>网络接入：Cloudflare Tunnel 反向连接，无公网入站端口暴露；</li>
              <li>边缘防护：Cloudflare CDN + WAF + DDoS 防护 + 自动 HTTPS；</li>
              <li>域名：yance.ai（官网 / 仪表盘）、api.yance.ai（API），均启用 HSTS。</li>
            </ul>

            <h2>2. 数据加密</h2>
            <ul>
              <li><strong>传输</strong>：全程 TLS 1.3，禁用弱协议与弱密码套件；</li>
              <li><strong>静态存储</strong>：数据库敏感字段（支付凭据、JWT 密钥等）AES-256 加密；</li>
              <li><strong>认证</strong>：JWT 签发，HS256 签名，过期时间可配置（默认 60 分钟）；</li>
              <li><strong>密码</strong>：服务端使用 pwdlib 推荐算法（含 salt）哈希存储，永不保存明文。</li>
            </ul>

            <h2>3. 访问控制</h2>
            <ul>
              <li><strong>多租户隔离</strong>：所有数据查询强制按 tenant_id 过滤，租户之间数据严格隔离；</li>
              <li><strong>RBAC 角色</strong>：owner / admin / member / viewer 四级权限，API 层强制鉴权；</li>
              <li><strong>限流</strong>：注册接口 IP 级限流（默认 5 次/小时），防滥用；</li>
              <li><strong>审计</strong>：所有写操作与异常事件记录审计日志，保留期 ≥ 180 天。</li>
            </ul>

            <h2>4. 数据备份与灾难恢复</h2>
            <ul>
              <li>数据库每日自动快照，保留 30 天；</li>
              <li>生产服务器与 Mac 侧保留双重备份；</li>
              <li>每月一次灾备演练（快照恢复测试）。</li>
            </ul>

            <h2>5. AI 模型安全</h2>
            <ul>
              <li>接入模型供应商（通义千问 / DeepSeek / OpenAI）均符合其合规与安全规范；</li>
              <li>用户数据不会用于模型训练，供应商均承诺零数据保留（zero retention）；</li>
              <li>生成内容经后处理过滤敏感信息与不当内容。</li>
            </ul>

            <h2>6. 合规声明</h2>
            <ul>
              <li><strong>GDPR</strong>：服务面向中国大陆与香港用户，不主动面向欧盟用户；如涉及欧盟用户数据，按 GDPR 要求处理；</li>
              <li><strong>PIPL（个人信息保护法）</strong>：服务遵循中华人民共和国《个人信息保护法》要求；</li>
              <li><strong>香港 PDPO</strong>：服务遵循香港《个人资料（私隐）条例》；</li>
              <li><strong>不涉及金融投资建议</strong>：衍策引擎AI 仅服务于科技企业产业研究与政策申报场景。</li>
            </ul>

            <h2>7. 漏洞报告</h2>
            <p>如发现任何安全漏洞，请通过 security@yance.ai 与我们联系。我们承诺：</p>
            <ul>
              <li>24 小时内确认收到；</li>
              <li>关键漏洞 72 小时内修复；</li>
              <li>对善意报告者不采取法律行动，并提供致谢。</li>
            </ul>

            <h2>8. 第三方安全评估</h2>
            <p>我们定期接受独立第三方安全评估（包括渗透测试与代码审计），评估报告摘要可按需向企业客户披露。</p>
          </div>
        </div>
      </section>
    </>
  );
}
