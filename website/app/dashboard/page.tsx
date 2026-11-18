'use client';

import Link from 'next/link';
import {useRouter} from 'next/navigation';
import {useCallback, useEffect, useState} from 'react';
import AppShell from '@/components/workspace/AppShell';
import AskBox from '@/components/workspace/AskBox';
import {PageHeader} from '@/components/ui/PageHeader';
import {LoadingState} from '@/components/ui/LoadingState';
import {InlineAlert} from '@/components/ui/InlineAlert';
import api, {type WorkspaceHome} from '@/lib/api';
import styles from '@/components/workspace/AskWorkspace.module.css';

const states: Record<string, string> = {completed:'已完成', running:'进行中', failed:'未完成', cancelled:'已停止', draft:'准备中', budget_exceeded:'预算已达上限', interrupted:'执行已中断'};
export default function DashboardPage() {
  const router = useRouter(); const [home, setHome] = useState<WorkspaceHome | null>(null);
  const [companyId, setCompanyId] = useState(''); const [error, setError] = useState('');
  const [revision, setRevision] = useState(0); const [conversation, setConversation] = useState<string>();
  const refresh = useCallback(() => setRevision(n => n + 1), []);
  useEffect(() => {
    if (!api.isAuthenticated()) { router.replace(`/login?next=${encodeURIComponent('/dashboard')}`); return; }
    const controller = new AbortController();
    api.getWorkspaceHome(companyId || undefined, controller.signal).then(data => { setHome(data); setError(''); })
      .catch(failure => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : '工作台读取失败'); });
    return () => controller.abort();
  }, [router, companyId, revision]);
  return <AppShell workspaceName={home?.tenant.name}>
    <PageHeader title="从一个问题开始" description={home?.company ? `${home.company.name} · 查条件、看原文、补证明` : '把政策原文、企业事实和下一步工作放在一起。'} />
    {error && <InlineAlert>{error} <button type="button" onClick={refresh}>重新加载</button></InlineAlert>}
    {!home && !error && <LoadingState label="正在读取企业与项目" />}
    {home && <>
      <AskBox key={home.company?.id || 'empty'} home={home} refresh={refresh} conversationId={conversation} selectCompany={id => { setCompanyId(id); setConversation(undefined); }} />
      <div className={styles.cards}>
        <Link className={styles.card} href="/opportunities">已记录符合<strong>{home.cards.eligible_count}</strong><small>仅计当前画像及有效政策版本的明确符合记录；不代表政府认定。</small><small>{home.cards.highest_amount_wan === null ? '资助上限待核实' : `条款最高上限 ${home.cards.highest_amount_wan.toLocaleString('zh-CN')} 万元，非预计到账`}</small></Link>
        <Link className={styles.card} href="/opportunities">30天内截止<strong>{home.cards.deadline_count}</strong><small>{home.cards.nearest_deadline ? `最近 ${new Date(home.cards.nearest_deadline).toLocaleDateString('zh-CN')}` : '暂无已核实的当期截止日期'}</small></Link>
        <Link className={styles.card} href="/applications">待补证明<strong>{home.cards.missing_evidence_count}</strong><small>当前企业未完成项目中，缺失或收集中的材料要求。</small></Link>
      </div>
      <div className={styles.grid}>
        <section className={styles.list}><h2>最近项目</h2>{!home.projects.length && <p>还没有项目。先查看政策原文并核对条件。</p>}{home.projects.map(item => <Link key={item.id} className={styles.row} href={`/applications/${item.id}`}><span>{item.title}</span><small>{states[item.status] || '查看状态'}</small></Link>)}<Link href="/applications">查看全部项目</Link></section>
        <section className={styles.list}><h2>最近对话</h2>{!home.conversations.length && <p>还没有提问记录。对话仅你本人可见。</p>}{home.conversations.map(item => <button type="button" key={item.id} className={styles.row} onClick={() => setConversation(item.id)}><span>{item.title}</span><small>{states[item.status] || '查看状态'}</small></button>)}</section>
      </div>
      <p><Link href={home.next_action.href}>{home.next_action.title} →</Link></p>
    </>}
  </AppShell>;
}
