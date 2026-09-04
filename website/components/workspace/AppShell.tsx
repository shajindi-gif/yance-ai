"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { WORKSPACE_NAVIGATION, type WorkspaceNavItem } from "@/lib/navigation";
import styles from "./AppShell.module.css";

function NavigationIcon({ icon }: Pick<WorkspaceNavItem, "icon">) {
  const paths: Record<WorkspaceNavItem["icon"], ReactNode> = {
    home: (
      <>
        <path d="M3 10.5 12 3l9 7.5" />
        <path d="M5.5 9.5V21h13V9.5" />
        <path d="M9.5 21v-7h5v7" />
      </>
    ),
    applications: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="M8 8h8M8 12h8M8 16h5" />
      </>
    ),
    opportunities: (
      <>
        <circle cx="12" cy="12" r="8" />
        <path d="m12 7 1.5 3.5L17 12l-3.5 1.5L12 17l-1.5-3.5L7 12l3.5-1.5z" />
      </>
    ),
    companies: (
      <>
        <path d="M4 21V5l8-3v19M12 8h8v13M8 7v2M8 12v2M8 17v2M16 12v2M16 17v2M2 21h20" />
      </>
    ),
    tasks: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="m8 8 1.5 1.5L12 7M8 14l1.5 1.5L12 13M14 9h2M14 15h2" />
      </>
    ),
    agents: (
      <>
        <circle cx="12" cy="8" r="3" />
        <path d="M6 21v-2a6 6 0 0 1 12 0v2M4 10h2M18 10h2M12 3V1" />
      </>
    ),
    documents: (
      <>
        <path d="M5 3h10l4 4v14H5z" />
        <path d="M15 3v5h4M8 13h8M8 17h6" />
      </>
    ),
    reports: (
      <>
        <path d="M5 3h10l4 4v14H5z" />
        <path d="M15 3v5h4M8 13h8M8 17h8" />
      </>
    ),
    billing: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <path d="M3 10h18M7 15h3" />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.8">
      {paths[icon]}
    </svg>
  );
}

interface AppShellProps {
  children: ReactNode;
  workspaceName?: string;
}

export default function AppShell({ children, workspaceName }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const activeItem = WORKSPACE_NAVIGATION.find((item) => item.match(pathname));

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  const logout = () => {
    api.clearToken();
    router.push("/login");
  };

  return (
    <div className={styles.shell}>
      <aside className={`${styles.sidebar} ${mobileOpen ? styles.sidebarOpen : ""}`}>
        <div className={styles.brandRow}>
          <Link href="/dashboard" className={styles.brand} aria-label="返回工作台">
            <Image src="/logo.png" alt="" width={34} height={34} priority />
            <span>
              <strong>衍策引擎</strong>
              <small>Yance Workspace</small>
            </span>
          </Link>
          <button
            type="button"
            className={styles.mobileClose}
            onClick={() => setMobileOpen(false)}
            aria-label="关闭工作区导航"
          >
            ×
          </button>
        </div>

        <div className={styles.workspaceIdentity}>
          <span className={styles.workspaceAvatar}>{(workspaceName || "Y").slice(0, 1)}</span>
          <span>
            <small>当前工作区</small>
            <strong>{workspaceName || "企业工作区"}</strong>
          </span>
        </div>

        <nav className={styles.navigation} aria-label="工作区导航">
          <p className={styles.navLabel}>Workspace</p>
          {WORKSPACE_NAVIGATION.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
                aria-current={active ? "page" : undefined}
              >
                <NavigationIcon icon={item.icon} />
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.description}</small>
                </span>
              </Link>
            );
          })}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.phaseNote}>
            <span>产品升级中</span>
            <p>Agent 运行已接入持久化轨迹；知识库与管理后台将按阶段开放。</p>
          </div>
          <Link href="/" className={styles.secondaryAction}>
            返回产品官网
          </Link>
          <button type="button" className={styles.logout} onClick={logout}>
            退出登录
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className={styles.backdrop}
          onClick={() => setMobileOpen(false)}
          aria-label="关闭工作区导航"
        />
      )}

      <div className={styles.workspace}>
        <header className={styles.topbar}>
          <button
            type="button"
            className={styles.mobileMenu}
            onClick={() => setMobileOpen(true)}
            aria-label="打开工作区导航"
            aria-expanded={mobileOpen}
          >
            <span />
            <span />
            <span />
          </button>
          <div>
            <span className={styles.topbarEyebrow}>Workspace</span>
            <strong>{activeItem?.label || "工作区"}</strong>
          </div>
          <span className={styles.environmentBadge}>服务端数据</span>
        </header>
        <main id="main-content" className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
}
