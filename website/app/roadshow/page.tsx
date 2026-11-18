import Link from 'next/link';
import styles from '@/components/marketing/sheet.module.css';
import {Closing} from '@/components/marketing/Closing';

export const metadata = {
  title: '园区试点说明 | 衍策引擎 AI',
  description: '园区试点是可讨论的验证模板。没有已签约客户、公开路演日程或可引用的试点指标。',
};

export default function RoadshowPage() {
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>园区与合作</p>
        <h1>试点从现有工作台开始，不另开一套产品。</h1>
        <p className={styles.lead}>以下是可讨论的验证步骤，不代表已签约园区、政府合作或已开放活动。范围、数据位置、周期和价格都要写入双方确认的协议。</p>
        <div className={styles.actions}>
          <Link href="/solutions/parks" className="btn btn-primary">查看园区方案</Link>
          <a className={styles.textLink} href="mailto:yanceai@163.com?subject=园区与合作">联系合作</a>
          <Link href="/security" className={styles.textLink}>安全与使用边界</Link>
        </div>
      </header>

      <section className={styles.block}>
        <p className={styles.kicker}>验证时先确认</p>
        <h2>指标留到真实试点再测量。</h2>
        <div className={styles.roles}>
          {[
            ['待测量', '覆盖企业数', '以数据库中的真实企业记录为准。'],
            ['待评测', '匹配准确率', '须来自冻结评测集，不在本页预写百分比。'],
            ['待测量', '响应与效率', '对照试点基线记录时延和步骤变化。'],
          ].map(([status, title, text]) => (
            <article key={title}><span>{status}</span><h2>{title}</h2><p>{text}</p></article>
          ))}
        </div>
      </section>

      <section className={styles.block}>
        <p className={styles.kicker}>可以怎么合作</p>
        <h2>三种讨论方式，都先确认已上线范围。</h2>
        <div className={styles.cols}>
          <article><h3>园区试点</h3><p>用现有企业档案、政策检索、资格核对和项目记录服务入驻企业。入驻推荐和费用另行核实。</p></article>
          <article><h3>服务机构</h3><p>咨询机构和行业协会可以了解同一套工作流。本页不提供渠道分成或代理承诺。</p></article>
          <article><h3>系统对接</h3><p>如需把检索或核对嵌入现有系统，先用邮件确认接口范围。页面不宣称已有可交付 SDK。</p></article>
        </div>
      </section>

      <section className={styles.block}>
        <p className={styles.kicker}>场景示例</p>
        <h2>这些城市不是路演日程。</h2>
        <p>上海、杭州、深圳、北京只表示可以讨论的产业场景。目前没有公开活动日期。</p>
      </section>

      <Closing
        title={<>园区与合作，<br />使用同一套已上线工作台。</>}
        primary={{href: '/solutions/parks', label: '查看园区方案'}}
        links={[{href: 'mailto:yanceai@163.com?subject=园区与合作', label: '联系合作'}]}
      />
    </div>
  );
}
