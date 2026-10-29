'use client';

import { useEffect, useRef, useState } from 'react';
import api from '@/lib/api';
import styles from './SmsAuth.module.css';

export default function SmsAuth({ binding = false, onSuccess }: { binding?: boolean; onSuccess?: () => void }) {
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [company, setCompany] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [profile, setProfile] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [seconds, setSeconds] = useState(0);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const guard = useRef(false);
  useEffect(() => {
    if (seconds <= 0) return;
    const timer = setTimeout(() => setSeconds(s => Math.max(0, s - 1)), 1000);
    return () => clearTimeout(timer);
  }, [seconds]);
  const run = async (send: boolean) => {
    if (guard.current) return;
    guard.current = true; setBusy(true); setError(''); setNotice('');
    try {
      if (send) {
        await api.smsAction(binding ? 'bind/send' : 'send', { phone: phone.trim() });
        setSeconds(60); setNotice('短信服务已受理，请查收验证码，5分钟内有效。');
      } else {
        const result = await api.smsAction(binding ? 'bind' : 'verify', {
          phone: phone.trim(), code,
          ...(profile ? { owner_name: name.trim(), company_name: company.trim(), agreed_terms_version: agreed ? '2026-10-29' : undefined } : {}),
        });
        if (!binding && result.access_token) api.setToken(result.access_token);
        setDone(true); setCode(''); setNotice(binding ? '手机号绑定成功。' : '登录成功，正在进入工作台。'); onSuccess?.();
      }
    } catch (failure) {
      const message = failure instanceof Error ? failure.message : '操作失败，请重试';
      if (message.includes('首次手机登录')) setProfile(true);
      setError(message);
    } finally { guard.current = false; setBusy(false); }
  };
  return <form className={styles.form} onSubmit={event => { event.preventDefault(); void run(false); }}>
    <p className={styles.hint}>{binding ? '绑定后可用短信登录当前账号；不会合并其他账号。' : '支持中国大陆手机号。新用户验证后补充企业信息；已有邮箱账号请先邮箱登录，再到设置绑定。'}</p>
    <p className={styles.hint}>获取验证码将通过腾讯云处理本次手机号与验证码，用于身份验证。<a href="/privacy" target="_blank" rel="noopener noreferrer">查看隐私政策</a></p>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {notice && <p role="status" className={styles.notice}>{notice}</p>}
    <div className={styles.field}><label htmlFor="sms-phone">中国大陆手机号</label>
      <input id="sms-phone" type="tel" inputMode="tel" autoComplete="tel-national" value={phone} maxLength={14} pattern="(\+86)?1[3-9][0-9]{9}" placeholder="输入11位手机号" required disabled={busy || done} onChange={e => { setPhone(e.target.value); setCode(''); setProfile(false); }} />
    </div>
    <div className={styles.field}><label htmlFor="sms-code">短信验证码</label>
      <input id="sms-code" inputMode="numeric" autoComplete="one-time-code" value={code} maxLength={6} pattern="[0-9]{6}" required disabled={busy || done} onChange={e => setCode(e.target.value)} />
      <button type="button" className={styles.send} disabled={busy || done || seconds > 0 || !/^(\+86)?1[3-9][0-9]{9}$/.test(phone.trim())} onClick={() => void run(true)}>{seconds ? `${seconds}秒后可重新获取` : '获取短信验证码'}</button>
    </div>
    {profile && <>
      <div className={styles.field}><label htmlFor="sms-name">联系人姓名</label><input id="sms-name" value={name} minLength={2} maxLength={160} required disabled={busy} onChange={e => setName(e.target.value)} /></div>
      <div className={styles.field}><label htmlFor="sms-company">企业全称</label><input id="sms-company" value={company} minLength={2} maxLength={160} required disabled={busy} onChange={e => setCompany(e.target.value)} /></div>
      <label className={styles.consent}><input type="checkbox" required checked={agreed} disabled={busy} onChange={e => setAgreed(e.target.checked)} /> 我已阅读并同意<a href="/terms" target="_blank" rel="noopener noreferrer">服务条款</a>与<a href="/privacy" target="_blank" rel="noopener noreferrer">隐私政策</a></label>
    </>}
    <button type="submit" className={styles.submit} disabled={busy || done}>{busy ? '处理中…' : binding ? '验证并绑定手机号' : profile ? '完成注册并登录' : '短信验证并登录'}</button>
  </form>;
}
