import Image from 'next/image';
import Link from 'next/link';
import styles from './Home.module.css';

const industries = [
  ['ai', '人工智能', '智能系统与产业数字化', 768, 468],
  ['robotics', '机器人与智能制造', '智能装备与产线改造', 700, 430],
  ['drone', '低空科技与无人系统', '无人系统研发与应用', 1440, 1800],
  ['computing', '算力与数字基础设施', '数据中心与算力设施', 547, 365],
  ['energy', '新能源与绿色转型', '清洁能源与节能改造', 1002, 751],
  ['biomed', '生物医药与研发', '实验研究与成果转化', 760, 506],
] as const;

const scenarios = [
  { title: '第一次找政策', role: '企业负责人', detail: '一家科技初创企业先确认注册地、业务方向和成立时间，再决定哪些机会值得投入。', href: '/companies', action: '确认企业资料' },
  { title: '核对一项申报条件', role: '政策申报人员', detail: '一家服务企业拿到申报通知后，逐条对照地域、期限和资质要求，记录仍需确认的条件。', href: '/opportunities', action: '核对政策机会' },
  { title: '补齐一份研发证明', role: '财务、研发及授权团队', detail: '一家制造企业在项目中整理缺少的证明，关联材料版本，交由授权同事复核后导出。', href: '/applications', action: '进入申报项目' },
];

export default function HomePage() {
  return <div className={styles.home}>
    <section className={styles.hero}>
      <div className={styles.intro}>
        <p className={styles.kicker}>企业政策与资源证据工作台</p>
        <h1>找到适合企业的政策，<br />看清每项条件的依据。</h1>
        <p>为科技、制造及各类有政策需求的企业核对申报条件，找到政策原文，列出还缺的证明。</p>
        <div className={styles.actions}>
          <Link className="btn btn-primary" href="/discover">查找政策</Link>
          <Link href="/dashboard">进入工作台 →</Link>
        </div>
      </div>
      <figure className={styles.document} id="product">
        <figcaption><strong>资格审查矩阵</strong><span>真实界面 · 合成数据示例</span></figcaption>
        <a href="/product/eligibility-matrix-20261109.png" aria-label="查看资格矩阵大图">
          <Image src="/product/eligibility-matrix-20261109.png" alt="隔离合成项目的真实资格矩阵，包含政策条件、企业事实、判断和原文证据" width={902} height={559} sizes="(max-width: 800px) 94vw, 54vw" loading="eager" fetchPriority="high" />
        </a>
      </figure>
    </section>

    <section id="workflow" className={styles.section}>
      <div id="scenarios">
        <header className={styles.heading}>
          <div><p className={styles.kicker}>使用场景示例</p><h2>从手头的申报任务开始</h2></div>
          <Link href="/company-match">了解完整流程 →</Link>
        </header>
        <div className={styles.tasks}>{scenarios.map(item => <article key={item.href}>
          <span>{item.role}</span><h3>{item.title}</h3><p>{item.detail}</p>
          <Link href={item.href}>{item.action} →</Link>
        </article>)}</div>
      </div>
    </section>

    <section id="industry-scenes" className={styles.section}>
      <header className={styles.heading} id="for-business">
        <div><p className={styles.kicker}>服务企业</p><h2>从产业方向，回到具体条件</h2></div>
        <details className={styles.scope}><summary>适合哪些企业？</summary><p>重点服务新质生产力企业、科技与研发型企业，也面向制造、商贸和专业服务等各类有政策需求的企业。适用范围以当期政策原文为准。</p></details>
      </header>
      <div className={styles.gallery}>{industries.map(([name,title,alt,width,height]) => <article key={name}>
        <Image src={`/industries/provided-20261029/${name}.webp`} alt={alt} width={width} height={height} sizes="(max-width: 600px) 45vw, 30vw" style={name === 'drone' ? {objectPosition:'50% 78%'} : undefined} />
        <h3>{title}</h3>
      </article>)}</div>
    </section>

    <section id="start-with-your-task" className={styles.section} aria-labelledby="delivery">
      <div className={styles.heading}><h2 id="delivery">价格、交付与使用帮助</h2><Link href="/login?register=1">创建企业工作区 →</Link></div>
      <div className={styles.help}>
        <div><h3>购买和交付</h3><p>购买前可查看交付范围和当前报价。已有订单可在账户内核对付款状态与交付物。</p>
          <div className={styles.actions}><Link href="/pricing">查看交付范围与价格</Link><Link href="/orders">查看订单与交付</Link></div>
        </div>
        <div><h3>依据和复核</h3><p>政策原文由服务器采集，企业资料由客户提供。申报窗口、证据缺口及材料工作稿由客户或授权团队复核。</p><Link href="/security">了解数据与安全 →</Link></div>
        <div id="customer-feedback"><h3>反馈使用问题</h3><p>发现原文失效、条件有误或操作受阻时，可登录提交反馈。反馈仅用于处理问题，公开引用须另获授权。</p><Link href="/feedback">分享使用反馈 →</Link></div>
      </div>
    </section>
  </div>;
}
