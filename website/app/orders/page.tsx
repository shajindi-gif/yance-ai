'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';

interface OrderItem {
  id: string;
  order_no: string;
  product_code: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
}

const PRODUCT_NAMES: Record<string, string> = {
  POLICY_REPORT: '企业政策 AI 体检报告',
  POLICY_DIAGNOSIS: '单项目申报诊断',
  APPLICATION_PLAN: 'AI 申报方案包',
  APPLICATION_DRAFT: 'AI 申报材料初稿',
};

const STATUS_LABELS: Record<string, { text: string; color: string }> = {
  created: { text: '待支付', color: '#ea580c' },
  pending: { text: '待支付', color: '#ea580c' },
  paid: { text: '已支付', color: '#16a34a' },
  completed: { text: '已完成', color: '#16a34a' },
  cancelled: { text: '已取消', color: '#94a3b8' },
  refunded: { text: '已退款', color: '#64748b' },
};

export default function OrdersPage() {
  const router = useRouter();
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login'); return; }
    api.getOrders().then(data => { setOrders(data); setLoading(false); }).catch(() => setLoading(false));
  }, [router]);

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
      <div style={{ color: '#64748b' }}>加载中...</div>
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingTop: '80px' }}>
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '32px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#0d1b2a', margin: '0 0 4px' }}>订单记录</h1>
            <p style={{ fontSize: '13px', color: '#64748b', margin: 0 }}>所有购买记录与发票状态</p>
          </div>
          <Link href="/dashboard" style={{ fontSize: '13px', color: '#0ea5e9', textDecoration: 'none' }}>← 返回工作台</Link>
        </div>

        {orders.length === 0 ? (
          <div style={{ background: '#fff', borderRadius: '16px', padding: '60px 32px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
            <h3 style={{ fontSize: '16px', color: '#0d1b2a', marginBottom: '8px' }}>暂无订单</h3>
            <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>开始政策匹配后可购买专业报告</p>
            <Link href="/dashboard" style={{ display: 'inline-block', padding: '10px 24px', background: '#0ea5e9', color: '#fff', borderRadius: '8px', textDecoration: 'none', fontSize: '14px' }}>开始匹配</Link>
          </div>
        ) : (
          <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
                  <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#64748b' }}>订单号</th>
                  <th style={{ padding: '14px 16px', textAlign: 'left', fontSize: '12px', fontWeight: 600, color: '#64748b' }}>产品</th>
                  <th style={{ padding: '14px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#64748b' }}>金额</th>
                  <th style={{ padding: '14px 16px', textAlign: 'center', fontSize: '12px', fontWeight: 600, color: '#64748b' }}>状态</th>
                  <th style={{ padding: '14px 16px', textAlign: 'right', fontSize: '12px', fontWeight: 600, color: '#64748b' }}>日期</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(order => {
                  const status = STATUS_LABELS[order.status] || { text: order.status, color: '#64748b' };
                  return (
                    <tr key={order.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                      <td style={{ padding: '14px 16px', fontSize: '13px', color: '#0d1b2a', fontFamily: 'monospace' }}>{order.order_no}</td>
                      <td style={{ padding: '14px 16px', fontSize: '13px', color: '#0d1b2a' }}>{PRODUCT_NAMES[order.product_code] || order.product_code}</td>
                      <td style={{ padding: '14px 16px', fontSize: '13px', color: '#0d1b2a', textAlign: 'right', fontWeight: 600 }}>¥{order.amount}</td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <span style={{ display: 'inline-block', padding: '3px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: 500, background: status.color + '18', color: status.color }}>{status.text}</span>
                      </td>
                      <td style={{ padding: '14px 16px', fontSize: '12px', color: '#64748b', textAlign: 'right' }}>{new Date(order.created_at).toLocaleDateString('zh-CN')}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
