'use client';

import { useEffect, useRef, useState } from 'react';
import api from '@/lib/api';
import {findQuoteSpan, type Citation} from '@/lib/ask-stream';
import { EvidencePassage } from './PolicyEvidenceSearch';
import styles from './AskWorkspace.module.css';

function SourceDialog({citation, close}: {citation: Citation; close: () => void}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [content, setContent] = useState(''); const [error, setError] = useState('');
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    let active = true;
    const node = dialog.current;
    node?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    api.getPolicyVersion(citation.policy_id, citation.version_id).then(version => { if (active) setContent(version.content); })
      .catch(() => { if (active) setError('原文读取失败。请关闭后重试，或前往政策原文检索。'); });
    return () => { active = false; node?.close(); document.body.style.overflow = overflow; previous?.focus(); };
  }, [citation]);
  const span = findQuoteSpan(content, citation.policy_quote, citation.char_start);
  let url: string | undefined;
  try { const parsed = new URL(citation.source_url || ''); if (parsed.protocol === 'https:') url = parsed.href; } catch { /* untrusted sources never become executable links */ }
  return <dialog ref={dialog} className={styles.dialog} aria-labelledby="ask-source-title" onClose={() => { if (!dialog.current?.open) close(); }}>
    <button type="button" className={styles.secondary} onClick={close} autoFocus>关闭原文</button>
    <h2 id="ask-source-title">{citation.title}</h2>
    <p>固定版本原文 · {citation.version_id}</p>
    <p>{citation.review_state === 'unreviewed'
      ? '采集资料 · 尚未复核。摘录不是资格认定。'
      : citation.review_state === 'dates_unverified'
        ? '已收录原文 · 日期未核实。摘录不是资格认定。'
        : '原文存在不等于企业符合资格。'}</p>
    {url && <p><a href={url} target="_blank" rel="noopener noreferrer">打开发布来源</a></p>}
    {error ? <p role="alert">{error}</p> : !content ? <p role="status">正在读取原文…</p> : <>
      <p>引文位置以保存的政策版本为准。</p>
      {!span ? <p role="alert">引文无法在当前版本逐字定位，请返回项目核对。</p> : null}
      <EvidencePassage content={content} start={span?.start ?? -1} end={span?.end ?? 0} />
    </>}
  </dialog>;
}

export default function AnswerWithCitations({text, citations}: {text: string; citations: Citation[]}) {
  const [selected, setSelected] = useState<Citation | null>(null);
  return <section className={styles.answer} aria-label="回答与政策依据">
    <h3>回答与依据</h3>
    <p>{text.split(/(\[\d+\])/g).map((part, i) => {
      const index = /^\[(\d+)\]$/.exec(part);
      const citation = index && citations.find(item => item.index === Number(index[1]));
      return citation ? <button type="button" key={i} className={styles.citation} aria-label={`查看引用 ${citation.index}：${citation.title}`} onClick={() => setSelected(citation)}>{part}</button> : <span key={i}>{part}</span>;
    })}</p>
    {selected && <SourceDialog key={selected.index} citation={selected} close={() => setSelected(null)} />}
  </section>;
}
