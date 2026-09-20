'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import Image from 'next/image';

/* -------------------------------------------
   Navigation Data — New Product Matrix
   ------------------------------------------- */
const productLinks = [
  {
    href: '/login?register=1',
    title: '政策匹配',
    subtitle: 'Policy Match',
    desc: '企业政策匹配引擎',
  },
  {
    href: '/pricing',
    title: '申报助手',
    subtitle: 'Grant Copilot',
    desc: '政策补贴申报辅助',
  },
  {
    href: '/policy-knowledge-base',
    title: '产业研究',
    subtitle: 'Industry Research',
    desc: '新质生产力产业研究',
  },
  {
    href: '/company-match',
    title: '企业画像',
    subtitle: 'Company Profile',
    desc: '科技企业画像生成',
  },
  {
    href: '/parks',
    title: '园区入驻',
    subtitle: 'Park Entry',
    desc: '园区资源匹配',
  },
  {
    href: '/brief-maker',
    title: '报告生成',
    subtitle: 'Report Studio',
    desc: '报告与申报材料生成',
  },
  {
    href: '/policy-knowledge-base',
    title: '知识库 Bot',
    subtitle: 'Knowledge Bot',
    desc: '路线图 · 尚未发布',
  },
];

const solutionLinks = [
  { href: '/company-match', title: 'AI 企业', desc: '大模型、AI 应用、AI SaaS 政策服务' },
  { href: '/company-match', title: '机器人与智能制造', desc: '首台套政策、产业用地、示范项目' },
  { href: '/company-match', title: '生物医药', desc: '研发补贴、临床批件、GMP 认证' },
  { href: '/company-match', title: '集成电路', desc: '流片补贴、EDA 工具、人才专项' },
  { href: '/company-match', title: '新能源新材料', desc: '绿色金融、碳中和政策、基地入驻' },
  { href: '/parks', title: '园区与产业服务机构', desc: '知识库 Bot、企业服务台、招商工具' },
];

const resourceLinks = [
  { href: '/dashboard', title: '政策仪表盘', desc: '查看企业政策红利与申报进度' },
  { href: '/login?register=1', title: '免费注册', desc: '注册后即可体验产品功能' },
  { href: '/policies', title: '政策知识库', desc: '浏览最新政策法规' },
  { href: '/pricing', title: '价格方案', desc: '产品目录与付费方式' },
  { href: '/about', title: '关于我们', desc: '团队与产品理念' },
  { href: '/security', title: '安全合规', desc: '数据安全与隐私保护' },
];

/* -------------------------------------------
   Mega Menu Component
   ------------------------------------------- */
interface MegaMenuProps {
  items: Array<{
    href: string;
    subtitle?: string;
    title: string;
    desc: string;
  }>;
  columns?: number;
  onNavigate: () => void;
}

function MegaMenu({ items, columns = 2, onNavigate }: MegaMenuProps) {
  return (
    <div
      className={`mega-menu ${columns === 1 ? 'mega-menu-single' : ''}`}
      style={columns !== 1 ? undefined : { minWidth: 280 }}
    >
      <div
        className="mega-menu-grid"
        style={columns !== 2 ? { gridTemplateColumns: '1fr' } : undefined}
      >
        {items.map((item) => (
          <Link
            key={item.title}
            href={item.href}
            className="mega-menu-item"
            onClick={onNavigate}
          >
            <div className="mega-menu-text">
              <h4>
                {item.title}
                {item.subtitle ? <span className="mega-menu-subtitle">{item.subtitle}</span> : null}
              </h4>
              <p>{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------
   Chevron SVG
   ------------------------------------------- */
function ChevronDown() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
        clipRule="evenodd"
      />
    </svg>
  );
}

/* -------------------------------------------
   Header Component
   ------------------------------------------- */
export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const navRef = useRef<HTMLElement>(null);
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Scroll detection for glass-morphism effect
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  // Close mega menu on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleMenuEnter = useCallback((menu: string) => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
    setOpenMenu(menu);
  }, []);

  const handleMenuLeave = useCallback(() => {
    closeTimerRef.current = setTimeout(() => {
      setOpenMenu(null);
    }, 150);
  }, []);

  const closeAll = useCallback(() => {
    setOpenMenu(null);
    setMobileOpen(false);
  }, []);

  return (
    <>
      <header className={`header ${scrolled ? 'scrolled' : ''}`}>
        <div className="header-inner">
          {/* Logo */}
          <Link href="/" className="header-logo" onClick={closeAll}>
            <Image
              src="/logo.png"
              alt="衍策引擎AI"
              width={40}
              height={40}
              className="header-logo-img"
              priority
            />
            <span>衍策引擎AI</span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="header-nav" ref={navRef} aria-label="主导航">
            {/* 产品 */}
            <div
              className={`nav-item ${openMenu === 'products' ? 'open' : ''}`}
              onMouseEnter={() => handleMenuEnter('products')}
              onMouseLeave={handleMenuLeave}
            >
              <button
                className="nav-trigger"
                aria-expanded={openMenu === 'products'}
                aria-haspopup="true"
                onClick={() =>
                  setOpenMenu(openMenu === 'products' ? null : 'products')
                }
              >
                产品
                <ChevronDown />
              </button>
              <MegaMenu
                items={productLinks}
                columns={2}
                onNavigate={closeAll}
              />
            </div>

            {/* 解决方案 */}
            <div
              className={`nav-item ${openMenu === 'solutions' ? 'open' : ''}`}
              onMouseEnter={() => handleMenuEnter('solutions')}
              onMouseLeave={handleMenuLeave}
            >
              <button
                className="nav-trigger"
                aria-expanded={openMenu === 'solutions'}
                aria-haspopup="true"
                onClick={() =>
                  setOpenMenu(openMenu === 'solutions' ? null : 'solutions')
                }
              >
                解决方案
                <ChevronDown />
              </button>
              <MegaMenu
                items={solutionLinks}
                columns={2}
                onNavigate={closeAll}
              />
            </div>

            {/* 资源 */}
            <div
              className={`nav-item ${openMenu === 'resources' ? 'open' : ''}`}
              onMouseEnter={() => handleMenuEnter('resources')}
              onMouseLeave={handleMenuLeave}
            >
              <button
                className="nav-trigger"
                aria-expanded={openMenu === 'resources'}
                aria-haspopup="true"
                onClick={() =>
                  setOpenMenu(openMenu === 'resources' ? null : 'resources')
                }
              >
                资源
                <ChevronDown />
              </button>
              <MegaMenu
                items={resourceLinks}
                columns={1}
                onNavigate={closeAll}
              />
            </div>

            {/* Simple links */}
            <Link href="/pricing">定价</Link>
            <Link href="/about">关于我们</Link>
          </nav>

          {/* Right Actions */}
          <div className="header-actions">
            <Link href="/login" className="header-login">
              登录
            </Link>
            <Link href="/login?register=1" className="btn btn-primary">
              免费开始
            </Link>

            {/* Mobile hamburger */}
            <button
              className={`mobile-toggle ${mobileOpen ? 'open' : ''}`}
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label={mobileOpen ? '关闭菜单' : '打开菜单'}
              aria-expanded={mobileOpen}
            >
              <span></span>
              <span></span>
              <span></span>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Overlay */}
      <div
        className={`mobile-overlay ${mobileOpen ? 'open' : ''}`}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />

      {/* Mobile Drawer */}
      <nav
        className={`mobile-menu ${mobileOpen ? 'open' : ''}`}
        aria-label="移动端导航"
      >
        <div className="mobile-section-title">产品</div>
        {productLinks.map((item) => (
          <Link
            key={item.title}
            href={item.href}
            onClick={() => setMobileOpen(false)}
          >
            {item.title}
          </Link>
        ))}

        <div className="mobile-section-title">解决方案</div>
        {solutionLinks.map((item) => (
          <Link
            key={item.title}
            href={item.href}
            onClick={() => setMobileOpen(false)}
          >
            {item.title}
          </Link>
        ))}

        <div className="mobile-section-title">资源</div>
        {resourceLinks.map((item) => (
          <Link
            key={item.title}
            href={item.href}
            onClick={() => setMobileOpen(false)}
          >
            {item.title}
          </Link>
        ))}

        <Link href="/pricing" onClick={() => setMobileOpen(false)}>
          定价
        </Link>
        <Link href="/about" onClick={() => setMobileOpen(false)}>
          关于我们
        </Link>

        <Link
          href="/login?register=1"
          className="btn btn-primary btn-lg"
          onClick={() => setMobileOpen(false)}
        >
          免费开始
        </Link>
      </nav>
    </>
  );
}
