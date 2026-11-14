import Link from 'next/link';
import PricingCatalogue from './PricingCatalogue';
import pageStyles from './page.module.css';
import type {ProductCatalogItem} from '@/lib/api';

export const revalidate = 300;
export const metadata = {title: '价格与交付范围｜衍策引擎 AI', description: '先免费查找政策机会，按需购买企业政策机会简报，核对来源、条件与所需证明。', openGraph: {images: [{url: '/og-brand.png', width: 1200, height: 630, alt: '衍策引擎AI'}], title: '价格与交付范围｜衍策引擎 AI', description: '免费发现政策机会，按需购买可追溯的企业政策简报。', url: '/pricing'}};

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
    <>
      <section className={["page-banner", pageStyles.section].filter(Boolean).join(' ')} >
        <div className="container">
          <span className={["badge", pageStyles.label].filter(Boolean).join(' ')} >按次付费</span>
          <h1>按次购买，需要时再买</h1>
          <p>先免费查找政策机会，需要整理判断依据与企业报告时再按份购买。</p>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <PricingCatalogue initialProducts={products} initialError={error} />
        </div>
      </section>

      {/* Value Chain */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">产品阶梯</span>
            <h2 className="section-title">按交付选择，按证据推进</h2>
          </div>
          <div className={["card", pageStyles.section5].filter(Boolean).join(' ')} >
            <p className={pageStyles.description}>
              从企业资料出发，查找政策、核对条件与证据，再整理材料。每份简报对应所选企业及固定报告版本，购买后在订单中取得交付物。
            </p>
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="section">
        <div className="container container-narrow">
          <div className="section-header">
            <span className="section-label">我们的承诺</span>
            <h2 className="section-title">AI 辅助，不伪造</h2>
          </div>
          <div className={["card", pageStyles.section6].filter(Boolean).join(' ')} >
            <p className={pageStyles.description2}>
              政策与原文由服务器采集，企业资料由客户提供。采集入库不代表已核验、完整或仍然有效；复核由客户本人或客户授权团队完成。
            </p>
            <ul className={pageStyles.section7}>
              <li>核对政策来源、有效期与当期申报截止时间</li>
              <li>缺失资料保持证据不足，客户确认不等于政府认定</li>
              <li>不承诺申报成功率，不承诺获得补贴金额</li>
              <li>付款凭证不等于正式税票；开票以实际申请流程为准</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="container container-narrow">
          <h2 className="section-title">持续协作，先把每一次交付做好</h2>
          <p>有团队协作或专项材料需求，可先沟通目标、资料与交付范围。已有订单可在工作区继续查看。</p>
          <details className="pricing-faq"><summary>购买前需要确认什么？</summary><p>先确认企业、政策或批次、输入资料、交付格式及支付渠道。信息不足时可能得到“证据不足”或“不符合”的结果，付款不代表申报资格成立。</p></details>
          <details className="pricing-faq"><summary>衍策会替企业审核和申报吗？</summary><p>业务复核由客户本人或授权团队完成。衍策辅助检索和材料准备，不提供人工业务审核、政府认定或补贴到账保证。</p></details>
          <details className="pricing-faq"><summary>如何查看已有购买记录？</summary><p>登录后在订单与账户权益中核对。已有购买不因展示名称调整而失效；遇到交付异常，请保留订单编号联系支持。</p></details>
        </div>
      </section>
      {/* CTA */}
      <section className={["cta-section", pageStyles.section8].filter(Boolean).join(' ')} >
        <div className="container">
          <h2 className="cta-title">创建工作区，开始政策机会初筛</h2>
          <p className="cta-subtitle">免费注册即可体验政策匹配，无需信用卡。</p>
          <div className="cta-actions">
            <Link href="/login?register=1" className={["btn btn-lg", pageStyles.action].join(" ")}>免费开始</Link>
            <a href="mailto:yanceai@163.com" className="btn btn-outline-white btn-lg">企业定制咨询</a>
          </div>
        </div>
      </section>
    </>
  );
}
