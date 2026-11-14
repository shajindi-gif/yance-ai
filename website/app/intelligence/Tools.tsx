'use client';
import { useState, type FormEvent } from 'react';
import Link from 'next/link';
import api, {type EvidenceHit} from '@/lib/api';

const modes = ['采购文件','合同条款','应收账款','地区规则'] as const;
const topics = {
  '采购文件':['资质','保证金','验收','评分','截止'],
  '合同条款':['付款','违约','解除','验收','争议'],
};

export function ReviewTools(){
  const [mode,setMode]=useState<typeof modes[number]>('采购文件');
  const [drafts,setDrafts]=useState({采购文件:'',合同条款:'',地区一:'',地区二:''});
  const [reference,setReference]=useState('');
  const [due,setDue]=useState('');
  const [ledger,setLedger]=useState<{id:string;reference:string;due:string;amount:number}[]>([]);
  const [total,setTotal]=useState('');
  const [received,setReceived]=useState('');
  const inputMode=mode==='采购文件'||mode==='合同条款'?mode:null;
  const lines=inputMode?drafts[inputMode].split(/\n|(?<=。)/u).map(line=>line.trim()).filter(Boolean):[];
  const valid=(v:string)=>/^\d{1,10}(\.\d{1,2})?$/.test(v);
  const cents=(v:string)=>Math.round(Number(v)*100);
  return <div>
    <nav aria-label="交易核对工具">{modes.map(m=><button key={m} aria-pressed={mode===m} onClick={()=>setMode(m)}>{m}</button>)}</nav>
    <p>本页为本机临时核对工具。输入仅保存在当前页面，刷新后清除。</p>
    {inputMode && <><label>{inputMode}原文<textarea maxLength={30000} value={drafts[inputMode]} onChange={e=>setDrafts({...drafts,[inputMode]:e.target.value})} placeholder="粘贴要核对的条款，每段单独一行" /></label>
      {lines.length>0 && <><p>按关键词定位待复核段落。未命中时，请继续人工核对同义表述及附件。</p><dl>{topics[inputMode].map(term=><div key={term}><dt>{term}</dt><dd>{lines.filter(line=>line.includes(term)).join('\n')||'未定位到该关键词'}</dd></div>)}</dl></>}</>}
    {mode==='应收账款' && <><p>按合同逐笔核对应收余额和约定到期日。此临时清单仅供本次核对。</p>
      <label>合同或项目简称<input maxLength={100} value={reference} onChange={e=>setReference(e.target.value)} /></label>
      <label>约定到期日<input type="date" value={due} onChange={e=>setDue(e.target.value)} /></label>
      <label>应收总额（元）<input inputMode="decimal" value={total} onChange={e=>setTotal(e.target.value)} /></label>
      <label>累计实收（元）<input inputMode="decimal" value={received} onChange={e=>setReceived(e.target.value)} /></label>
      {total && received && <p role="status">{valid(total)&&valid(received)?(cents(total)>=cents(received)?'待收余额 ¥'+((cents(total)-cents(received))/100).toFixed(2):'实收超过应收，请核对金额。'):'请输入非负金额，最多两位小数、十位整数。'}</p>}
      <button disabled={!reference.trim()||!due||!valid(total)||!valid(received)||cents(received)>cents(total)} onClick={()=>{
        setLedger(rows=>[...rows,{id:crypto.randomUUID(),reference:reference.trim(),due,amount:cents(total)-cents(received)}]);
        setReference('');setDue('');setTotal('');setReceived('');
      }}>加入本次清单</button>
      {ledger.length>0 && <><p>合计待收 ¥{(ledger.reduce((sum,row)=>sum+row.amount,0)/100).toFixed(2)}</p>
        <ul>{ledger.map(row=><li key={row.id}>{row.reference} · 到期 {row.due} · 待收 ¥{(row.amount/100).toFixed(2)} <button aria-label={`移除 ${row.reference}`} onClick={()=>setLedger(rows=>rows.filter(item=>item.id!==row.id))}>移除</button></li>)}</ul></>}
    </>}
    {mode==='地区规则' && <><p>并排核对两个地区的适用范围、生效日期与条款差异。请随原文填写地区、来源链接和日期。</p><div className="rule-pair">{(['地区一','地区二'] as const).map(key=><label key={key}>{key}的规则与来源<textarea value={drafts[key]} maxLength={30000} onChange={e=>setDrafts({...drafts,[key]:e.target.value})} /></label>)}</div></>}
  </div>;
}

export function IndustrySearch(){
  const [query,setQuery]=useState('');
  const [hits,setHits]=useState<EvidenceHit[]|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  async function search(event:FormEvent){
    event.preventDefault();
    if(busy||!query.trim())return;
    setBusy(true); setError(''); setHits(null);
    try {setHits((await api.searchPolicyEvidence(query.trim())).hits);}
    catch(e){setError(e instanceof Error?e.message:'读取失败，请重试');}
    finally{setBusy(false);}
  }
  const regions=new Map<string,number>();
  for(const hit of hits||[]){const region=hit.jurisdiction||'地域待核对';regions.set(region,(regions.get(region)||0)+1);}
  return <><form onSubmit={search}><label>产业关键词<input maxLength={200} value={query} disabled={busy} onChange={e=>{setQuery(e.target.value);setHits(null);setError('');}} placeholder="例如：智能制造" /></label><button disabled={busy||!query.trim()}>{busy?'检索中…':'查看地域分布'}</button></form>
    {error && <p role="alert">{error} <Link href="/login?next=%2Fintelligence%23industry">登录后继续</Link></p>}
    {hits && <><p role="status">本次命中 {hits.length} 份。按相关性最多取20份，仅反映本次检索样本。</p><ul>{Array.from(regions,([region,n])=><li key={region}>{region} · {n} 份</li>)}</ul><ul>{hits.map(hit=><li key={hit.policy_id}>{hit.source_url?.startsWith('https://')?<a href={hit.source_url} target="_blank" rel="noreferrer">{hit.title}</a>:hit.title} · {hit.issuing_authority||'来源机构待核对'}</li>)}</ul></>}
  </>;
}
