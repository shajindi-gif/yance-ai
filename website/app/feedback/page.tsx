'use client';

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import api, { type FeedbackItem } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { InlineAlert } from '@/components/ui/InlineAlert';
import styles from './page.module.css';

const STATUS: Record<string, string> = { open: '已收到', reviewing: '处理中', resolved: '已处理', dismissed: '已归档' };
const CATEGORY: Record<string, string> = { product: '功能与体验建议', data: '数据来源问题', policy: '政策内容问题', billing: '订单与计费问题', support: '其他使用问题' };

export default function FeedbackPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [ready, setReady] = useState(false);
  const [revision, setRevision] = useState(0);
  const [category, setCategory] = useState('product');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const [history, setHistory] = useState<FeedbackItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const pending = useRef(false);
  const request = useRef<{ signature: string; id: string } | null>(null);

  const refreshHistory = useCallback(async () => {
    setHistoryLoading(true); setHistoryError('');
    try { setHistory(await api.getMyFeedback()); }
    catch { setHistoryError('反馈进度暂时无法读取，请重试。'); setAuthenticated(api.isAuthenticated()); }
    finally { setHistoryLoading(false); }
  }, []);

  useEffect(() => {
    let active = true;
    setAuthenticated(api.isAuthenticated());
    api.getAuthConfig().then(config => {
      if (!active) return;
      const supported = config.feedback_revision === 1;
      setRevision(supported ? 1 : 0); setReady(true);
      if (supported && api.isAuthenticated()) void refreshHistory();
    });
    return () => { active = false; };
  }, [refreshHistory]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current || !ready || !api.isAuthenticated() || message.trim().length < 2) return;
    pending.current = true; setBusy(true); setError(''); setSent(false);
    const trimmed = message.trim();
    const signature = JSON.stringify([category, trimmed]);
    if (revision === 1 && request.current?.signature !== signature) request.current = { signature, id: crypto.randomUUID() };
    try {
      await api.submitFeedback(category, trimmed, revision === 1 ? request.current?.id : undefined);
      setMessage(''); setSent(true); request.current = null;
      if (revision === 1) void refreshHistory();
    } catch {
      setAuthenticated(api.isAuthenticated());
      setError('反馈未确认提交成功，内容已保留。请检查登录状态后重试；若网络中断，请先核对下方进度，避免重复提交。');
    } finally { pending.current = false; setBusy(false); }
  }

  return <section className={styles.page}>
    <Link href="/#customer-feedback">← 返回使用场景与反馈</Link>
    <h1>分享使用反馈</h1>
    <p>告诉我们使用中遇到的问题与改进建议。反馈用于产品改进，不自动成为公开案例或客户评价；公开前会另行征得授权。</p>
    {!authenticated ? <InlineAlert tone="info">请先<Link href="/login?next=%2Ffeedback">登录账号</Link>，登录后会回到此页。</InlineAlert> : null}
    <form onSubmit={submit} className={styles.form} aria-busy={busy}>
      <label htmlFor="feedback-category">反馈类型</label>
      <select id="feedback-category" value={category} disabled={busy} onChange={event => { setCategory(event.target.value); setSent(false); }}>
        {Object.entries(CATEGORY).map(([value,label]) => <option key={value} value={value}>{label}</option>)}
      </select>
      <label htmlFor="feedback-message">问题与建议</label>
      <textarea id="feedback-message" value={message} disabled={busy} onChange={event => { setMessage(event.target.value); setSent(false); }} minLength={2} maxLength={5000} required rows={7} aria-describedby="feedback-hint" />
      <p id="feedback-hint">请说明使用的功能、问题与预期；2–5000 字。请勿填写密钥、完整客户资料或未经授权的个人信息。</p>
      {error ? <InlineAlert>{error}</InlineAlert> : null}
      {sent ? <InlineAlert tone="info">反馈已提交，感谢你的建议。内容不会自动公开。</InlineAlert> : null}
      <Button type="submit" disabled={!ready || !authenticated || busy || message.trim().length < 2}>{busy ? '正在提交…' : '提交反馈'}</Button>
    </form>
    {authenticated ? <section className={styles.history} aria-labelledby="feedback-history-heading">
      <h2 id="feedback-history-heading">我的反馈进度</h2>
      {revision !== 1 ? <p>当前后台尚不支持查看反馈进度。已收到的反馈仍按原流程处理。</p> : <>
        <p>仅显示本账号在当前企业工作区提交的最近 20 条反馈。处理状态不代表政策资格或获批结果。</p>
        <Button type="button" variant="secondary" onClick={() => void refreshHistory()} disabled={historyLoading}>{historyLoading ? '正在读取…' : '刷新进度'}</Button>
        {historyError ? <InlineAlert>{historyError}</InlineAlert> : null}
        {!historyLoading && !historyError && history.length === 0 ? <p>暂无反馈记录。</p> : null}
        <ul>{history.map(item => <li key={item.id}><div><strong>{CATEGORY[item.category] || '使用反馈'}</strong><span>{STATUS[item.status] || '状态待核对'}</span></div><p>{item.message}</p><time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString('zh-CN')}</time></li>)}</ul>
      </>}
    </section> : null}
  </section>;
}
