import Link from 'next/link';

export const metadata = {
  title: '页面不存在 | 衍策引擎AI',
  robots: { index: false },
};

export default function NotFound() {
  return (
    <section
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0d1b2a 0%, #1b2d45 50%, #142842 100%)',
        padding: '120px 24px 64px',
      }}
    >
      <div style={{ maxWidth: 520, textAlign: 'center' }}>
        <p style={{ color: '#6cbce4', fontWeight: 700, fontSize: 14, letterSpacing: '0.08em', margin: '0 0 12px' }}>
          404
        </p>
        <h1 style={{ color: '#fff', fontSize: 28, fontWeight: 700, margin: '0 0 12px' }}>
          页面不存在或已移动
        </h1>
        <p style={{ color: 'rgba(255,255,255,0.65)', lineHeight: 1.7, margin: '0 0 28px' }}>
          你访问的地址可能已下线。可以回到首页继续，或查看政策知识库与产品目录。
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link
            href="/"
            style={{
              padding: '12px 28px',
              background: '#f97316',
              color: '#fff',
              borderRadius: 10,
              fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            回到首页
          </Link>
          <Link
            href="/policies"
            style={{
              padding: '12px 28px',
              border: '1px solid rgba(255,255,255,0.3)',
              color: 'rgba(255,255,255,0.85)',
              borderRadius: 10,
              fontWeight: 600,
              textDecoration: 'none',
            }}
          >
            政策知识库
          </Link>
        </div>
      </div>
    </section>
  );
}
