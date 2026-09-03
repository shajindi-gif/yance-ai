import type { Metadata } from 'next';

export const metadata: Metadata = { title: '隐私政策 | 衍策引擎AI' };

export default function PrivacyPage() {
  return (
    <>
      <section className="page-banner" style={{ background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d44 60%, #0d1b2a 100%)' }}>
        <div className="container">
          <h1>隐私政策</h1>
          <p>上海衍策引擎人工智能科技有限公司重视并保护用户隐私。</p>
        </div>
      </section>
      <section className="section">
        <div className="container container-narrow">
          <div className="legal-doc">
            <p className="legal-date">最近更新日期：2026 年 9 月 3 日</p>

            <h2>1. 信息收集</h2>
            <p>为提供政策匹配与申报辅助服务，我们收集以下信息：</p>
            <ul>
              <li><strong>注册信息</strong>：企业全称、行业、所在省市、联系人姓名、邮箱。</li>
              <li><strong>企业档案</strong>：统一社会信用代码、规模、研发情况、知识产权等（用于政策匹配）。</li>
              <li><strong>使用数据</strong>：登录日志、搜索关键词、报告生成记录、支付记录。</li>
              <li><strong>请求信息</strong>：IP 地址、请求路径、访问时间和 request_id（用于安全与故障排查）。</li>
            </ul>

            <h2>2. 信息使用</h2>
            <p>收集的信息仅用于：</p>
            <ul>
              <li>提供、维护和改进政策匹配、报告生成、支付结算等核心服务；</li>
              <li>账户安全验证、反欺诈与客户服务；</li>
              <li>按租户汇总真实使用事件，用于产品运营与故障排查；</li>
              <li>法律法规要求下的必要披露。</li>
            </ul>

            <h2>3. 数据存储与安全</h2>
            <p>数据处理位置由实际部署环境和所选模型供应商决定。当前代码层已实现：</p>
            <ul>
              <li>基于租户和角色的 API 访问控制；</li>
              <li>密码哈希、访问令牌有效期和生产密钥配置校验；</li>
              <li>文档类型、大小以及 PDF 渲染外部访问限制；</li>
              <li>部署层 TLS、备份、存储加密和数据地域需在生产环境另行配置与验收。</li>
            </ul>

            <h2>4. 信息共享</h2>
            <p>未经用户明确同意，我们不会向任何第三方出售、出租或共享用户个人信息，以下情形除外：</p>
            <ul>
              <li>为完成支付结算而与支付机构共享必要信息；</li>
              <li>法律法规、司法或行政机关依法要求；</li>
              <li>为保护用户、公众或本公司的人身与财产安全所必需。</li>
            </ul>

            <h2>5. 用户权利</h2>
            <p>如需查阅、更正、导出、删除数据或注销账户，请联系 contact@yance.ai。自助导出和删除功能仍在建设中，当前请求需经身份与组织权限核验后人工处理。</p>

            <h2>6. Cookie 与类似技术</h2>
            <p>当前 Web 客户端在浏览器本地存储访问令牌。请勿在共享设备上保持登录；会话与 Cookie 方案将在后续安全阶段升级。</p>

            <h2>7. 未成年人保护</h2>
            <p>本服务仅面向企业用户。我们不会故意收集未满 18 周岁个人的信息。</p>

            <h2>8. 第三方模型与跨境处理</h2>
            <p>启用通义千问、DeepSeek 或 OpenAI-compatible 模型时，发送给模型的上下文可能由相应供应商处理。具体供应商、区域、保留策略和跨境安排应在企业开通前确认；本页面不作零数据保留承诺。</p>

            <h2>9. 政策更新</h2>
            <p>我们可能不时更新本隐私政策。重大变更将通过站内通知或注册邮箱提前告知。</p>

            <h2>10. 联系我们</h2>
            <p>关于隐私的任何问题，请联系：</p>
            <ul>
              <li>邮箱：contact@yance.ai</li>
              <li>公司：上海衍策引擎人工智能科技有限公司</li>
            </ul>
          </div>
        </div>
      </section>
    </>
  );
}
