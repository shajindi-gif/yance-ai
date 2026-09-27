export interface WorkspaceNavItem {
  href: string;
  label: string;
  description: string;
  icon:
    | "home"
    | "discover"
    | "opportunities"
    | "applications"
    | "projects"
    | "companies"
    | "documents"
    | "consultant"
    | "notifications"
    | "agents"
    | "tasks"
    | "reports"
    | "billing"
    | "team"
    | "settings"
    | "admin";
  match: (pathname: string) => boolean;
}

export const WORKSPACE_ROUTES = [
  "/dashboard",
  "/discover",
  "/opportunities",
  "/applications",
  "/projects",
  "/companies",
  "/documents",
  "/consultant",
  "/notifications",
  "/agents",
  "/tasks",
  "/reports",
  "/orders",
  "/billing",
  "/team",
  "/settings",
  "/admin",
] as const;

/** Funding OS information architecture, grouped for the sidebar. */
export const WORKSPACE_NAVIGATION_GROUPS: { title: string; items: WorkspaceNavItem[] }[] = [
  {
    title: "Funding",
    items: [
      {
        href: "/dashboard",
        label: "指挥中心",
        description: "资金管道与行动建议",
        icon: "home",
        match: (pathname) => pathname === "/dashboard",
      },
      {
        href: "/discover",
        label: "发现资金",
        description: "政策 · 补贴 · 基金目录",
        icon: "discover",
        match: (pathname) => pathname === "/discover",
      },
      {
        href: "/opportunities",
        label: "我的机会",
        description: "匹配与资格状态",
        icon: "opportunities",
        match: (pathname) => pathname === "/opportunities" || pathname.startsWith("/opportunities/"),
      },
      {
        href: "/applications",
        label: "申报",
        description: "材料与执行进度",
        icon: "applications",
        match: (pathname) => pathname === "/applications" || pathname.startsWith("/applications/"),
      },
      {
        href: "/projects",
        label: "项目管道",
        description: "全生命周期与里程碑",
        icon: "projects",
        match: (pathname) => pathname === "/projects",
      },
    ],
  },
  {
    title: "Knowledge",
    items: [
      {
        href: "/companies",
        label: "企业档案",
        description: "画像与证据",
        icon: "companies",
        match: (pathname) => pathname === "/companies" || pathname.startsWith("/companies/"),
      },
      {
        href: "/documents",
        label: "资料库",
        description: "上传与摄取状态",
        icon: "documents",
        match: (pathname) => pathname === "/documents" || pathname.startsWith("/documents/"),
      },
      {
        href: "/consultant",
        label: "AI 顾问",
        description: "基于证据的资金咨询",
        icon: "consultant",
        match: (pathname) => pathname === "/consultant",
      },
      {
        href: "/notifications",
        label: "通知",
        description: "截止日与管道动态",
        icon: "notifications",
        match: (pathname) => pathname === "/notifications",
      },
    ],
  },
  {
    title: "Operations",
    items: [
      {
        href: "/reports",
        label: "报告",
        description: "已授权的分析文件",
        icon: "reports",
        match: (pathname) => pathname === "/reports",
      },
      {
        href: "/tasks",
        label: "执行任务",
        description: "运行进度与交付",
        icon: "tasks",
        match: (pathname) => pathname === "/tasks" || pathname.startsWith("/tasks/"),
      },
      {
        href: "/agents",
        label: "Agent 运行",
        description: "执行轨迹与质量状态",
        icon: "agents",
        match: (pathname) => pathname === "/agents" || pathname.startsWith("/agents/"),
      },
    ],
  },
];

export const WORKSPACE_NAVIGATION: WorkspaceNavItem[] =
  WORKSPACE_NAVIGATION_GROUPS.flatMap((group) => group.items);

export const WORKSPACE_BOTTOM_NAVIGATION: WorkspaceNavItem[] = [
  {
    href: "/billing",
    label: "用量与账单",
    description: "套餐、配额与交易",
    icon: "billing",
    match: (pathname) => pathname === "/billing" || pathname === "/orders",
  },
  {
    href: "/team",
    label: "团队",
    description: "成员与角色",
    icon: "team",
    match: (pathname) => pathname === "/team",
  },
  {
    href: "/settings",
    label: "设置",
    description: "API 与数据治理",
    icon: "settings",
    match: (pathname) => pathname === "/settings",
  },
];

export const ADMIN_NAVIGATION: WorkspaceNavItem = {
  href: "/admin",
  label: "Admin",
  description: "平台运营与真实指标",
  icon: "admin",
  match: (pathname) => pathname === "/admin" || pathname.startsWith("/admin/"),
};

export function isWorkspaceRoute(pathname: string): boolean {
  return WORKSPACE_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}
