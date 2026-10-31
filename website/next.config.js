/** @type {import('next').NextConfig} */

// 支付供应商回调（如支付宝异步 notify）配置在主域 yance.ai/api/v1/*，
// 而 API 实际部署在 api.yance.ai。此 rewrite 让主域 /api/* 透明代理到 API，
// 保证回调可达；前端仍可直接使用 NEXT_PUBLIC_API_URL。
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || 'https://api.yance.ai';

const securityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Content-Security-Policy', value: "base-uri 'self'; object-src 'none'; frame-ancestors 'none'" },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
];

const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  async headers() {
    return [
      ...['admin','dashboard','onboarding','orders','billing','settings','tasks','companies',
          'documents','applications','opportunities','reports','agents','checkout','success',
          'team','invoices','feedback','policy-scan','login'].map(path => ({
        source: `/${path}/:path*`,
        headers: [{ key: 'X-Robots-Tag', value: 'noindex, nofollow' }],
      })),
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
