export interface WorkspaceNavItem {
  href: string;
  label: string;
  description: string;
  icon: "home" | "opportunities" | "companies" | "applications" | "agents" | "tasks" | "documents" | "reports" | "billing";
  match: (pathname: string) => boolean;
}

export const WORKSPACE_ROUTES = [
  "/dashboard",
  "/opportunities",
  "/companies",
  "/applications",
  "/documents",
  "/agents",
  "/tasks",
  "/reports",
  "/orders",
] as const;

export const WORKSPACE_NAVIGATION: WorkspaceNavItem[] = [
  {
    href: "/dashboard",
    label: "工作台",
    description: "企业与机会概览",
    icon: "home",
    match: (pathname) => pathname === "/dashboard",
  },
  {
    href: "/opportunities",
    label: "政策机会",
    description: "匹配与资格状态",
    icon: "opportunities",
    match: (pathname) => pathname === "/opportunities" || pathname.startsWith("/opportunities/"),
  },
  {
    href: "/companies",
    label: "企业",
    description: "画像与版本",
    icon: "companies",
    match: (pathname) => pathname === "/companies" || pathname.startsWith("/companies/"),
  },
  {
    href: "/applications",
    label: "申报项目",
    description: "材料与执行进度",
    icon: "applications",
    match: (pathname) => pathname === "/applications" || pathname.startsWith("/applications/"),
  },
  {
    href: "/agents",
    label: "Agent 运行",
    description: "执行轨迹与质量状态",
    icon: "agents",
    match: (pathname) => pathname === "/agents" || pathname.startsWith("/agents/"),
  },
  {
    href: "/documents",
    label: "企业资料",
    description: "上传与摄取状态",
    icon: "documents",
    match: (pathname) => pathname === "/documents" || pathname.startsWith("/documents/"),
  },
  {
    href: "/tasks",
    label: "执行任务",
    description: "运行进度与交付",
    icon: "tasks",
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
