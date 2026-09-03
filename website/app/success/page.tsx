import Link from 'next/link';

export default function PaymentReturnPage() {
  return (
    <main style={{ minHeight: '100vh', background: '#f8fafc', padding: '140px 24px 48px' }}>
      <section style={{ maxWidth: 560, margin: '0 auto', padding: 32, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 16 }}>
        <p style={{ color: '#0ea5e9', fontWeight: 700 }}>支付状态确认中</p>
        <h1 style={{ color: '#0d1b2a', fontSize: 24 }}>请以订单状态为准</h1>
        <p style={{ color: '#64748b', lineHeight: 1.7 }}>
          返回成功页不等于支付已完成。系统只会在收到并验证支付供应商的服务端回调后更新订单和权益。
        </p>
        <div style={{ display: 'flex', gap: 12, marginTop: 24 }}>
          <Link href="/orders" className="yc-btn-primary">查看订单</Link>
          <Link href="/reports" style={{ padding: '10px 16px', color: '#0369a1' }}>查看报告</Link>
        </div>
      </section>
    </main>
  );
}
