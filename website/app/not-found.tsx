import Link from 'next/link';
import pageStyles from './not-found.module.css';

export const metadata = {
  title: '页面不存在 | 衍策引擎AI',
  robots: { index: false },
};

export default function NotFound() {
  return (
    <section
      className={pageStyles.layout}
    >
      <div className={pageStyles.section}>
        <p className={pageStyles.description}>
          404
        </p>
        <h1 className={pageStyles.heading}>
          页面不存在或已移动
        </h1>
        <p className={pageStyles.description2}>
          你访问的地址可能已下线。可以回到首页继续，或查看政策知识库与产品目录。
        </p>
        <div className={pageStyles.layout2}>
          <Link
            href="/"
            className={pageStyles.link}
          >
            回到首页
          </Link>
          <Link
            href="/policies"
            className={pageStyles.link2}
          >
            政策知识库
          </Link>
        </div>
      </div>
    </section>
  );
}
