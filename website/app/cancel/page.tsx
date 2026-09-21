import Link from 'next/link';

export const metadata = {
  title: '支付已取消 | 衍策引擎AI',
  robots: { index: false },
};

export default function PaymentCancelPage() {
  return (
    <main style={{ minHeight: '100vh', background: '#f8fafc', padding: '140px 24px 48px' }}>
      <section style={{ maxWidth: 560, margin: '0 auto', padding: 32, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <p style={{ color: '#b45309', fontWeight: 700 }}>支付已取消</p>
        <h1 style={{ color: '#0d1b2a', fontSize: 24, margin: '8px 0 12px' }}>订单仍保留，可随时重新支付</h1>
        <p style={{ color: '#64748b', lineHeight: 1.7 }}>
          你已退出支付流程，未产生扣款。订单会保留在工作区中，你可以稍后在订单页重新发起支付，或联系我们协助完成。
        </p>
        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <Link href="/orders" className="yc-btn-primary">返回订单</Link>
          <a href="mailto:contact@yance.ai" style={{ padding: '10px 16px', color: '#126a9a' }}>
            联系我们
          </a>
        </div>
      </section>
    </main>
  );
}
