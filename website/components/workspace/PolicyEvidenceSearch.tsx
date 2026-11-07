'use client';

import { useRef, useState, type FormEvent } from 'react';
import api, { type EvidenceHit } from '@/lib/api';

const dateLabel = (value: string | null) => value ? value.slice(0, 10) : '待核对';
const sourceLink = (value: string | null) => {
  try { const url = new URL(value || ''); return url.protocol === 'https:' ? url.href : undefined; }
  catch { return undefined; }
};

export default function PolicyEvidenceSearch() {
  const [query, setQuery] = useState('');
  const [level, setLevel] = useState('');
  const [hits, setHits] = useState<EvidenceHit[]>([]);
  const [pending, setPending] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState('');
  const [source, setSource] = useState<{id: string; content: string} | null>(null);
  const [sourcePending, setSourcePending] = useState('');
  const request = useRef(0);
  const sourceRequest = useRef(0);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    const attempt = ++request.current;
    ++sourceRequest.current;
    setPending(true); setError(''); setSource(null); setSourcePending(''); setHits([]);
    try {
      const response = await api.searchPolicyEvidence(query.trim(), level);
      if (attempt === request.current) { setHits(response.hits); setSearched(true); }
    } catch (failure) {
      if (attempt === request.current) setError(failure instanceof Error ? failure.message : '检索失败，请重试');
    } finally { if (attempt === request.current) setPending(false); }
  }

  async function read(hit: EvidenceHit) {
    const attempt = ++sourceRequest.current;
    setSource(null); setError(''); setSourcePending(hit.version_id);
    try {
      const version = await api.getPolicyVersion(hit.policy_id, hit.version_id);
      if (attempt === sourceRequest.current) setSource({id: hit.version_id, content: version.content});
    } catch (failure) {
      if (attempt === sourceRequest.current) setError(failure instanceof Error ? failure.message : '原文读取失败，请重试');
    } finally { if (attempt === sourceRequest.current) setSourcePending(''); }
  }

  return <section aria-labelledby="evidence-search-heading" style={{marginBlock: 24}}>
    <h2 id="evidence-search-heading">搜索政策原文</h2>
    <p>按正文和条款查找已收录资料。采集资料保留待核对状态，搜索相关性不代表企业符合资格。</p>
    <form onSubmit={search} style={{display:'flex', flexWrap:'wrap', gap:12}}>
      <input aria-label="政策原文关键词" placeholder="例如：研发费用、专精特新" required maxLength={200}
        value={query} onChange={e => setQuery(e.target.value)} style={{flex:'1 1 200px', minWidth:0}} />
      <select aria-label="原文检索层级" value={level} onChange={e => setLevel(e.target.value)}>
        <option value="">全部层级</option><option value="national">国家级</option>
        <option value="provincial">省级</option><option value="municipal">市级</option><option value="district">区级</option>
      </select>
      <button className="yc-btn-primary" disabled={pending || !query.trim()}>{pending ? '检索中…' : '检索原文'}</button>
    </form>
    {error && <p role="alert">{error}。可保留关键词重新检索，或重试读取原文。</p>}
    <p role="status">{searched && !pending ? `找到 ${hits.length} 份资料` : ''}</p>
    {searched && !pending && !error && !hits.length && <p>暂无命中资料。可减少关键词或切换层级；来源覆盖仍在持续更新。</p>}
    {hits.map(hit => <article key={hit.policy_id} style={{borderBottom:'1px solid var(--line, #ddd)', paddingBlock:20, overflowWrap:'anywhere'}}>
      <h3>{hit.title}</h3>
      <p>{hit.jurisdiction || '适用地域待核对'} · {hit.issuing_authority || '发布机构待核对'} · 原文 v{hit.version_no}</p>
      <p>发布日期 {dateLabel(hit.published_at)} · 申报截止 {dateLabel(hit.deadline)} · 政策失效 {dateLabel(hit.expires_at)}</p>
      <p>{hit.review_state === 'unreviewed' ? '采集资料 · 尚未复核' : '已发布资料 · 使用前核对当期条件'}</p>
      {!!hit.metadata_gaps.length && <p>
        {hit.metadata_gaps.includes('newer_version_unavailable')
          ? '已有更新版本尚未解析完成，当前展示较早的可读版本，请核对最新发布来源。'
          : '部分日期或地域资料不完整，需核对原文及当期申报通知。'}
      </p>}
      <blockquote style={{whiteSpace:'pre-wrap', marginInline:0}}>{hit.snippet}</blockquote>
      <p>引用位置 {hit.char_start}–{hit.char_end} · 版本 {hit.version_id}</p>
      <button type="button" onClick={() => void read(hit)} disabled={sourcePending === hit.version_id}>
        {sourcePending === hit.version_id ? '读取中…' : '查看对应版本原文'}
      </button>{' '}
      {sourceLink(hit.source_url) && <a href={sourceLink(hit.source_url)} target="_blank" rel="noopener noreferrer">打开发布来源</a>}
      {source?.id === hit.version_id && <details open><summary>对应版本完整原文</summary>
        <p style={{whiteSpace:'pre-wrap'}}>
          {source.content.slice(0, hit.char_start)}
          <mark>{source.content.slice(hit.char_start, hit.char_end)}</mark>
          {source.content.slice(hit.char_end)}
        </p></details>}
    </article>)}
  </section>;
}
