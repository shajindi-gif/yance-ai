'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';

/* 扁平导航：每个入口对应一个真实可访问的页面，无占位项、无路线图项。 */
const NAV_LINKS = [
  { href: '/company-match', label: '政策匹配' },
  { href: '/parks', label: '园区服务' },
  { href: '/brief-maker', label: '报告与材料' },
  { href: '/policy-knowledge-base', label: '政策库' },
  { href: '/pricing', label: '价格' },
  { href: '/about', label: '关于我们' },
];

export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  const closeAll = () => setMobileOpen(false);

  return (
    <>
      <header className={`header ${scrolled ? 'scrolled' : ''}`}>
        <div className="header-inner">
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

          <nav className="header-nav" aria-label="主导航">
            {NAV_LINKS.map((item) => (
              <Link key={item.href} href={item.href}>
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="header-actions">
            <Link href="/login" className="header-login">
              登录
            </Link>
            <Link href="/login?register=1" className="btn btn-primary">
              免费开始
            </Link>

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

      <div
        className={`mobile-overlay ${mobileOpen ? 'open' : ''}`}
        onClick={closeAll}
        aria-hidden="true"
      />

      <nav
        className={`mobile-menu ${mobileOpen ? 'open' : ''}`}
        aria-label="移动端导航"
      >
        {NAV_LINKS.map((item) => (
          <Link key={item.href} href={item.href} onClick={closeAll}>
            {item.label}
          </Link>
        ))}
        <Link href="/login" onClick={closeAll}>
          登录
        </Link>
        <Link
          href="/login?register=1"
          className="btn btn-primary btn-lg"
          onClick={closeAll}
        >
          免费开始
        </Link>
      </nav>
    </>
  );
}
