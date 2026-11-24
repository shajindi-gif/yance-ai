'use client';

import { useEffect, useRef, useState, type FormEvent } from 'react';
import Link from 'next/link';
import api, {type WorkspaceHome} from '@/lib/api';
import type { Citation } from '@/lib/ask-stream';
import AnswerWithCitations from './AnswerWithCitations';
import styles from './AskWorkspace.module.css';

const presets = [
  ['同城申报窗口', '我所在城市近期有哪些可申报、有明确窗口期的政策？请只依据已收录条款原文回答。'],
  ['专精特新条件', '专精特新企业认定的硬性条件是什么？请逐条引用政策原文。'],
  ['研发加计扣除', '研发费用加计扣除的政策条件与所需证明材料有哪些？请引用原文。'],
  ['缺什么材料', '根据当前企业已有申报项目，还缺哪些证明材料？请只基于工作区记录回答。'],
];

export default function AskBox({home, selectCompany, refresh, conversationId}: {home: WorkspaceHome; selectCompany: (id: string) => void; refresh: () => void; conversationId?: string}) {
  const [question, setQuestion] = useState(''); const [mode, setMode] = useState<'fast' | 'deep'>('fast');
  const [pending, setPending] = useState(false); const [status, setStatus] = useState('');
  const [text, setText] = useState(''); const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState(''); const [uploading, setUploading] = useState(false);
  const abort = useRef<AbortController | null>(null); const inFlight = useRef(false);
  const requestId = useRef<string | null>(null);
  const draftKey = `yance-ask:${home.tenant.id}:${home.user_id}:${home.company?.id}`;
  useEffect(() => {
    setQuestion(sessionStorage.getItem(draftKey) || '');
    return () => abort.current?.abort();
  }, [draftKey]);
  useEffect(() => {
    if (!conversationId) return;
    let active = true;
    api.getConversation(conversationId).then(saved => {
      if (!active) return;
      const answer = saved.messages.findLast(item => item.role === 'assistant');
      setText(answer?.content || '回答尚未完成，请稍后重新打开对话。'); setCitations(answer?.citations || []);
      setStatus(`已保存对话 · ${{completed:"已完成",running:"进行中",failed:"未完成",cancelled:"已停止",interrupted:"执行已中断",budget_exceeded:"预算已达上限"}[saved.status] || "待核对"}`);
    }).catch(failure => { if (active) setError(failure instanceof Error ? failure.message : '对话读取失败'); });
    return () => { active = false; };
  }, [conversationId]);
  function change(value: string) { setQuestion(value); sessionStorage.setItem(draftKey, value); requestId.current = null; }
  async function send(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current || !home.company || !question.trim()) return;
    inFlight.current = true; setPending(true); setError(''); setText(''); setCitations([]); setStatus('正在检索可引用的政策版本…');
    abort.current = new AbortController();
    const timeout = setTimeout(() => abort.current?.abort(), 120000);
    requestId.current ||= crypto.randomUUID();
    try {
      let failed = false;
      await api.askWorkspace({company_id: home.company.id, question: question.trim(), mode, request_id: requestId.current}, event => {
        if (event.event === 'retrieval') setStatus(`已读取 ${event.data.sources.length} 个来源片段，正在核对依据…`);
        if (event.event === 'token') setText(previous => previous + event.data.text);
        if (event.event === 'citations') setCitations(event.data.citations);
        if (event.event === 'error') { failed = true; setError(event.data.message); setStatus('回答未完成，问题已保存'); requestId.current = null; }
        if (event.event === 'done') { setStatus('回答已保存 · 请核对条款与企业证明'); requestId.current = null; }
      }, abort.current.signal);
      if (!failed) { sessionStorage.removeItem(draftKey); setQuestion(''); }
    } catch (failure) {
      setError(failure instanceof Error && failure.name !== 'AbortError' ? failure.message : '请求已停止，问题保留。请先查看最近对话，确认结果后再重试。');
      setStatus('回答未完成');
    } finally { clearTimeout(timeout); inFlight.current = false; setPending(false); refresh(); }
  }
  async function upload(file?: File) {
    if (!file || !home.company || uploading) return;
    setUploading(true); setError('');
    try { await api.uploadDocument(home.company.id, file); setStatus('资料已入库。本次回答尚未读取上传文件；请到资料库核对解析并在项目中关联证据。'); }
    catch (failure) { setError(failure instanceof Error ? failure.message : '上传失败，请重试'); }
    finally { setUploading(false); }
  }
  const canAsk = Boolean(home.company && home.ask_enabled && home.can_ask);
  return <section className={styles.ask} aria-labelledby="ask-title">
    <div className={styles.askHead}>
      <div>
        <h2 id="ask-title">问一句，看原文</h2>
        <p>只依据已收录政策片段作答；无证据会拒答，不会编造资格或金额。</p>
      </div>
      {home.company ? <span className={styles.askBadge}>{home.company.name}</span> : null}
    </div>
    <form onSubmit={send}>
      <div className={styles.controls}>
        <label>当前企业<select disabled={pending || uploading} value={home.company?.id || ''} onChange={e => selectCompany(e.target.value)}>
          {!home.companies.length && <option value="">请先创建企业档案</option>}
          {home.companies.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select></label>
        <label>检索范围<select disabled={pending || !canAsk} value={mode} onChange={e => setMode(e.target.value as 'fast' | 'deep')}><option value="fast">快速 · 最多4个片段</option><option value="deep">深度 · 最多8个片段</option></select></label>
      </div>
      <textarea id="ask-question" className={styles.input} aria-label="向衍策提问" placeholder="例如：同城近期有哪些可申报窗口？研发加计要什么材料？" maxLength={2000} required minLength={2} value={question} disabled={pending || !canAsk} onChange={e => change(e.target.value)} />
      <div className={styles.controls}>
        <button className="yc-btn-primary" disabled={pending || uploading || !canAsk || question.trim().length < 2}>{pending ? '正在核对依据…' : '发送问题'}</button>
        {pending && <button className={styles.secondary} type="button" onClick={() => abort.current?.abort()}>停止回答</button>}
        <label>上传到资料库<input className={styles.file} type="file" disabled={uploading || pending || !home.company || !home.can_ask} onChange={e => { void upload(e.target.files?.[0]); e.target.value = ''; }} /></label>
      </div>
    </form>
    {!home.company && <p className={styles.nextHint}>还没有企业。<Link href="/companies">创建企业档案</Link>后即可提问与扫描。</p>}
    {home.company && !home.can_ask && <p className={styles.nextHint}>当前角色仅可查看，请联系企业管理员开通编辑权限。</p>}
    {home.company && !home.ask_enabled && (
      <p className={styles.nextHint}>
        问答即将可用。你现在可以继续
        <Link href="/discover">检索政策原文</Link>
        、
        <Link href={`/companies/${home.company.id}`}>补全并发布画像</Link>
        或
        <Link href="/opportunities">查看按实效排序的机会</Link>
        。
      </p>
    )}
    <div className={styles.quick} aria-label="常用问题">{presets.map(([label, prompt]) => <button key={label} disabled={pending || !home.company} type="button" onClick={() => { change(prompt); document.getElementById('ask-question')?.focus(); }}>{label}</button>)}</div>
    <p className={styles.fine}>预设只填入问题，不会自动认定资格、发布画像或提交申报。</p>
    <p role="status">{uploading ? '正在上传并解析资料…' : status}</p>
    {error && <p role="alert">{error}</p>}
    {text && <AnswerWithCitations text={text} citations={citations} />}
  </section>;
}
