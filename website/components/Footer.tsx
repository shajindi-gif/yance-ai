import Link from 'next/link';
import Image from 'next/image';

/* -------------------------------------------
   Footer Data — New Product Matrix
   ------------------------------------------- */
const productLinks = [
  { href: '/login?register=1', label: '政策匹配' },
  { href: '/applications', label: '申报工作台' },
  { href: '/policy-knowledge-base', label: '政策库介绍' },
  { href: '/companies', label: '企业画像' },
  { href: '/parks', label: '园区入驻' },
  { href: '/brief-maker', label: '报告生成' },
];

const solutionLinks = [
  { href: '/company-match', label: 'AI 企业' },
  { href: '/company-match', label: '机器人与智能制造' },
  { href: '/company-match', label: '生物医药' },
  { href: '/company-match', label: '集成电路' },
  { href: '/company-match', label: '新能源新材料' },
  { href: '/parks', label: '园区与产业服务机构' },
];

const resourceLinks = [
  { href: '/dashboard', label: '政策仪表盘' },
  { href: '/login?register=1', label: '免费注册' },
  { href: '/policies', label: '政策知识库' },
  { href: '/pricing', label: '价格方案' },
  { href: '/downloads', label: '客户端与渠道' },
  { href: '/feedback', label: '使用反馈' },
];

const companyLinks = [
  { href: '/about', label: '关于我们' },
  { href: '/security', label: '安全合规' },
  { href: 'mailto:yanceai@163.com', label: '联系我们' },
  { href: '/privacy', label: '隐私政策' },
  { href: '/terms', label: '服务条款' },
];

/* -------------------------------------------
   Social Icons (inline SVGs)
   ------------------------------------------- */
function MailIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  );
}

/* -------------------------------------------
   Footer Component
   ------------------------------------------- */
export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-grid">
          {/* Brand Column */}
          <div className="footer-brand">
            <Link href="/" className="footer-brand-logo">
              <Image
                src="/logo.png"
                alt="衍策引擎AI"
                width={48}
                height={48}
                className="footer-brand-logo-img"
              />
              <span className="footer-brand-name">衍策引擎AI</span>
            </Link>
            <p className="footer-brand-desc">
              聚焦新质生产力与科技企业，面向各类有政策需求的企业的政策与资源证据工作台。从企业事实与政策原文出发，辅助资格核对、材料准备与客户自主复核。
            </p>
            <div className="footer-social">
              <a href="mailto:yanceai@163.com" aria-label="邮件联系" title="yanceai@163.com">
                <MailIcon />
              </a>
            </div>
          </div>

          {/* Products Column */}
          <div>
            <h4 className="footer-column-title">产品</h4>
            <div className="footer-links">
              {productLinks.map((link) => (
                <Link key={link.label} href={link.href}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Solutions Column */}
          <div>
            <h4 className="footer-column-title">解决方案</h4>
            <div className="footer-links">
              {solutionLinks.map((link) => (
                <Link key={link.label} href={link.href}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Resources Column */}
          <div>
            <h4 className="footer-column-title">资源</h4>
            <div className="footer-links">
              {resourceLinks.map((link) => (
                <Link key={link.label} href={link.href}>
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          {/* Company Column */}
          <div>
            <h4 className="footer-column-title">公司</h4>
            <div className="footer-links">
              {companyLinks.map((link) =>
                link.href.startsWith('mailto:') ? (
                  <a key={link.label} href={link.href}>
                    {link.label}
                  </a>
                ) : (
                  <Link key={link.label} href={link.href}>
                    {link.label}
                  </Link>
                )
              )}
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="footer-bottom">
          <p className="footer-copyright">
            &copy; {year} 上海衍策引擎人工智能科技有限公司 | 衍策引擎AI | 客服邮箱：
            <a href="mailto:yanceai@163.com">yanceai@163.com</a>
            {/* 备案号待挂载：yance.ai（.ai）无法 ICP 备案；yance.cn 备案通过后在此行邮箱旁展示 */}
          </p>
          <div className="footer-legal">
            <span className="footer-deploy-tag">部署地域以实际环境为准</span>
            <Link href="/privacy">隐私政策</Link>
            <Link href="/terms">服务条款</Link>
            <Link href="/security">安全合规</Link>
          </div>
        </div>

        {/* Compliance Disclaimer */}
        <div className="footer-compliance">
          <p style={{ marginBottom: '8px' }}>
            衍策引擎AI 提供产业研究、政策信息整理、材料生成和申报辅助服务，具体申报条件、申报结果和补贴金额以主管部门、园区、政策文件和审核结果为准。
          </p>
          <p>
            本网站不涉及任何金融投资建议。衍策引擎AI 仅服务于科技企业产业研究与政策申报场景。
          </p>
        </div>
      </div>
    </footer>
  );
}
