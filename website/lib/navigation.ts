export interface WorkspaceNavItem {
  href: string;
  label: string;
  description: string;
  icon: "home" | "applications" | "reports" | "billing";
  match: (pathname: string) => boolean;
}

export const WORKSPACE_ROUTES = ["/dashboard", "/tasks", "/reports", "/orders"] as const;

export const WORKSPACE_NAVIGATION: WorkspaceNavItem[] = [
  {
    href: "/dashboard",
    label: "工作台",
    description: "企业与机会概览",
    icon: "home",
    match: (pathname) => pathname === "/dashboard",
  },
  {
    href: "/tasks",
    label: "任务与申报",
    description: "执行进度与交付",
    icon: "applications",
    match: (pathname) => pathname === "/tasks" || pathname.startsWith("/tasks/"),
  },
  {
    href: "/reports",
    label: "报告",
    description: "已授权的分析文件",
    icon: "reports",
    match: (pathname) => pathname === "/reports",
  },
  {
    href: "/orders",
    label: "订单与账单",
    description: "真实交易记录",
    icon: "billing",
    match: (pathname) => pathname === "/orders",
  },
];

export function isWorkspaceRoute(pathname: string): boolean {
  return WORKSPACE_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}
