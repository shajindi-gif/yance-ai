'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import api, { API_BASE } from '@/lib/api';

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  queued: { label: '排队中', color: '#ea580c', bg: '#fff7ed' },
  running: { label: '执行中', color: '#0ea5e9', bg: '#f0f9ff' },
  delivered: { label: '已交付', color: '#16a34a', bg: '#f0fdf4' },
  accepted: { label: '已验收', color: '#16a34a', bg: '#f0fdf4' },
  failed: { label: '失败', color: '#dc2626', bg: '#fef2f2' },
  revision_requested: { label: '修改中', color: '#ca8a04', bg: '#fffbeb' },
  awaiting_payment: { label: '待支付', color: '#ea580c', bg: '#fff7ed' },
};

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login'); return; }
    const load = () => fetch(`${API_BASE}/tasks`, { headers: { Authorization: `Bearer ${api.getToken()}` } }).then(r => r.json()).then(d => { setTasks(d); setLoading(false); }).catch(() => setLoading(false));
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [router]);

  if (loading) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>加载中...</div>;

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingTop: '80px' }}>
      <div style={{ maxWidth: '960px', margin: '0 auto', padding: '32px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div><h1 style={{ fontSize: '24px', fontWeight: 700, color: '#0d1b2a', margin: 0 }}>任务中心</h1><p style={{ fontSize: '13px', color: '#64748b', margin: '4px 0 0' }}>Agent 自动执行的业务任务</p></div>
          <Link href="/dashboard" style={{ fontSize: '13px', color: '#0ea5e9', textDecoration: 'none' }}>← 工作台</Link>
        </div>
        {tasks.length === 0 ? (
          <div style={{ background: '#fff', borderRadius: '16px', padding: '60px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🤖</div>
            <h3 style={{ color: '#0d1b2a', marginBottom: '8px' }}>暂无任务</h3>
            <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '20px' }}>创建第一个 Agent 任务，体验自动化政策分析</p>
            <Link href="/dashboard" style={{ display: 'inline-block', padding: '10px 24px', background: '#0ea5e9', color: '#fff', borderRadius: '8px', textDecoration: 'none', fontSize: '14px' }}>开始匹配</Link>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {tasks.map((t: any) => {
              const s = STATUS_MAP[t.status] || { label: t.status, color: '#64748b', bg: '#f1f5f9' };
              return (
                <Link key={t.id} href={`/tasks/${t.id}`} style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '20px 24px', textDecoration: 'none', display: 'block' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '8px' }}>
                    <div style={{ fontSize: '15px', fontWeight: 600, color: '#0d1b2a' }}>{t.title}</div>
                    <span style={{ padding: '3px 12px', borderRadius: '12px', fontSize: '11px', fontWeight: 500, color: s.color, background: s.bg }}>{s.label}</span>
                  </div>
                  {(t.status === 'running' || t.status === 'queued') && (
                    <div style={{ marginBottom: '8px' }}>
                      <div style={{ height: '6px', background: '#f1f5f9', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${t.progress || 0}%`, background: '#0ea5e9', borderRadius: '3px', transition: 'width 1s' }} />
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>{t.current_stage || '处理中'} ({t.progress || 0}%)</div>
                    </div>
                  )}
                  <div style={{ fontSize: '12px', color: '#94a3b8' }}>{new Date(t.created_at).toLocaleString('zh-CN')}</div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
