'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { InlineAlert } from '@/components/ui/InlineAlert';
import styles from './page.module.css';

export default function FeedbackPage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [category, setCategory] = useState('product');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [sent, setSent] = useState(false);
  const pending = useRef(false);
  useEffect(() => { setAuthenticated(api.isAuthenticated()); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current || !api.isAuthenticated() || message.trim().length < 2) return;
    pending.current = true; setBusy(true); setError(''); setSent(false);
    try {
      await api.submitFeedback(category, message.trim());
      setMessage(''); setSent(true);
    } catch {
      setError('反馈未确认提交成功，内容已保留。请检查登录状态后重试；若网络中断，请先核对，避免重复提交。');
    } finally { pending.current = false; setBusy(false); }
  }

  return <section className={styles.page}>
    <Link href="/#customer-feedback">← 返回使用场景与反馈</Link>
    <h1>分享使用反馈</h1>
    <p>告诉我们使用中遇到的问题与改进建议。反馈用于产品改进，不自动成为公开案例或客户评价；公开前会另行征得授权。</p>
    {!authenticated ? <InlineAlert tone="info">请先<Link href="/login">登录账号</Link>，然后返回此页提交反馈。</InlineAlert> : null}
    <form onSubmit={submit} className={styles.form}>
      <label htmlFor="feedback-category">反馈类型</label>
      <select id="feedback-category" value={category} disabled={busy} onChange={event => { setCategory(event.target.value); setSent(false); }}>
        <option value="product">功能与体验建议</option><option value="data">数据来源问题</option><option value="policy">政策内容问题</option><option value="billing">订单与计费问题</option><option value="support">其他使用问题</option>
      </select>
      <label htmlFor="feedback-message">问题与建议</label>
      <textarea id="feedback-message" value={message} disabled={busy} onChange={event => { setMessage(event.target.value); setSent(false); }} minLength={2} maxLength={5000} required rows={7} aria-describedby="feedback-hint" />
      <p id="feedback-hint">请说明使用的功能、问题与预期；2–5000 字。请勿填写密钥、完整客户资料或未经授权的个人信息。</p>
      {error ? <InlineAlert>{error}</InlineAlert> : null}
      {sent ? <InlineAlert tone="info">反馈已提交，感谢你的建议。内容不会自动公开。</InlineAlert> : null}
      <Button type="submit" disabled={!authenticated || busy || message.trim().length < 2}>{busy ? '正在提交…' : '提交反馈'}</Button>
    </form>
  </section>;
}
