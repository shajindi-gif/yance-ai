/** @type {import('next').NextConfig} */

// 支付供应商回调（如支付宝异步 notify）配置在主域 yance.ai/api/v1/*，
// 而 API 实际部署在 api.yance.ai。此 rewrite 让主域 /api/* 透明代理到 API，
// 保证回调可达；前端仍可直接使用 NEXT_PUBLIC_API_URL。
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || 'https://api.yance.ai';

// ACC-09: Content Security Policy.
// Pages are statically generated, so per-request nonces (which force dynamic
// rendering) are not used; script-src therefore keeps 'unsafe-inline' for
// Next's inline bootstrap. The policy still blocks third-party scripts, plugin
// content, framing, foreign <base>/form targets, and — most importantly for the
// localStorage token — network requests to any origin other than this site and
// the configured API. Set CSP_REPORT_ONLY=1 to observe without enforcing.
function apiOrigin() {
  const raw = process.env.NEXT_PUBLIC_API_URL || '';
  try {
    return /^https?:\/\//.test(raw) ? new URL(raw).origin : '';
  } catch {
    return '';
  }
}

function contentSecurityPolicy() {
  const isDev = process.env.NODE_ENV === 'development';
  const connect = ["'self'", apiOrigin(), isDev ? 'ws:' : ''].filter(Boolean).join(' ');
  return [
    "default-src 'self'",
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline'",
    // api.qrserver.com renders the WeChat Pay QR image today (tracked separately as ACC-22).
    "img-src 'self' data: blob: https://api.qrserver.com",
    "font-src 'self' data:",
    `connect-src ${connect}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join('; ');
}

const securityHeaders = [
  {
    key: process.env.CSP_REPORT_ONLY === '1' ? 'Content-Security-Policy-Report-Only' : 'Content-Security-Policy',
    value: contentSecurityPolicy(),
  },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
];

const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ];
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${API_PROXY_TARGET}/api/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
