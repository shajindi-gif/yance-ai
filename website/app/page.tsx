import Image from 'next/image';
import Link from 'next/link';
import styles from './Home.module.css';

const JOURNEY = [
  ['01', '确认企业资料', '经营情况、研发投入、知识产权。由你提供，并保留确认与版本。', '/companies'],
  ['02', '发现政策机会', '按地域和企业情况检索政策，查看来源、时效与申报窗口。', '/discover'],
  ['03', '逐条核对资格', '把政策条件与企业事实放在一起，分清满足、缺失与待复核。', '/opportunities'],
  ['04', '推进项目材料', '整理补证清单，起草材料，比较版本，留下协作意见。', '/applications'],
  ['05', '自行复核与导出', '由企业本人或授权团队核对具体版本，再按权限导出。', '/applications'],
];
const FAQ = [
  ['适合哪些企业？', '重点服务新质生产力与科技企业，同时面向制造、商贸、专业服务等各类有政策需求的企业。无论处于初创、成长还是转型阶段，都可以从企业事实开始初筛。具体可用政策取决于来源覆盖、地域、批次和实际条件，不代表所有行业与地区均已覆盖。'],
  ['政策和企业资料从哪里来？', '政策知识库和原文由服务器采集，企业资料由客户提供。采集入库不代表来源已核验或政策仍然有效，使用时应核对发布机构、原文和当期申报通知。'],
  ['谁负责复核？', '客户本人或客户授权团队负责复核。衍策辅助整理依据与材料，不提供人工业务审核，不替代主管部门认定，也不保证获批。'],
  ['可以先了解价格再使用吗？', '可以。价格页读取当前服务端产品目录，购买前可查看具体产品和权益。支付及开票是否可用取决于相应渠道配置，未接通时会提示。'],
];

export default function HomePage() {
  return <div className={styles.home}>
    <section className={styles.hero}>
      <div className={styles.heroTop}><span className={styles.eyebrow}>衍策引擎 AI / 企业政策与资源证据工作台</span><span className={styles.issue}>聚焦新质生产力与科技企业 · 服务各类企业</span></div>
      <div className={styles.heroGrid}>
        <div>
          <h1>为新质生产力企业，<br />找到有依据的<br /><em>政策与资源机会。</em></h1>
          <p className={styles.lead}>重点服务新质生产力与科技企业，也面向各类有政策需求的企业。结合企业资料与政策原文，梳理申报条件、补证任务和材料工作稿，让每一步都有来源、有状态、可复核。</p>
          <div className={styles.actions}><Link href="/discover" className="btn btn-primary">开始查找政策 <span aria-hidden="true">↗</span></Link><Link href="/dashboard" className={styles.textLink}>进入工作台 <span aria-hidden="true">→</span></Link></div>
          <p className={styles.note}>企业提供资料 · 条件逐项核对 · 客户自主复核</p>
        </div>
        <figure className={styles.heroScene}>
          <Image src="/industries/manufacturing.webp" alt="AI生成的制造企业团队协作场景示意" width={1200} height={800} sizes="(max-width: 700px) 100vw, 50vw" preload />
          <figcaption>行业场景 · AI 生成示意，非真实客户</figcaption>
          <div className={styles.sceneCaption}><span>把创新投入，转化为有据可查的准备工作</span><strong>看政策条件，也看自己的证据。</strong></div>
        </figure>
      </div>
      <div className={styles.sectors}><span>重点领域，开放服务</span><p>人工智能 / 智能制造 / 生物医药 / 集成电路 / 新能源新材料<br />也服务传统制造、商贸与专业服务等企业，按实际条件寻找机会。</p></div>
    </section>

    <section className={styles.section} id="for-business" aria-labelledby="business-heading">
      <div className={styles.sectionHead}><div><span className={styles.eyebrow}>服务对象 / 从重点到更广的企业需求</span><h2 id="business-heading">企业类型不同，<br />都从自己的事实出发。</h2></div><p>关注创新，也关注经营。先核对地域、规模、经营与研发情况，再判断政策是否适用。</p></div>
      <div className={styles.businessGrid}>{[
        ['manufacturing', '重点服务', '新质生产力企业', '人工智能、机器人、集成电路、新能源新材料等方向，先看政策原文中的产业与技术条件。'],
        ['research', '重点服务', '科技与研发型企业', '梳理研发活动、知识产权与成果转化事实，核对申报条件，缺少证明时保留待补证状态。'],
        ['business', '开放服务', '各类有政策需求的企业', '制造、商贸、专业服务等企业，无论初创、成长或转型，都可按所在地域与实际经营情况开始初筛。'],
      ].map(([scene,label,title,description]) => <article key={title}><figure className={styles.segmentImage}><Image src={`/industries/${scene}.webp`} alt={`${title}的AI生成场景示意`} width={1200} height={800} sizes="(max-width: 700px) 100vw, 33vw" /><figcaption>AI 生成 · 行业示意</figcaption></figure><span className={styles.segment}>{label}</span><h3>{title}</h3><p>{description}</p><Link href="/companies" className={styles.textLink}>从企业资料开始 →</Link></article>)}</div>
      <p className={styles.note}>面向各类企业开放使用，不等于已覆盖所有地区、行业或政策；企业类型和行业标签不直接决定申报资格。</p>
    </section>

    <section className={styles.section} id="product">
      <div className={styles.sectionHead}><div><span className={styles.eyebrow}>01 / 一个持续工作的空间</span><h2>让政策、事实和材料，<br />在同一个项目里对齐。</h2></div><p>从逐条资格核对，到工作稿版本比较和协作评论，把判断的来由和下一步工作放在手边。</p></div>
      <figure className={styles.productShot}>
        <div className={styles.shotBar}><span>衍策 / 项目工作台</span><span>隔离环境 · 合成数据示例</span></div>
        <Image src="/product/evidence-workspace.png" alt="隔离合成项目的真实资格矩阵界面，展示政策条件、企业事实、判断与原文证据" width={1440} height={1000} sizes="(max-width: 700px) 100vw, 1160px" />
        <figcaption>实际产品界面，使用合成企业和合成政策，不代表真实资助项目或客户结果。部分证据与协作能力需后台升级后启用，以工作区提示为准。</figcaption>
      </figure>
      <div className={styles.featureRows}>{[
        ['证据先行', '看见依据，也看见不足', '条件与事实并列阅读；缺少原文、事实不全或来源变化时，保留提醒。'],
        ['材料协作', '每一版修改，都有去处', '保留工作稿、版本差异、评论和摘要建议。接受建议会生成新稿，仍需客户复核。'],
        ['受控执行', '行动有状态，操作有权限', '按项目权限准备材料、处理补证和导出；任务结果来自实际执行记录。'],
      ].map(([label,title,description]) => <article key={label}><span>{label}</span><h3>{title}</h3><p>{description}</p></article>)}</div>
    </section>

    <section className={styles.workflowSection} id="workflow"><div className={styles.sectionHead}><div><span className={styles.eyebrow}>02 / 从企业资料出发</span><h2>把一次检索，<br />变成有步骤的准备工作。</h2></div><Link href="/company-match" className={styles.textLink}>了解产品流程 →</Link></div><ol className={styles.journey}>{JOURNEY.map(([number,title,description,href]) => <li key={number}><span>{number}</span><div><h3><Link href={href}>{title} <span aria-hidden="true">↗</span></Link></h3><p>{description}</p></div></li>)}</ol></section>

    <section className={styles.section}><div className={styles.sectionHead}><div><span className={styles.eyebrow}>03 / 为企业团队设计</span><h2>关注同一个机会，<br />各自找到下一步。</h2></div></div><div className={styles.audience}>{[
      ['企业负责人', '判断是否值得投入', '查看政策条件、缺口和项目进度，组织企业内部复核。'],
      ['政策申报人员', '把准备工作做扎实', '核对原文、整理材料、补充证据，保留每一版工作稿。'],
      ['财务与研发人员', '把事实和证明对齐', '补充财务、研发与知识产权资料，由企业确认来源和真实性。'],
      ['企业授权团队', '在明确权限内协作', '围绕具体项目讨论，由有权限的客户成员复核和导出。'],
    ].map(([role,title,description]) => <article key={role}><span>{role}</span><h3>{title}</h3><p>{description}</p></article>)}</div></section>

    <section className={styles.scenariosSection} id="scenarios" aria-labelledby="scenarios-heading">
      <div className={styles.sectionHead}><div><span className={styles.eyebrow}>使用场景 / 看看可以怎样开始</span><h2 id="scenarios-heading">把企业的具体问题，<br />变成下一步准备工作。</h2></div><p>以下为场景示例，不是真实客户案例、客户评价或获批结果。可用功能以工作区和后台支持情况为准。</p></div>
      <div className={styles.scenarios}>{[
        ['01 / 科技初创', '第一次找政策，不知道从哪里开始', '企业负责人先整理地域、成立时间与业务方向。', '从企业资料进入政策检索，查看来源与申报窗口，记录不清楚的条件。', '政策机会与待核对事项；没有匹配结果时，继续核对资料与目录覆盖。', '/discover', '开始查找政策'],
        ['02 / 制造成长', '准备一个项目，先看还缺哪些证明', '申报人员会同财务、研发同事准备企业事实。', '对照一项政策的条件，区分满足、不满足与证据不足，再整理材料要求。', '条件核对与补证清单；缺少财务事实或证明时，不自动认定符合。', '/opportunities', '查看政策机会'],
        ['03 / 商贸与专业服务', '已有政策线索，想确认是否适用', '企业负责人提供经营情况，并核对所在地和申报批次。', '先检索相关原文，核实适用行业、地域和期限，再决定是否推进。', '适用性与缺口记录；未收录或已过期的政策不作为当前可申报结论。', '/discover', '核对政策来源'],
      ].map(([tag,title,input,action,output,href,cta]) => <article key={tag}><span className={styles.segment}>场景示例 · {tag}</span><h3>{title}</h3><dl><dt>谁来准备</dt><dd>{input}</dd><dt>怎样使用</dt><dd>{action}</dd><dt>关注结果</dt><dd>{output}</dd></dl><Link href={href} className={styles.textLink}>{cta} →</Link></article>)}</div>
    </section>

    <section className={styles.section} id="start-with-your-task" aria-labelledby="task-heading">
      <div className={styles.sectionHead}><div><span className={styles.eyebrow}>从你的需求开始</span><h2 id="task-heading">今天，你想先解决哪件事？</h2></div><p>先看是否适合，再决定投入。企业类型不是资格结论，缺少证据的条件会保留待核对状态。</p></div>
      <div className={styles.intentGrid}>{[
        ['还没有明确政策线索', '建立企业档案，开始初筛', '准备所在地、业务方向与已有资质。确认企业事实后，再检索适用的政策来源。', '/companies', '建立企业档案'],
        ['已经准备推进一项政策', '把条件变成项目清单', '核对资格矩阵，整理补证任务与材料版本，由你或授权团队复核。', '/applications', '进入项目工作台'],
        ['已经购买，需要拿到交付', '找回订单与已购报告', '支付以服务端订单状态为准。报告按当前企业权益授权下载，异常可提交反馈。', '/orders', '查看订单与交付'],
      ].map(([tag,title,description,href,cta]) => <article key={tag}><span className={styles.segment}>{tag}</span><h3>{title}</h3><p>{description}</p><Link href={href} className={styles.textLink}>{cta} →</Link></article>)}</div>
      <div className={styles.purchasePath}><div><strong>先体验，再按需购买</strong><p>在账户现有额度内了解政策机会。需要报告时，先核对交付范围、企业和服务端报价，再决定是否购买；未开放产品不接受新单。</p></div><Link href="/pricing" className="btn btn-primary">查看交付范围与价格 →</Link></div>
    </section>

    <section className={styles.section} id="customer-feedback" aria-labelledby="feedback-heading">
      <div className={styles.feedbackPanel}><div><span className={styles.eyebrow}>用户使用与反馈</span><h2 id="feedback-heading">你的实际体验，<br />帮助我们把产品做得更好。</h2><p>暂未展示获授权的客户评价。欢迎反馈政策来源问题、使用障碍与改进建议；案例内容仅在取得单独授权后公开。</p></div><div><p>建议说明你使用的功能、遇到的问题和希望的改进。请勿提交密钥、完整客户资料或未经授权的文件。</p><Link href="/feedback" className="btn btn-primary">分享使用反馈 ↗</Link><p className={styles.note}>登录后提交 · 不自动公开 · 不影响申报判断</p></div></div>
    </section>

    <section className={styles.trustSection}><span className={styles.eyebrow}>04 / 清楚的来源与边界</span><h2>可信，始于知道<br />哪些已经确认。</h2><div><p>政策原文由服务器采集，企业事实由客户提供。来源有效性、申报窗口和缺失证据需要逐项核对。</p><p>复核由客户本人或授权团队完成。客户确认不代表政府认定或获批；园区及其他资源的可用性、费用与对接条件应另行核实。</p><Link href="/security" className={styles.textLink}>了解安全与使用边界 →</Link></div></section>

    <section className={styles.section}><div className={styles.sectionHead}><div><span className={styles.eyebrow}>常见问题</span><h2>开始前，你可能想了解。</h2></div></div><div className={styles.faq}>{FAQ.map(([question,answer]) => <details key={question}><summary>{question}<span aria-hidden="true">＋</span></summary><p>{answer}</p></details>)}</div></section>
    <section className={styles.closing}><span className={styles.eyebrow}>YANCE / 下一步</span><h2>从你的企业，<br />开始寻找合适的机会。</h2><div className={styles.actions}><Link href="/login?register=1" className="btn btn-primary">创建企业工作区 ↗</Link><Link href="/pricing" className={styles.textLink}>查看价格 →</Link></div></section>
  </div>;
}
