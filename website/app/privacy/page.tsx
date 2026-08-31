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
            <p className="legal-date">最近更新日期：2026 年 8 月 13 日 · 生效日期：2026 年 8 月 13 日</p>

            <h2>1. 信息收集</h2>
            <p>为提供政策匹配与申报辅助服务，我们收集以下信息：</p>
            <ul>
              <li><strong>注册信息</strong>：企业全称、行业、所在省市、联系人姓名、邮箱。</li>
              <li><strong>企业档案</strong>：统一社会信用代码、规模、研发情况、知识产权等（用于政策匹配）。</li>
              <li><strong>使用数据</strong>：登录日志、搜索关键词、报告生成记录、支付记录。</li>
              <li><strong>设备信息</strong>：IP 地址、浏览器类型、访问时间（用于安全与性能优化）。</li>
            </ul>

            <h2>2. 信息使用</h2>
            <p>收集的信息仅用于：</p>
            <ul>
              <li>提供、维护和改进政策匹配、报告生成、支付结算等核心服务；</li>
              <li>账户安全验证、反欺诈与客户服务；</li>
              <li>匿名化聚合分析，用于优化匹配算法与推荐逻辑；</li>
              <li>法律法规要求下的必要披露。</li>
            </ul>

            <h2>3. 数据存储与安全</h2>
            <p>用户数据存储于中国香港合规数据中心。我们采用以下措施：</p>
            <ul>
              <li>传输层 TLS 1.3 加密；</li>
              <li>数据库字段级 AES-256 加密；</li>
              <li>严格的访问控制与审计日志；</li>
              <li>定期第三方安全评估。</li>
            </ul>

            <h2>4. 信息共享</h2>
            <p>未经用户明确同意，我们不会向任何第三方出售、出租或共享用户个人信息，以下情形除外：</p>
            <ul>
              <li>为完成支付结算而与支付机构共享必要信息；</li>
              <li>法律法规、司法或行政机关依法要求；</li>
              <li>为保护用户、公众或本公司的人身与财产安全所必需。</li>
            </ul>

            <h2>5. 用户权利</h2>
            <p>用户享有对其个人信息的以下权利：查阅、更正、删除、导出，以及撤销同意与注销账户。可通过账户设置或联系 contact@yance.ai 行使。</p>

            <h2>6. Cookie 与类似技术</h2>
            <p>我们使用 Cookie 维持登录状态与偏好。用户可在浏览器设置中关闭 Cookie，但可能影响部分功能使用。</p>

            <h2>7. 未成年人保护</h2>
            <p>本服务仅面向企业用户。我们不会故意收集未满 18 周岁个人的信息。</p>

            <h2>8. 跨境数据</h2>
            <p>本服务部署于中国香港。中国大陆用户访问时，注册与使用数据将在香港存储与处理。继续使用本服务即视为同意此跨境处理安排。</p>

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
