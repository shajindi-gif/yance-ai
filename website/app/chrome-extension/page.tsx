'use client';

import { useState } from 'react';
import Link from 'next/link';
import styles from '@/components/marketing/sheet.module.css';
import {Closing} from '@/components/marketing/Closing';

const SPECS = [
  ['产品状态', '未发布'],
  ['Manifest 目标', 'Manifest V3，待实现'],
  ['权限范围', '发布前按最小权限重新评审'],
  ['数据处理', '发布前完成隐私与安全验收'],
  ['兼容性', '尚未建立真实兼容性测试'],
  ['安装包', '尚无可用构件'],
];

export default function ChromeExtensionPage() {
  const [tab, setTab] = useState<'status' | 'install'>('status');
  return (
    <div className={styles.page}>
      <header className={styles.hero}>
        <p className={styles.kicker}>浏览器扩展 · 未发布</p>
        <h1>政策核对请先在 Web 工作区完成。</h1>
        <p className={styles.lead}>浏览器侧边栏采集仍是设想。当前没有可安装扩展，也没有经过验证的采集效率。设想中的字段包括政策名称、发文机关、产业、资助、截止日期和材料要求，这些都还不能在网页里自动提取。</p>
        <div className={styles.actions}>
          <Link href="/login?register=1&next=%2Fcompanies" className="btn btn-primary">打开 Web 工作区</Link>
          <Link href="/downloads" className={styles.textLink}>查看发布状态</Link>
        </div>
      </header>
      <section className={styles.block}>
        <div className={styles.tabs}>
          <button type="button" aria-pressed={tab === 'status'} onClick={() => setTab('status')}>当前状态</button>
          <button type="button" aria-pressed={tab === 'install'} onClick={() => setTab('install')}>为何还不能安装</button>
        </div>
        {tab === 'status' ? (
          <table className={styles.table}><tbody>{SPECS.map(([label, value]) => <tr key={label}><th>{label}</th><td>{value}</td></tr>)}</tbody></table>
        ) : (
          <ol className={styles.rows}>
            <li><span className={styles.index}>01</span><div><h3>没有安装包</h3><p>进度以<Link href="/downloads">发布状态页</Link>为准。</p></div></li>
            <li><span className={styles.index}>02</span><div><h3>先完成最小权限</h3><p>来源校验、登录和上传前确认都要在实现里存在。</p></div></li>
            <li><span className={styles.index}>03</span><div><h3>再做安全验收</h3><p>权限、隐私披露和兼容性测试完成之前，不提供安装说明。</p></div></li>
          </ol>
        )}
      </section>
      <Closing
        title={<>浏览器扩展尚未发布，<br />请先使用 Web 工作区。</>}
        primary={{href: '/login?register=1&next=%2Fcompanies', label: '打开 Web 工作区'}}
        links={[{href: '/downloads', label: '查看发布状态'}]}
      />
    </div>
  );
}
