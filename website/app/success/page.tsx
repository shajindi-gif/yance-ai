'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api, { type Order } from '@/lib/api';

function PaymentResult() {
  const id = useSearchParams().get('order');
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    if (!api.isAuthenticated()) { setLoading(false); return; }
    api.getOrders().then(rows => {
      if (!active) return;
      const current = rows.find(row => row.id === id);
      setOrder(current ?? null);
      if (!current) setError('未找到当前账号可查看的这笔订单，请前往订单列表核对。');
    }).catch(() => { if (active) setError('暂时无法读取付款结果，请稍后刷新；请勿重复付款。'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id, retry]);
  const paid = order?.status === 'paid';
  const labels: Record<string,string> = {created:'等待付款确认',pending:'等待付款确认',cancelled:'订单已取消',refunded:'订单已退款',failed:'付款未完成'};
  return <main style={{minHeight:'100vh',background:'var(--paper)',padding:'140px 24px 48px'}}>
    <section style={{maxWidth:560,margin:'0 auto',padding:32,background:'var(--surface)',border:'1px solid var(--line)',borderRadius:16}} aria-busy={loading}>
      <h1 style={{fontSize:26}}>{loading ? '正在核对付款结果…' : paid ? '付款已确认' : labels[order?.status ?? ''] ?? '核对订单结果'}</h1>
      {error && <p role="alert">{error}</p>}
      {!api.isAuthenticated() ? <p><Link href={`/login?next=${encodeURIComponent('/success?order=' + (id ?? ''))}`}>登录后查看订单</Link></p> : <>
        {order && <p>订单号：{order.order_no} · ¥{Number(order.amount).toFixed(2)}</p>}
        <p role="status">{paid ? '可以前往报告页获取本订单授权的交付物，并在发票页申请开票。' : '若已完成付款，请稍后刷新确认。返回此页本身不会更改订单或授予权益。'}</p>
        {!paid && <button type="button" className="yc-btn-primary" disabled={loading} onClick={()=>setRetry(v=>v+1)}>{loading ? '正在核对…' : '刷新付款结果'}</button>}
      </>}
      <div style={{display:'flex',flexWrap:'wrap',gap:16,marginTop:24}}>
        <Link href="/orders">查看订单</Link>
        {paid && <><Link href="/reports">获取报告 →</Link><Link href="/invoices">申请开票</Link></>}
      </div>
    </section>
  </main>;
}
export default function PaymentReturnPage() { return <Suspense fallback={<p role="status">正在读取订单…</p>}><PaymentResult /></Suspense>; }
