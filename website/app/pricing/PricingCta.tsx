'use client';

import {useRouter} from 'next/navigation';
import api, {type ProductCatalogItem} from '@/lib/api';

export default function PricingCta({product, featured}: {product: ProductCatalogItem; featured: boolean}) {
  const router = useRouter();
  const choose = () => {
    const destination = product.code === 'FREE_POLICY_MATCH' ? '/dashboard' : `/checkout?product=${encodeURIComponent(product.code)}`;
    router.push(api.isAuthenticated() ? destination : `/login?register=1&next=${encodeURIComponent(destination)}`);
  };
  return <button onClick={choose} className={`btn ${featured ? '' : 'btn-outline'}`}
    style={featured ? {background:'var(--teal)',color:'var(--surface)',borderColor:'var(--teal)',borderRadius:'12px',width:'100%',cursor:'pointer'} : {borderRadius:'12px',width:'100%',cursor:'pointer'}}>
    {product.code === 'FREE_POLICY_MATCH' ? '免费开始' : '选择企业并购买'}
  </button>;
}
