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

const belongsTo = (routes: string[]) => (pathname: string) => routes.some(route => pathname === route || pathname.startsWith(`${route}/`));
export const WORKSPACE_NAVIGATION_GROUPS: {title: string; items: WorkspaceNavItem[]}[] = [{title: '企业工作区', items: [
  {href: '/dashboard', label: '问衍策', description: '提问与查看政策依据', icon: 'home', match: belongsTo(['/dashboard', '/consultant'])},
  {href: '/opportunities', label: '政策机会', description: '查找政策、核对条件', icon: 'opportunities', match: belongsTo(['/opportunities', '/discover', '/notifications'])},
  {href: '/applications', label: '申报项目', description: '补证、复核与执行记录', icon: 'applications', match: belongsTo(['/applications', '/projects', '/tasks', '/agents'])},
  {href: '/companies', label: '企业与资料', description: '企业事实、材料与报告', icon: 'companies', match: belongsTo(['/companies', '/documents', '/reports'])},
  {href: '/billing', label: '账户', description: '账单、订单与团队设置', icon: 'billing', match: belongsTo(['/billing', '/orders', '/team', '/settings'])},
]}];
export const WORKSPACE_NAVIGATION = WORKSPACE_NAVIGATION_GROUPS.flatMap(group => group.items);
export const WORKSPACE_BOTTOM_NAVIGATION: WorkspaceNavItem[] = [];
export const WORKSPACE_SECONDARY: Record<string, {href: string; label: string}[]> = {
  '/dashboard': [{href: '/dashboard', label: '问衍策'}, {href: '/consultant', label: '企业证据记录'}],
  '/opportunities': [{href: '/opportunities', label: '企业机会'}, {href: '/discover', label: '政策原文检索'}, {href: '/notifications', label: '通知'}],
  '/applications': [{href: '/applications', label: '申报项目'}, {href: '/projects', label: '项目总览'}, {href: '/tasks', label: '执行任务'}, {href: '/agents', label: '执行记录'}],
  '/companies': [{href: '/companies', label: '企业资料'}, {href: '/documents', label: '资料库'}, {href: '/reports', label: '报告'}],
  '/billing': [{href: '/billing', label: '用量与账单'}, {href: '/orders', label: '订单与发票'}, {href: '/team', label: '团队'}, {href: '/settings', label: '设置'}],
};

export const ADMIN_NAVIGATION: WorkspaceNavItem = {
  href: "/admin",
  label: "平台管理",
  description: "平台运营与真实指标",
  icon: "admin",
  match: (pathname) => pathname === "/admin" || pathname.startsWith("/admin/"),
};

export function isWorkspaceRoute(pathname: string): boolean {
  return WORKSPACE_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
}
