import Link from 'next/link';
import Image from 'next/image';

/* -------------------------------------------
   Footer Data — New Product Matrix
   ------------------------------------------- */
const productLinks = [
  { href: '/login?register=1', label: 'Policy Match' },
  { href: '/pricing', label: 'Grant Copilot' },
  { href: '/policy-knowledge-base', label: 'Industry Research' },
  { href: '/company-match', label: 'Company Profile' },
  { href: '/parks', label: 'Park Entry' },
  { href: '/brief-maker', label: 'Report Studio' },
  { href: '/policies', label: 'Knowledge Bot' },
];

const solutionLinks = [
  { href: '/login?register=1', label: 'AI 企业' },
  { href: '/login?register=1', label: '机器人与智能制造' },
  { href: '/login?register=1', label: '生物医药' },
  { href: '/login?register=1', label: '集成电路' },
  { href: '/login?register=1', label: '新能源新材料' },
  { href: '/parks', label: '园区与产业服务机构' },
];

const resourceLinks = [
  { href: '/dashboard', label: '政策仪表盘' },
  { href: '/login?register=1', label: '免费体验' },
  { href: '/policies', label: '政策知识库' },
  { href: '/chrome-extension', label: '浏览器插件' },
  { href: '/about', label: '关于我们' },
  { href: '/security', label: '安全合规' },
  { href: '/pricing', label: '价格方案' },
];

const companyLinks = [
  { href: '/about', label: '关于我们' },
  { href: '/about', label: '团队' },
  { href: 'mailto:contact@yance.ai', label: '联系我们' },
  { href: '/privacy', label: '隐私政策' },
  { href: '/terms', label: '服务条款' },
];

/* -------------------------------------------
   Social Icons (inline SVGs)
   ------------------------------------------- */
function WeChatIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 01.213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 00.167-.054l1.903-1.114a.864.864 0 01.717-.098 10.16 10.16 0 002.837.403c.276 0 .543-.027.811-.05a6.127 6.127 0 01-.253-1.726c0-3.573 3.27-6.47 7.3-6.47.34 0 .672.03 1 .07-.629-3.484-4.157-6.306-8.558-6.306zM5.785 7.033a1.053 1.053 0 110-2.106 1.053 1.053 0 010 2.106zm5.813 0a1.053 1.053 0 110-2.106 1.053 1.053 0 010 2.106zM23.998 15.623c0-3.248-3.262-5.883-7.252-5.883-3.988 0-7.252 2.635-7.252 5.883 0 3.248 3.264 5.883 7.252 5.883.85 0 1.67-.127 2.428-.347a.681.681 0 01.576.08l1.53.895a.262.262 0 00.135.044.236.236 0 00.233-.237c0-.058-.023-.115-.039-.171l-.313-1.19a.474.474 0 01.171-.534c1.476-1.087 2.531-2.827 2.531-4.423zm-9.583-.91a.856.856 0 110-1.712.856.856 0 010 1.712zm4.662 0a.856.856 0 110-1.712.856.856 0 010 1.712z" />
    </svg>
  );
}

function ZhihuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M5.721 0C2.251 0 0 2.25 0 5.719V18.28C0 21.751 2.252 24 5.721 24h12.56C21.751 24 24 21.75 24 18.281V5.72C24 2.249 21.75 0 18.281 0H5.721zm1.964 4.078h6.543s.082-.352.082-.574c0-.223-.082-.426-.082-.426H7.923s-.164.102-.164.5c0 .398.164.5.164.5zm-.408 2.344h5.508l-.41 1.348H8.793L7.275 13.5h3.379l-2.617 5.86 6.316-4.028-1.453-1.832h-1.98l.793-1.953H7.275l1.002-2.125zm9.506.04h1.59s.121-.535.121-.82c0-.285-.121-.57-.121-.57h-3.145s-.09.246-.09.57c0 .324.09.82.09.82h1.555z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
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
              面向中国新质生产力科技企业的 AI 产业研究与政策申报服务平台。为 AI、机器人、生物医药、集成电路、新能源等科技企业及产业园区提供智能化政策匹配、申报辅助和产业研究服务。
            </p>
            <div className="footer-social">
              <a href="#" aria-label="微信公众号" title="微信公众号">
                <WeChatIcon />
              </a>
              <a href="#" aria-label="知乎" title="知乎">
                <ZhihuIcon />
              </a>
              <a
                href="https://github.com/yance-policy-agent"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub"
                title="GitHub"
              >
                <GitHubIcon />
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
            &copy; {year} 上海衍策引擎人工智能科技有限公司 | 衍策引擎AI
          </p>
          <div className="footer-legal">
            <span className="footer-deploy-tag">服务部署于中国香港</span>
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
