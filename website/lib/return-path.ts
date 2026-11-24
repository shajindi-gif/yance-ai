const ROOTS = ['/dashboard','/feedback','/checkout','/discover','/companies','/opportunities','/applications','/projects','/documents','/reports','/orders','/billing','/team','/settings','/tasks','/agents','/notifications','/onboarding','/admin'];

/** Only known in-app pages may be a post-auth destination. */
export function safeReturnPath(value: string | null | undefined, fallback = '/dashboard'): string {
  if (!value || !value.startsWith('/') || /[\\\u0000-\u001f\u007f]/.test(value)) return fallback;
  try {
    const decoded = decodeURIComponent(value);
    if (decoded.startsWith('//') || /[\\\u0000-\u001f\u007f]/.test(decoded)) return fallback;
    const url = new URL(value, 'https://yance.invalid');
    if (url.origin !== 'https://yance.invalid' || !ROOTS.some(root => url.pathname === root || url.pathname.startsWith(root + '/'))) return fallback;
    return url.pathname + url.search + url.hash;
  } catch { return fallback; }
}
