import type { Metadata } from "next";
import Link from "next/link";
import { SOLUTIONS } from "@/lib/solutions";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "行业解决方案 | 衍策引擎 AI",
  description: "按科技产业、企业成长阶段和投资园区机构，进入同一套政策检索与资格核对工作流。行业标签不等于申报资格。",
};

export default function SolutionsPage() {
  const groups = ["产业方向", "企业成长", "机构服务"] as const;
  return (
    <main className={styles.page}>
      <header>
        <p className={styles.kicker}>解决方案</p>
        <h1>按你的产业与角色，进入同一套核对流程。</h1>
        <p>每个方案都回到企业资料、政策检索、资格依据和申报项目。这里不承诺补贴、认定或成功率。</p>
      </header>
      {groups.map((group) => (
        <section key={group} aria-labelledby={group}>
          <h2 id={group}>{group}</h2>
          <div className={styles.grid}>
            {SOLUTIONS.filter((item) => item.group === group).map((item) => (
              <Link key={item.slug} href={`/solutions/${item.slug}`}>
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
              </Link>
            ))}
          </div>
        </section>
      ))}
      <p className={styles.note}>政策条数与城市覆盖率未在这些页面展示。数量级说明见政策知识库。</p>
      <Link href="/policy-knowledge-base">查看数据说明</Link>
    </main>
  );
}
