'use client';

import {useEffect, useState} from 'react';
import api, {type ProductCatalogItem} from '@/lib/api';
import {productPresentation} from '@/lib/product-presentation';
import PricingCta from './PricingCta';
import pageStyles from './page.module.css';

export default function PricingCatalogue({initialProducts, initialError}: {initialProducts: ProductCatalogItem[]; initialError: string}) {
  const [products,setProducts] = useState(initialProducts);
  const [error,setError] = useState(initialError);
  const [retry,setRetry] = useState(0);
  const [loading,setLoading] = useState(false);
  useEffect(() => {
    let active = true;
    api.getProducts().then(data => {
      if (active) {setProducts(data);setError('');}
    }).catch(() => {if(active) setError('当前无法读取最新价格，请稍后重试。');})
      .finally(() => {if(active) setLoading(false);});
    return () => {active = false;};
  }, [retry]);
  const available = products.filter(product => product.code === 'FREE_POLICY_MATCH' || (product.purchase_available === true && product.code === 'POLICY_REPORT' && product.entitlement_type === 'report'));
  const consultation = products.filter(product => !available.includes(product));
  return <>
    {error && <div role="alert" className={pageStyles.section2}><p>{error}</p><button type="button" className="btn btn-outline" disabled={loading} onClick={() => {setLoading(true);setRetry(value => value+1);}}>重新加载产品目录</button></div>}
    {!error && available.length === 0 && <p role="status">当前暂无可购买的服务。请稍后再试或联系咨询。</p>}
    <div className="grid grid-4 pricing-catalogue">
      {available.map(product => {
        const presentation = productPresentation(product);
        const featured = product.code === 'POLICY_REPORT';
        const price = product.promotional_price ?? product.price;
        return <article aria-label={presentation.name} key={product.code} className={`pricing-card${featured ? ' pricing-card-featured' : ''}`} style={featured ? {borderColor:'var(--teal)',borderWidth:'1px'} : {}}>
          {featured && <div className={pageStyles.section4}>按需首购</div>}
          <h2 className="pricing-name">{presentation.name}</h2>
          <p className="pricing-desc">{product.code === 'FREE_POLICY_MATCH' ? '确认企业资料，开始政策机会初筛' : '按份购买 · 对应所选企业的固定报告'}</p>
          <div className="pricing-price">{price === 0 ? <span className={pageStyles.label2}>免费</span> : <>¥{price}<span className="pricing-price-unit">{presentation.unit}</span></>}</div>
          <div className="pricing-divider" />
          <ul className="pricing-features">{presentation.features.map(feature => <li key={feature}>{feature}</li>)}</ul>
          <PricingCta product={product} featured={featured} />
          <p className="pricing-boundary">{presentation.boundary}</p>
        </article>;
      })}
    </div>
    {consultation.length > 0 && <details className="pricing-faq"><summary>更多服务 · 预约咨询</summary>
      {consultation.map(product => <p key={product.code}>{productPresentation(product).name} · <a href="mailto:yanceai@163.com">沟通交付需求</a></p>)}
    </details>}
  </>;
}
