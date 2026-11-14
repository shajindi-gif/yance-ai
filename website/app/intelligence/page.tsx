import Link from 'next/link';
import { ReviewTools, IndustrySearch } from './Tools';
import styles from './page.module.css';

export const metadata = { title: '企业情报中心｜衍策引擎 AI', description: '查政策依据、核对交易材料，并从已收录的公开政策观察产业与地域分布。' };

export default function IntelligencePage() {
  return <div className={styles.page}>
    <header><h1>企业情报中心</h1><nav aria-label="业务方向"><a href="#policy">政策情报</a><a href="#compliance">合规与交易</a><a href="#industry">产业与公共数据</a></nav></header>
    <section id="policy"><small>Policy Intelligence</small><h2>政策情报与企业匹配</h2><p>检索已收录的政策原文，在项目里逐条核对企业事实、引用版本和申报期限。遇到来源变更或证据不足，由客户团队复核。</p><nav><Link href="/discover">检索政策与原文</Link><Link href="/companies">确认企业资料</Link><Link href="/opportunities">核对申报资格</Link><Link href="/applications">查看项目与补证</Link><Link href="/notifications">查看工作台通知</Link></nav></section>
    <section id="compliance"><small>Compliance Intelligence</small><h2>合规与交易审查</h2><ReviewTools /></section>
    <section id="industry"><small>Industry Intelligence</small><h2>产业与公共数据分析</h2><p>按产业关键词查看已收录政策的地域分布，回到原文核对样本来源。</p><IndustrySearch /></section>
  </div>;
}
