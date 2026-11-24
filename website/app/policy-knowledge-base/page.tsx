import Link from 'next/link';
import styles from '@/components/marketing/sheet.module.css';
import {Closing} from '@/components/marketing/Closing';

export const metadata = {
  title: '政策知识库 | 衍策引擎AI',
  description: '已收录政策按层级、行业和类型组织。数量、城市覆盖和更新频率尚未公开。没有原文时不猜测条件。',
};

const UNPUBLISHED = ['政策文件总数', '覆盖城市', '更新频率', '结构化覆盖率'];

export default function PolicyKnowledgeBasePage() {
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>政策知识库</p>
        <h1>先看来源，再谈这条政策和你有没有关系。</h1>
        <p className={styles.lead}>知识库保存服务器采集的政策原文和字段，供检索与资格核对引用。采集入库不代表已经核验、完整或仍然有效。数量、城市个数和更新频率须由数据库计算，当前不展示。</p>
        <div className={styles.actions}>
          <Link href="/login?register=1&next=%2Fdiscover" className="btn btn-primary">查找已收录政策</Link>
          <Link href="/security" className={styles.textLink}>安全与使用边界</Link>
        </div>
      </header>

      <section className={styles.block}>
        <p className={styles.kicker}>尚未公开</p>
        <h2>这些数字留空，直到可以计算。</h2>
        <div className={styles.roles}>
          {UNPUBLISHED.map((item) => <article key={item}><span>待统计</span><h2>{item}</h2><p>不使用占位数字，也不把样本规模写成覆盖率。</p></article>)}
        </div>
      </section>

      <section className={styles.block}>
        <p className={styles.kicker}>目录怎么分</p>
        <h2>字段用来筛选，不是资格结论。</h2>
        <div className={styles.cols}>
          <article>
            <h3>行政级别</h3>
            <ul className={styles.list}>
              <li>国家级</li>
              <li>省级与直辖市</li>
              <li>市级</li>
              <li>区级，含开发区与高新区字段</li>
            </ul>
          </article>
          <article>
            <h3>行业与类型</h3>
            <ul className={styles.list}>
              <li>人工智能、生物医药、集成电路、新能源、先进制造</li>
              <li>资质核对、资金、税收、人才、场地</li>
              <li>高企、专精特新只作为核对主题，标签不等于认定</li>
            </ul>
          </article>
        </div>
      </section>

      <section className={styles.block}>
        <p className={styles.kicker}>没有原文时</p>
        <h2>缺来源就保持证据不足。</h2>
        <div className={styles.cols}>
          <article>
            <h3>示例问题</h3>
            <p>「某项认定需要多少项知识产权？」没有对应政策原文时，结果应是证据不足，而不是猜测一个数量。</p>
          </article>
          <article>
            <h3>示例问题</h3>
            <p>「某地区有哪些企业补贴？」需要先检索有效期和适用地区匹配的来源，再显示条款与发布日期。</p>
          </article>
        </div>
        <p className={styles.note}>问答是否在当前工作区开放，以登录后的实际入口为准。已开放的回答应带来源；本页不把多轮对话或政策对比写成已经交付的能力。</p>
      </section>

      <Closing
        title={<>先检索已收录政策，<br />再核对你的企业条件。</>}
        primary={{href: '/login?register=1&next=%2Fdiscover', label: '免费注册'}}
        links={[{href: '/solutions/parks', label: '了解园区方案'}]}
      />
    </div>
  );
}
