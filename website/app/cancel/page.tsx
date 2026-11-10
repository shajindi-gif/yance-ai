import Link from 'next/link';
import pageStyles from './page.module.css';

export const metadata = {
  title: '支付已取消 | 衍策引擎AI',
  robots: { index: false },
};

export default function PaymentCancelPage() {
  return (
    <main className={pageStyles.section}>
      <section className={pageStyles.section2}>
        <p className={pageStyles.description}>支付已取消</p>
        <h1 className={pageStyles.heading}>返回订单，核对付款状态</h1>
        <p className={pageStyles.description2}>
          请在订单页核对支付渠道返回的状态与金额。仍待支付时可继续付款；如已扣款但状态未更新，请先刷新结果或联系我们协助核对。
        </p>
        <div className={pageStyles.layout}>
          <Link href="/orders" className="yc-btn-primary">返回订单</Link>
          <a href="mailto:yanceai@163.com" className={pageStyles.link}>
            联系我们
          </a>
        </div>
      </section>
    </main>
  );
}
