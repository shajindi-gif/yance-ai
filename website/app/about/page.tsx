import Link from 'next/link';
import styles from '@/components/marketing/sheet.module.css';
import {Closing} from '@/components/marketing/Closing';

export const metadata = {
  title: '关于我们 | 衍策引擎AI',
  description: '上海衍策引擎人工智能科技有限公司。为中国科技企业整理可核对的政策条件，由企业团队复核。',
  openGraph: {images: [{url: '/og-brand.png', width: 1200, height: 630, alt: '衍策引擎AI'}], title: '关于衍策引擎 AI', description: '以可追溯的数据和流程支持企业政策申报准备。', url: '/about'},
};

export default function AboutPage() {
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>关于衍策引擎</p>
        <h1>把政策原文，整理成可以逐条核对的条件。</h1>
        <p className={styles.lead}>上海衍策引擎人工智能科技有限公司，服务中国科技企业、园区服务人员和投资机构分析师。页面帮助发现、核对、留痕和准备材料。认定与获批由企业和主管部门完成。</p>
        <div className={styles.actions}>
          <Link href="/login?register=1&next=%2Fcompanies" className="btn btn-primary">免费注册</Link>
          <Link href="/discover" className={styles.textLink}>查找政策</Link>
          <a className={styles.textLink} href="mailto:yanceai@163.com?subject=预约企业演示">预约企业演示</a>
        </div>
      </header>

      <section className={styles.block}>
        <p className={styles.kicker}>谁在用</p>
        <h2>先判断和自己有没有关系。</h2>
        <div className={styles.roles}>
          <article><span>科技企业</span><h2>创始人与资质负责人</h2><p>用企业事实对照政策条件，看缺口和下一步材料。</p></article>
          <article><span>园区与孵化器</span><h2>服务入驻企业</h2><p>使用同一套档案、检索和项目记录。入驻、费用和对接条件不由本页承诺。</p></article>
          <article><span>投资机构</span><h2>看组合里的政策线索</h2><p>可以按单家企业核对。组合批量扫描和城市评分尚未作为产品交付。</p></article>
        </div>
      </section>

      <section className={styles.block}>
        <p className={styles.kicker}>现在能做的事</p>
        <h2>四步都回到已有页面。</h2>
        <ol className={styles.rows}>
          <li><span className={styles.index}>01</span><div><h3><Link href="/companies">确认企业资料</Link></h3><p>地域、业务、研发和知识产权由客户填写并保留版本。</p></div></li>
          <li><span className={styles.index}>02</span><div><h3><Link href="/discover">检索已收录政策</Link></h3><p>按名称、机关、行业、层级和城市字段筛选。条数与覆盖率未在此公布。</p></div></li>
          <li><span className={styles.index}>03</span><div><h3><Link href="/opportunities">核对条件与依据</Link></h3><p>区分满足、不满足、证据不足和待复核，并查看原文引用。</p></div></li>
          <li><span className={styles.index}>04</span><div><h3><Link href="/applications">留下项目记录</Link></h3><p>补证和材料版本由客户本人或授权团队复核。</p></div></li>
        </ol>
        <p className={styles.note}><Link href="/security" className={styles.textLink}>了解安全与使用边界 →</Link></p>
      </section>

      <section className={styles.block}>
        <p className={styles.kicker}>联系</p>
        <h2>产品、合作与加入团队，都从这封邮件开始。</h2>
        <div className={styles.cols}>
          <article><h3>邮件</h3><p><a href="mailto:yanceai@163.com">yanceai@163.com</a></p></article>
          <article><h3>地址</h3><p>上海市徐汇区</p></article>
        </div>
      </section>

      <Closing
        title={<>从企业的政策需求开始。</>}
        primary={{href: '/login?register=1&next=%2Fcompanies', label: '免费注册'}}
        links={[
          {href: '/feedback?category=sales', label: '申请产品演示'},
          {href: 'mailto:yanceai@163.com', label: '联系衍策引擎'},
        ]}
      />
    </div>
  );
}
