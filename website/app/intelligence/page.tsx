import Link from "next/link";
import { ReviewTools, IndustrySearch } from "./Tools";
import styles from "./page.module.css";

export const metadata = {
  title: "政策与核对工具｜衍策引擎 AI",
  description: "政策部分进入既有工作流。交易核对只在本页临时计算，产业分布只反映本次检索样本。",
};

export default function IntelligencePage() {
  return (
    <div className={styles.page}>
      <header>
        <h1>政策与核对工具</h1>
        <p>三块能力边界不同：政策工作流、本机临时核对、本次检索样本。</p>
        <nav aria-label="工具分区">
          <a href="#policy">政策情报</a>
          <a href="#compliance">合规与交易</a>
          <a href="#industry">产业与公共数据</a>
        </nav>
      </header>
      <section id="policy">
        <h2>政策情报</h2>
        <p>这里不单独计算匹配。请进入已有的企业档案、政策检索、资格核对和申报项目。</p>
        <nav>
          <Link href="/discover">检索政策与原文</Link>
          <Link href="/companies">确认企业资料</Link>
          <Link href="/opportunities">核对申报资格</Link>
          <Link href="/applications">查看项目与补证</Link>
        </nav>
      </section>
      <section id="compliance">
        <h2>合规与交易</h2>
        <p>以下工具在浏览器内临时计算。内容不会上传，刷新后即清除，也不进入政策匹配。</p>
        <ReviewTools />
      </section>
      <section id="industry">
        <h2>产业与公共数据</h2>
        <p>按关键词调用已有政策检索。返回最多 20 条，只说明本次样本里的地域分布，不是资格结论，也不代表该产业的全部政策。</p>
        <IndustrySearch />
      </section>
    </div>
  );
}
