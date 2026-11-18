import Link from "next/link";
import type { Solution } from "@/lib/solutions";
import { SOLUTIONS } from "@/lib/solutions";
import styles from "./SolutionView.module.css";

const FLOW = [
  ["确认企业资料", "地域、业务、研发与知识产权由客户填写并确认版本。", "/companies"],
  ["检索已收录政策", "按名称、机关、行业、层级和城市字段筛选目录。", "/discover"],
  ["核对条件与依据", "区分满足、不满足、证据不足和待复核，并查看原文引用。", "/opportunities"],
  ["整理下一步", "在申报项目中保留补证和材料版本，由企业团队复核。", "/applications"],
];

export function SolutionView({ item }: { item: Solution }) {
  const others = SOLUTIONS.filter((entry) => entry.slug !== item.slug).slice(0, 3);
  return (
    <article className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>{item.group}</p>
        <h1>{item.title}</h1>
        <p className={styles.lead}>{item.summary}</p>
        <div className={styles.actions}>
          <Link href="/login?register=1&next=%2Fcompanies" className="btn btn-primary">立即匹配企业政策</Link>
          <Link href="/discover" className={styles.textLink}>查找已收录政策</Link>
          <a className={styles.textLink} href="mailto:yanceai@163.com?subject=预约企业演示">预约企业演示</a>
          <Link href="/security" className={styles.textLink}>安全与使用边界</Link>
        </div>
        <p className={styles.limit}>{item.limit}</p>
      </header>

      <section className={styles.grid} aria-label="需求与政策类别">
        <div>
          <h2>这类客户通常要解决</h2>
          <ul>{item.needs.map((need) => <li key={need}>{need}</li>)}</ul>
        </div>
        <div>
          <h2>可核对的政策类别</h2>
          <ul>{item.categories.map((category) => <li key={category}>{category}</li>)}</ul>
          <p>类别用于组织检索与核对，不表示每一类都已完整收录，也不表示本企业符合条件。</p>
        </div>
      </section>

      <section>
        <h2>衍策当前可以完成的工作</h2>
        <ol className={styles.flow}>
          {FLOW.map(([title, description, href], index) => (
            <li key={title}>
              <span>0{index + 1}</span>
              <h3><Link href={href}>{title}</Link></h3>
              <p>{description}</p>
            </li>
          ))}
        </ol>
        <ul className={styles.solves}>{item.solves.map((line) => <li key={line}>{line}</li>)}</ul>
      </section>

      <section>
        <h2>典型使用场景</h2>
        <p className={styles.note}>以下是使用方式说明，不是客户案例，也不是获批结果。</p>
        <ul className={styles.scenes}>{item.scenes.map((scene) => <li key={scene}>{scene}</li>)}</ul>
      </section>

      <aside className={styles.more}>
        <h2>继续查看</h2>
        <div>
          {others.map((entry) => (
            <Link key={entry.slug} href={`/solutions/${entry.slug}`}>{entry.title}</Link>
          ))}
          <Link href="/solutions">全部方案</Link>
          <Link href="/pricing">查看价格</Link>
        </div>
      </aside>
    </article>
  );
}
