'use client';
import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import api, { API_BASE } from '@/lib/api';

const STAGES = [
  { key: 10, label: '企业画像读取' },
  { key: 30, label: '政策检索与匹配' },
  { key: 60, label: '申报条件分析' },
  { key: 80, label: '报告文件生成' },
  { key: 100, label: '交付物生成' },
];

export default function TaskDetailPage() {
  const { taskId } = useParams();
  const router = useRouter();
  const [task, setTask] = useState<any>(null);
  const [actions, setActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!api.isAuthenticated()) { router.push('/login'); return; }
    const load = () => {
      fetch(`${API_BASE}/tasks/${taskId}`, { headers: { Authorization: `Bearer ${api.getToken()}` } })
        .then(r => r.json()).then(d => { setTask(d); setLoading(false); }).catch(() => setLoading(false));
    };
    load();
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [taskId, router]);

  useEffect(() => {
    if (task && (task.status === 'delivered' || task.status === 'accepted')) {
      fetch(`${API_BASE}/tasks/${taskId}/next-actions`, { headers: { Authorization: `Bearer ${api.getToken()}` } })
        .then(r => r.json()).then(d => setActions(d.actions || [])).catch(() => {});
    }
  }, [task?.status, taskId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${API_BASE}/tasks/${taskId}/download`, { headers: { Authorization: `Bearer ${api.getToken()}` } });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = '政策分析报告.pdf'; a.click(); URL.revokeObjectURL(url);
    } catch {} finally { setDownloading(false); }
  };

  const handleAccept = async () => {
    await fetch(`${API_BASE}/tasks/${taskId}/accept`, { method: 'POST', headers: { Authorization: `Bearer ${api.getToken()}` } });
    setTask((prev: any) => ({ ...prev, status: 'accepted' }));
  };

  const handleRevision = async () => {
    const request = prompt('请描述修改要求：');
    if (!request || !task?.deliverables?.length) return;
    await fetch(`${API_BASE}/tasks/${taskId}/revision`, {
      method: 'POST', headers: { Authorization: `Bearer ${api.getToken()}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ deliverable_id: task.deliverables[0].id, request })
    });
    setTask((prev: any) => ({ ...prev, status: 'revision_requested' }));
  };

  if (loading) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>加载中...</div>;
  if (!task) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#dc2626' }}>任务不存在</div>;

  const isRunning = task.status === 'running' || task.status === 'queued';
  const isDone = task.status === 'delivered' || task.status === 'accepted';
  const progress = task.progress || 0;

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingTop: '80px' }}>
      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '32px 24px' }}>
        <Link href="/tasks" style={{ fontSize: '13px', color: '#0ea5e9', textDecoration: 'none', display: 'block', marginBottom: '16px' }}>← 任务中心</Link>

        {/* Header */}
        <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '28px', marginBottom: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '12px' }}>
            <div>
              <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#0d1b2a', margin: '0 0 4px' }}>{task.title}</h1>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>Task ID: {task.id}</p>
            </div>
            <span style={{ padding: '4px 14px', borderRadius: '12px', fontSize: '12px', fontWeight: 500, background: isDone ? '#f0fdf4' : isRunning ? '#f0f9ff' : '#fef2f2', color: isDone ? '#16a34a' : isRunning ? '#0ea5e9' : '#dc2626' }}>
              {task.status === 'delivered' ? '已交付' : task.status === 'accepted' ? '已验收' : task.status === 'running' ? '执行中' : task.status === 'queued' ? '排队中' : task.status}
            </span>
          </div>
          <div style={{ fontSize: '13px', color: '#64748b' }}>企业: {task.company_name} | 创建: {new Date(task.created_at).toLocaleString('zh-CN')}</div>
        </div>

        {/* Progress */}
        {(isRunning || isDone) && (
          <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '28px', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#0d1b2a', margin: '0 0 16px' }}>Agent 执行进度</h2>
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ fontSize: '13px', color: '#374151' }}>{task.current_stage || (isDone ? '已完成' : '处理中')}</span>
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#0ea5e9' }}>{progress}%</span>
              </div>
              <div style={{ height: '8px', background: '#f1f5f9', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${progress}%`, background: 'linear-gradient(90deg, #0ea5e9, #38bdf8)', borderRadius: '4px', transition: 'width 1s ease' }} />
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {STAGES.map(stage => {
                const done = progress >= stage.key;
                const active = !done && progress >= (STAGES[STAGES.indexOf(stage) - 1]?.key || 0);
                return (
                  <div key={stage.key} style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
                    <span style={{ width: '20px', height: '20px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', background: done ? '#16a34a' : active ? '#0ea5e9' : '#f1f5f9', color: done || active ? '#fff' : '#94a3b8' }}>
                      {done ? '✓' : active ? '●' : '○'}
                    </span>
                    <span style={{ color: done ? '#0d1b2a' : active ? '#0ea5e9' : '#94a3b8', fontWeight: done || active ? 500 : 400 }}>{stage.label}</span>
                  </div>
                );
              })}
            </div>
            {isRunning && <p style={{ fontSize: '12px', color: '#94a3b8', textAlign: 'center', marginTop: '16px' }}>Agent 正在工作，页面自动刷新...</p>}
          </div>
        )}

        {/* Actions when done */}
        {isDone && task.deliverables?.length > 0 && (
          <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '28px', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#0d1b2a', margin: '0 0 16px' }}>交付物</h2>
            {task.deliverables.map((d: any) => (
              <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f1f5f9' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 500, color: '#0d1b2a' }}>{d.title} (V{d.version})</div>
                  <div style={{ fontSize: '11px', color: '#94a3b8' }}>质量分: {d.quality_score} | {new Date(d.generated_at).toLocaleString('zh-CN')}</div>
                </div>
                <button onClick={handleDownload} disabled={downloading} style={{ padding: '8px 20px', borderRadius: '8px', border: 'none', background: downloading ? '#94a3b8' : '#0ea5e9', color: '#fff', fontSize: '13px', cursor: downloading ? 'not-allowed' : 'pointer' }}>
                  {downloading ? '下载中...' : '下载 PDF'}
                </button>
              </div>
            ))}
            {task.status === 'delivered' && (
              <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                <button onClick={handleAccept} style={{ flex: 1, padding: '12px', borderRadius: '8px', border: 'none', background: '#16a34a', color: '#fff', fontSize: '14px', fontWeight: 600, cursor: 'pointer' }}>✓ 确认验收</button>
                <button onClick={handleRevision} style={{ flex: 1, padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0', background: '#fff', color: '#64748b', fontSize: '14px', cursor: 'pointer' }}>申请修改</button>
              </div>
            )}
          </div>
        )}

        {/* Next Best Action */}
        {isDone && actions.length > 0 && (
          <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '28px', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#0d1b2a', margin: '0 0 4px' }}>下一步建议</h2>
            <p style={{ fontSize: '12px', color: '#94a3b8', margin: '0 0 16px' }}>根据本次分析结果，推荐以下行动</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {actions.map((a: any, i: number) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 16px', background: '#f8fafc', borderRadius: '10px', border: '1px solid #f1f5f9' }}>
                  <div>
                    <div style={{ fontSize: '14px', fontWeight: 500, color: '#0d1b2a' }}>{i + 1}. {a.action}</div>
                    <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{a.desc}</div>
                  </div>
                  {a.product_code ? (
                    <Link href="/pricing" style={{ padding: '8px 16px', borderRadius: '8px', background: '#f97316', color: '#fff', fontSize: '12px', fontWeight: 500, textDecoration: 'none', whiteSpace: 'nowrap' }}>{a.cta}</Link>
                  ) : (
                    <span style={{ padding: '8px 16px', borderRadius: '8px', background: '#f1f5f9', color: '#94a3b8', fontSize: '12px', whiteSpace: 'nowrap' }}>{a.cta}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Agent Activity Log */}
        {task.agent_runs?.length > 0 && (
          <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', padding: '28px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#0d1b2a', margin: '0 0 12px' }}>Agent 执行日志</h2>
            {task.agent_runs.map((r: any, i: number) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '6px 0', fontSize: '12px' }}>
                <span style={{ color: r.status === 'completed' ? '#16a34a' : '#0ea5e9' }}>{r.status === 'completed' ? '✓' : '●'}</span>
                <span style={{ color: '#374151' }}>{r.agent}</span>
                {r.latency_ms && <span style={{ color: '#94a3b8', marginLeft: 'auto' }}>{r.latency_ms}ms</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
