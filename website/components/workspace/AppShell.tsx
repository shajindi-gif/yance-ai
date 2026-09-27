"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import {
  ADMIN_NAVIGATION,
  WORKSPACE_BOTTOM_NAVIGATION,
  WORKSPACE_NAVIGATION,
  WORKSPACE_NAVIGATION_GROUPS,
  type WorkspaceNavItem,
} from "@/lib/navigation";
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
    discover: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="m15.5 8.5-2 5-5 2 2-5z" />
      </>
    ),
    projects: (
      <>
        <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <path d="M8 13h8" />
      </>
    ),
    consultant: (
      <>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        <path d="m12 7 1 2.5L15.5 10 13 11l-1 2.5-1-2.5L8.5 10 11 9.5z" />
      </>
    ),
    notifications: (
      <>
        <path d="M18 9a6 6 0 1 0-12 0c0 6-2.5 7-2.5 7h17S18 15 18 9" />
        <path d="M10 20a2.2 2.2 0 0 0 4 0" />
      </>
    ),
    team: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 20v-1.5A4.5 4.5 0 0 1 7.5 14h3A4.5 4.5 0 0 1 15 18.5V20" />
        <path d="M16 4.5a3 3 0 0 1 0 7M18 14a4 4 0 0 1 3 3.9V20" />
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
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.5V21h-4v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.5-1H3v-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.5V3h4v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.5 1h.1v4h-.1a1.7 1.7 0 0 0-1.5 1Z" />
      </>
    ),
    admin: (
      <>
        <path d="M12 3 4.5 6v5c0 4.7 2.8 8.2 7.5 10 4.7-1.8 7.5-5.3 7.5-10V6z" />
        <path d="M9 12h6M12 9v6" />
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
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
  const [unread, setUnread] = useState(0);
  const allItems = [...WORKSPACE_NAVIGATION, ...WORKSPACE_BOTTOM_NAVIGATION, ADMIN_NAVIGATION];
  const activeItem = allItems.find((item) => item.match(pathname));

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  useEffect(() => {
    let active = true;
    if (!api.isAuthenticated()) return;
    api.getMe().then((user) => {
      if (active) setIsPlatformAdmin(user.is_platform_admin);
    }).catch(() => {
      if (active) setIsPlatformAdmin(false);
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!api.isAuthenticated()) return;
    let active = true;
    const load = () => {
      api.getUnreadNotificationCount()
        .then((result) => { if (active) setUnread(result.unread); })
        .catch(() => { if (active) setUnread(0); });
    };
    load();
    const timer = setInterval(load, 60_000);
    return () => { active = false; clearInterval(timer); };
  }, [pathname]);

  const logout = () => {
    api.clearToken();
    router.push("/login");
  };

  const renderNavItem = (item: WorkspaceNavItem) => {
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
  };

  return (
    <div className={styles.shell}>
      <aside className={`${styles.sidebar} ${mobileOpen ? styles.sidebarOpen : ""}`}>
        <div className={styles.brandRow}>
          <Link href="/dashboard" className={styles.brand} aria-label="返回工作台">
            <Image src="/logo.png" alt="" width={34} height={34} priority />
            <span>
              <strong>衍策引擎</strong>
              <small>Yance Funding OS</small>
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
          {WORKSPACE_NAVIGATION_GROUPS.map((group) => (
            <div key={group.title}>
              <p className={styles.navLabel}>{group.title}</p>
              {group.items.map(renderNavItem)}
            </div>
          ))}
          <p className={styles.navLabel}>Account</p>
          {WORKSPACE_BOTTOM_NAVIGATION.map(renderNavItem)}
          {isPlatformAdmin ? renderNavItem(ADMIN_NAVIGATION) : null}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.phaseNote}>
            <span>Funding OS</span>
            <p>资格结论、证据与管道均读取服务端记录，不展示推测数据。</p>
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
            <span className={styles.topbarEyebrow}>Funding OS</span>
            <strong>{activeItem?.label || "工作区"}</strong>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
            <Link
              href="/notifications"
              aria-label={unread > 0 ? `通知，${unread} 条未读` : "通知"}
              style={{ position: "relative", display: "inline-flex", padding: 4, color: "inherit" }}
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
                <path d="M18 9a6 6 0 1 0-12 0c0 6-2.5 7-2.5 7h17S18 15 18 9" />
                <path d="M10 20a2.2 2.2 0 0 0 4 0" />
              </svg>
              {unread > 0 ? (
                <span
                  style={{
                    position: "absolute",
                    top: -2,
                    right: -4,
                    minWidth: 16,
                    height: 16,
                    padding: "0 4px",
                    borderRadius: 8,
                    background: "#f97316",
                    color: "#fff",
                    fontSize: 10,
                    fontWeight: 700,
                    lineHeight: "16px",
                    textAlign: "center",
                  }}
                >
                  {unread > 99 ? "99+" : unread}
                </span>
              ) : null}
            </Link>
            <span className={styles.environmentBadge}>服务端数据</span>
          </div>
        </header>
        <main id="main-content" className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
}
