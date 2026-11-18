import Link from 'next/link';
import PricingCatalogue from './PricingCatalogue';
import pageStyles from './page.module.css';
import type {ProductCatalogItem} from '@/lib/api';
import {Closing} from '@/components/marketing/Closing';

export const revalidate = 300;
export const metadata = {title: '价格与交付范围｜衍策引擎 AI', description: '先免费查找政策机会。需要简报时按目录价购买，可用支付宝或微信支付，支付后在账单页申请数电票。', openGraph: {images: [{url: '/og-brand.png', width: 1200, height: 630, alt: '衍策引擎AI'}], title: '价格与交付范围｜衍策引擎 AI', description: '免费发现政策机会，按需购买可追溯的企业政策简报。', url: '/pricing'}};

export default async function PricingPage() {
  let products: ProductCatalogItem[] = [];
  let error = '';
  try {
    const target = process.env.API_PROXY_TARGET || 'https://api.yance.ai';
    const response = await fetch(`${target}/api/v1/products`, {next: {revalidate: 300}, signal: AbortSignal.timeout(8000)});
    if (!response.ok) throw new Error('catalogue unavailable');
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('invalid catalogue');
    products = data;
  } catch {
    error = '当前无法读取价格，请稍后重试。';
  }
  return (
    <div className={pageStyles.page}>
      <section className={pageStyles.hero}>
        <span className={pageStyles.eyebrow}>价格</span>
        <h1>按次购买，需要时再买</h1>
        <p>先免费查找政策，报告按现有目录按次购买。页面金额来自当前产品目录，结算以服务端订单为准。</p>
      </section>

      <section className={pageStyles.sectionBlock} aria-labelledby="pricing-path">
        <div className={pageStyles.sectionHead}>
          <div>
            <span className={pageStyles.eyebrow}>购买路径</span>
            <h2 id="pricing-path">先体验，在需要交付时再付款</h2>
          </div>
          <p>当前售卖的是一次性简报，不是席位订阅。免费额度用完之前，不要求绑定支付方式。</p>
        </div>
        <ol className={pageStyles.steps}>
          <li><span>01</span><div><h3>免费建立企业</h3><p>注册后填写企业资料，在账户额度内查看政策机会、来源和缺失材料。</p></div></li>
          <li><span>02</span><div><h3>核对到需要报告</h3><p>机会列表可以继续查看。需要把所选企业的判断整理成可下载简报时，再进入结算。</p></div></li>
          <li><span>03</span><div><h3>按份支付并申请发票</h3><p>可选支付宝或微信支付。支付确认后，在账单页提交抬头和税号，申请数电票。</p></div></li>
        </ol>
        <div className={pageStyles.facts}>
          <div>
            <h3>现在可以结算</h3>
            <p>免费体验，以及企业政策机会简报。简报价格显示在下方目录，当前为按份计价。</p>
          </div>
          <div>
            <h3>目录里还有两档</h3>
            <p>单项核对和材料工作稿保留目录价，独立交付验收后才会开放购买。展开「更多服务 · 预约咨询」可看到金额。</p>
          </div>
          <div>
            <h3>支付与发票</h3>
            <p>支付宝、微信支付。付款回执不是税票；已支付订单在<Link href="/billing">账单</Link>申请开票，开具后可下载发票文件。</p>
          </div>
        </div>
      </section>

      <section className={pageStyles.sectionBlock} aria-labelledby="catalogue-heading">
        <div className={pageStyles.sectionHead}>
          <div>
            <span className={pageStyles.eyebrow}>产品目录</span>
            <h2 id="catalogue-heading">按交付选择</h2>
          </div>
          <p>从企业资料出发，查找政策、核对条件与证据，再整理材料。每份简报对应所选企业及固定报告版本。</p>
        </div>
        <PricingCatalogue initialProducts={products} initialError={error} />
      </section>

      <section className={pageStyles.sectionBlock}>
        <div className={pageStyles.sectionHead}>
          <div>
            <span className={pageStyles.eyebrow}>边界</span>
            <h2>购买的是整理，不是认定</h2>
          </div>
        </div>
        <ul className={pageStyles.bounds}>
          <li>核对政策来源、有效期与当期申报截止时间</li>
          <li>缺失资料保持证据不足，客户确认不等于政府认定</li>
          <li>不承诺申报成功率，不承诺获得补贴金额</li>
          <li>付款凭证不等于正式税票；开票以账单页的申请流程为准</li>
        </ul>
        <div className={pageStyles.faq}>
          <details className="pricing-faq"><summary>购买前需要确认什么？</summary><p>先确认企业、政策或批次、输入资料、交付格式及支付渠道。信息不足时可能得到“证据不足”或“不符合”的结果，付款不代表申报资格成立。</p></details>
          <details className="pricing-faq"><summary>衍策会替企业审核和申报吗？</summary><p>业务复核由客户本人或授权团队完成。衍策辅助检索和材料准备，不提供人工业务审核、政府认定或补贴到账保证。</p></details>
          <details className="pricing-faq"><summary>如何查看已有购买记录？</summary><p>登录后在订单与账户权益中核对。已有购买不因展示名称调整而失效；遇到交付异常，请保留订单编号联系支持。</p></details>
          <details className="pricing-faq"><summary>有哪些付款和开票方式？</summary><p>结算页提供支付宝和微信支付。订单支付成功后，在账单页填写发票抬头和纳税人识别号申请数电票。企业专项协作通过邮件约定范围，不在此页生成无法结算的套餐价。</p></details>
        </div>
      </section>

      <Closing
        title={<>先免费核对机会，<br />需要报告时再购买。</>}
        primary={{href: '/login?register=1&next=%2Fcompanies', label: '免费开始'}}
        links={[
          {href: '/billing', label: '查看账单与发票'},
          {href: 'mailto:yanceai@163.com?subject=预约企业演示', label: '预约企业演示'},
        ]}
      />
    </div>
  );
}
