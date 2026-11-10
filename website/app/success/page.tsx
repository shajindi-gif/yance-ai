'use client';

import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api, { type Order } from '@/lib/api';
import pageStyles from './page.module.css';

function PaymentResult() {
  const id = useSearchParams().get('order');
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setLoading(true); setError('');
    const signedIn = api.isAuthenticated();
    setAuthenticated(signedIn);
    if (!signedIn) { setLoading(false); return; }
    api.getOrders().then(rows => {
      if (!active) return;
      const current = rows.find(row => row.id === id);
      setOrder(current ?? null);
      if (current && ['created','pending'].includes(current.status) && retry < 20) timer = setTimeout(() => setRetry(v=>v+1), 3000);
      if (!current) setError('未找到当前账号可查看的这笔订单，请前往订单列表核对。');
    }).catch(() => { if (active) setError('暂时无法读取付款结果，请稍后刷新；请勿重复付款。'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [id, retry]);
  const currentOrder = order?.id === id ? order : null;
  const paid = currentOrder?.status === 'paid';
  const labels: Record<string,string> = {created:'等待付款确认',pending:'等待付款确认',cancelled:'订单已取消',refunded:'订单已退款',failed:'付款未完成'};
  return <main className={pageStyles.section}>
    <section className={pageStyles.section2} aria-busy={loading}>
      <h1 className={pageStyles.heading}>{loading && !currentOrder ? '正在核对付款结果…' : paid ? '付款已确认' : labels[currentOrder?.status ?? ''] ?? '核对订单结果'}</h1>
      {error && <p role="alert">{error}</p>}
      {authenticated === null ? <p role="status">正在读取登录状态…</p> : !authenticated ? <p><Link href={`/login?next=${encodeURIComponent('/success?order=' + (id ?? ''))}`}>登录后查看订单</Link></p> : <>
        {currentOrder && <p>订单号：{currentOrder.order_no} · ¥{Number(currentOrder.amount).toFixed(2)}</p>}
        <p role="status">{paid ? '可以前往报告页获取本订单授权的交付物，并在发票页申请开票。' : '若已完成付款，请稍后刷新确认。返回此页本身不会更改订单或授予权益。'}</p>
        {!paid && <button type="button" className="yc-btn-primary" disabled={loading} onClick={()=>setRetry(v=>v+1)}>{loading ? '正在核对…' : '刷新付款结果'}</button>}
      </>}
      <div className={pageStyles.layout}>
        <Link href="/orders">查看订单</Link>
        {paid && <><Link href="/reports">获取报告 →</Link><Link href="/billing">申请开票</Link></>}
      </div>
    </section>
  </main>;
}
export default function PaymentReturnPage() { return <Suspense fallback={<p role="status">正在读取订单…</p>}><PaymentResult /></Suspense>; }
