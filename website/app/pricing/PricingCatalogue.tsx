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
    {error && <div role="alert" className={pageStyles.section2}><p>{error}</p><button type="button" className="btn btn-outline" disabled={loading} onClick={() => {setError('');setLoading(true);setRetry(value => value+1);}}>重新加载产品目录</button></div>}
    {!error && available.length === 0 && !loading && <p role="status">当前暂无可购买的服务。请稍后再试或联系咨询。</p>}
    <div className="grid grid-4 pricing-catalogue">
      {available.map(product => {
        const presentation = productPresentation(product);
        const featured = product.code === 'POLICY_REPORT';
        const price = product.promotional_price ?? product.price;
        return <article aria-label={presentation.name} key={product.code} className={`pricing-card${featured ? ' pricing-card-featured' : ''}`}>
          <p className={pageStyles.status}>{product.code === 'FREE_POLICY_MATCH' ? '现在可体验' : '现在可购买'}</p>
          <h2 className="pricing-name">{presentation.name}</h2>
          <p className="pricing-desc">{product.code === 'FREE_POLICY_MATCH' ? '注册后建立企业档案，在账户额度内做政策初筛。' : '需要可下载简报时，为所选企业按份结算。'}</p>
          <div className="pricing-price">{price === 0 ? <span className={pageStyles.label2}>免费</span> : <>¥{price}<span className="pricing-price-unit">{presentation.unit}</span></>}</div>
          <div className="pricing-divider" />
          <ul className="pricing-features">{presentation.features.map(feature => <li key={feature}>{feature}</li>)}</ul>
          <PricingCta product={product} featured={featured} />
          <p className="pricing-boundary">{presentation.boundary}</p>
        </article>;
      })}
    </div>
    {consultation.length > 0 && <details className="pricing-faq"><summary>更多服务 · 预约咨询</summary>
      {consultation.map(product => {
        const presentation = productPresentation(product);
        const price = product.promotional_price ?? product.price;
        return <p key={product.code}>{presentation.name} · 目录价 ¥{price}{presentation.unit} · {product.purchase_unavailable_reason || '独立交付验收后才会开放购买。'} · <a href="mailto:yanceai@163.com?subject=预约企业演示">沟通交付需求</a></p>;
      })}
    </details>}
  </>;
}
