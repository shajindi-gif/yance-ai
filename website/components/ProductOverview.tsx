import Image from 'next/image';
import Link from 'next/link';
import styles from './ProductOverview.module.css';

type Section = { title: string; description: string; href: string; action: string };
export function ProductOverview({ label, title, description, sections }: {label:string;title:string;description:string;sections:Section[]}) {
  return <>
    <section className="page-banner"><div className="container"><span className="section-label">{label}</span><h1>{title}</h1><p>{description}</p><div className={styles.actions}><Link href="/login?register=1" className="btn btn-primary">创建企业工作区 ↗</Link><Link href="/applications" className="btn btn-outline">进入项目工作台</Link></div></div></section>
    <section className="section"><div className={`container ${styles.layout}`}><div className={styles.intro}><span className="section-label">从资料到交付</span><h2>让每一步工作，<br />都能回到依据。</h2><p>企业资料由客户提供，政策原文由服务器采集。客户本人或授权团队负责核对事实、原文与材料；客户确认不代表政府认定或获批。</p><Link href="/security">了解数据与安全边界 →</Link></div><div>{sections.map((section,index) => <article className={styles.row} key={section.title}><span>0{index+1}</span><div><h3>{section.title}</h3><p>{section.description}</p><Link href={section.href}>{section.action} ↗</Link></div></article>)}</div></div></section>
    <section className="section section-alt"><div className="container"><div className={styles.shotHeading}><h2>在真实工作界面中准备材料</h2><p>以下为隔离环境的合成数据示例；部分证据与协作能力需后台升级后启用，以工作区提示为准。</p></div><figure className={styles.shot}><Image src="/product/evidence-workspace.png" alt="合成项目资格矩阵的实际产品截图，展示事实与条款的逐项对照" width={1440} height={1000} sizes="(max-width: 700px) 100vw, 1160px" /><figcaption>合成企业与合成政策，仅用于展示操作方式，不代表客户结果或真实政策。</figcaption></figure></div></section>
  </>;
}
