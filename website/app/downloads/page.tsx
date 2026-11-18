'use client';

import { useState } from 'react';
import styles from '@/components/marketing/sheet.module.css';
import {Closing} from '@/components/marketing/Closing';

const DOWNLOADS = [
  ['Chrome 浏览器插件', 'Chrome 90+'],
  ['Safari 浏览器插件', 'Safari 16+'],
  ['Mac 客户端', 'macOS 12+'],
  ['Windows 客户端', 'Windows 10+'],
  ['iOS App', 'iOS 16+'],
  ['Android App', 'Android 12+'],
];

const GUIDES = [
  ['当前有可下载的安装包吗？', '没有。仓库和发布流程尚未生成经过签名与验证的浏览器、桌面或移动端安装包。'],
  ['现在如何使用衍策引擎AI？', '请使用 Web 工作区。客户端版本、商店上架状态和系统要求将在真实发布后更新。'],
  ['可以提前申请客户端试用吗？', '可以通过 yanceai@163.com 提交场景需求。这不代表客户端已有可交付版本或确定发布时间。'],
];

export default function DownloadsPage() {
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>客户端</p>
        <h1>现在只有 Web 工作区。</h1>
        <p className={styles.lead}>下列浏览器、桌面和移动端都未发布。页面不提供下载按钮，也不预告上线日期。</p>
      </header>
      <section className={styles.block}>
        <table className={styles.table}>
          <tbody>
            {DOWNLOADS.map(([name, platform]) => (
              <tr key={name}><th>{name}</th><td>{platform} · 未发布 · 暂无安装包</td></tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className={styles.block}>
        <p className={styles.kicker}>发布前</p>
        <h2>安装说明等签名包出现后再写。</h2>
        <div className={styles.faq}>
          {GUIDES.map(([question, answer], index) => (
            <div key={question}>
              <button type="button" aria-expanded={open === index} onClick={() => setOpen(open === index ? null : index)}>{question}<span aria-hidden="true">{open === index ? '－' : '＋'}</span></button>
              {open === index && <p>{answer}</p>}
            </div>
          ))}
        </div>
      </section>
      <Closing
        title={<>需要评估部署范围时，<br />先确认现有能力。</>}
        primary={{href: '/login?register=1&next=%2Fcompanies', label: '打开 Web 工作区'}}
        links={[{href: 'mailto:yanceai@163.com?subject=部署与定制', label: '联系我们'}]}
      />
    </div>
  );
}
