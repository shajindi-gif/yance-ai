'use client';

import { useState } from 'react';
import Link from 'next/link';

/* --- Downloads Data --- */
const DOWNLOADS = [
  {
    icon: '\u{1F310}',
    name: 'Chrome 浏览器插件',
    desc: '侧边栏政策查询 + 网页内容智能采集，在任何政策页面上直接使用 衍策引擎AI 能力。',
    platform: 'Chrome 90+',
    version: 'v1.0.0',
    status: 'available' as const,
    featured: true,
  },
  {
    icon: '\u{1F9ED}',
    name: 'Safari 浏览器插件',
    desc: '为 macOS / iOS Safari 用户提供的浏览器扩展，功能与 Chrome 版一致。',
    platform: 'Safari 16+',
    version: 'v1.0.0',
    status: 'soon' as const,
    featured: false,
  },
  {
    icon: '\u{1F4BB}',
    name: 'Mac 客户端',
    desc: 'macOS 原生应用，系统托盘快捷入口 + 桌面通知，随时获取政策更新。',
    platform: 'macOS 12+',
    version: 'v1.0.0',
    status: 'soon' as const,
    featured: false,
  },
  {
    icon: '\u{1F5A5}',
    name: 'Windows 客户端',
    desc: 'Windows 桌面应用，任务栏固定入口，原生通知推送政策动态。',
    platform: 'Windows 10+',
    version: 'v1.0.0',
    status: 'soon' as const,
    featured: false,
  },
  {
    icon: '\u{1F4F1}',
    name: 'iOS App',
    desc: 'iPhone / iPad 移动应用，随时随地查看政策匹配结果和申报进度。',
    platform: 'iOS 16+',
    version: 'v1.0.0',
    status: 'soon' as const,
    featured: false,
  },
  {
    icon: '\u{1F4F2}',
    name: 'Android App',
    desc: 'Android 移动应用，支持推送通知，第一时间获取新政策发布提醒。',
    platform: 'Android 12+',
    version: 'v1.0.0',
    status: 'soon' as const,
    featured: false,
  },
];

/* --- Installation Guides --- */
const GUIDES = [
  {
    q: 'Chrome 插件如何安装？',
    a: `1. 下载插件压缩包并解压到本地文件夹
2. 打开 Chrome，访问 chrome://extensions/
3. 开启右上角"开发者模式"
4. 点击"加载已解压的扩展程序"，选择解压后的文件夹
5. 插件安装完成，可在任意网页上点击工具栏图标使用`,
  },
  {
    q: 'Safari 插件如何安装？',
    a: `Safari 扩展将通过 Mac App Store 分发。在 App Store 中搜索"衍策引擎AI"即可下载安装。安装后在 Safari → 设置 → 扩展中启用。`,
  },
  {
    q: 'Mac / Windows 客户端如何安装？',
    a: `Mac 用户下载 .dmg 文件，双击后将应用拖入 Applications 文件夹。Windows 用户下载 .exe 安装包，双击运行安装向导。首次启动时可能需要允许来自"未知开发者"的应用（Mac: 系统设置 → 隐私与安全性 → 仍要打开）。`,
  },
  {
    q: '移动端 App 如何安装？',
    a: `iOS 用户可从 App Store 搜索"衍策引擎AI"下载。Android 用户可从 Google Play 或官网下载 APK 文件安装（需允许"未知来源"安装）。`,
  },
  {
    q: '各平台数据是否互通？',
    a: `是的。所有平台使用同一个 衍策引擎AI 账号登录，政策收藏、企业画像、申报记录等数据实时同步。浏览器插件采集的政策内容会自动同步到您的平台账户。`,
  },
];

/* --- Requirements Table --- */
const REQUIREMENTS = [
  { platform: 'Chrome 插件', os: 'Chrome 90+ / Edge 90+', cpu: '任意', ram: '-', disk: '~10 MB' },
  { platform: 'Safari 插件', os: 'macOS 12+ / Safari 16+', cpu: 'Apple Silicon / Intel', ram: '-', disk: '~10 MB' },
  { platform: 'Mac 客户端', os: 'macOS 12+', cpu: 'Apple Silicon / Intel', ram: '4 GB', disk: '~30 MB' },
  { platform: 'Windows 客户端', os: 'Windows 10 (1809)+', cpu: 'x64 / ARM64', ram: '4 GB', disk: '~30 MB' },
  { platform: 'iOS App', os: 'iOS 16+', cpu: '-', ram: '-', disk: '~25 MB' },
  { platform: 'Android App', os: 'Android 12+', cpu: 'ARM64 / x86_64', ram: '3 GB', disk: '~25 MB' },
];

/* --- Chevron Icon --- */
function ChevronDown() {
  return (
    <svg className="yc-dl-guide-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

/* --- Page Component --- */
export default function DownloadsPage() {
  const [openGuide, setOpenGuide] = useState<number | null>(null);

  return (
    <>
      {/* Hero */}
      <div className="yc-dl-hero">
        <div className="container">
          <h1>全平台下载</h1>
          <p>
            在浏览器、桌面和移动设备上使用 衍策引擎AI，让政策研究和企业服务随时随地触手可及。
          </p>
        </div>
      </div>

      {/* Downloads Grid */}
      <section className="section">
        <div className="container">
          <div className="yc-dl-grid">
            {DOWNLOADS.map((d, i) => (
              <div key={i} className={`yc-dl-card${d.featured ? ' yc-dl-card-featured' : ''}`}>
                <div className="yc-dl-icon">{d.icon}</div>
                <h3 className="yc-dl-name">{d.name}</h3>
                <p className="yc-dl-desc">{d.desc}</p>
                <span className="yc-dl-meta">{d.platform} · {d.version}</span>
                {d.status === 'available' ? (
                  <>
                    <span className="yc-dl-badge yc-dl-badge-available">已发布</span>
                    <Link href="/chrome-extension" className="yc-dl-btn yc-dl-btn-primary">
                      查看详情
                    </Link>
                  </>
                ) : (
                  <>
                    <span className="yc-dl-badge yc-dl-badge-soon">即将上线</span>
                    <span className="yc-dl-btn yc-dl-btn-disabled">敬请期待</span>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Installation Guides */}
      <section className="section section-alt yc-dl-guide">
        <div className="container container-narrow">
          <div className="section-header">
            <span className="section-label">帮助中心</span>
            <h2 className="section-title">安装指南</h2>
            <p className="section-subtitle">
              各平台安装与使用方法，如有问题可联系 contact@yance.ai
            </p>
          </div>

          {GUIDES.map((g, i) => (
            <div
              key={i}
              className={`yc-dl-guide-item${openGuide === i ? ' open' : ''}`}
            >
              <button
                className="yc-dl-guide-question"
                onClick={() => setOpenGuide(openGuide === i ? null : i)}
              >
                {g.q}
                <ChevronDown />
              </button>
              <div className="yc-dl-guide-answer">
                <div className="yc-dl-guide-content">
                  {g.a.split('\n').map((line, j) => (
                    <p key={j}>{line}</p>
                  ))}
                </div>
              </div>
            </div>
          ))}

          {/* Requirements Table */}
          <div className="yc-dl-requirements">
            <table>
              <thead>
                <tr>
                  <th>平台</th>
                  <th>系统要求</th>
                  <th>CPU</th>
                  <th>内存</th>
                  <th>磁盘</th>
                </tr>
              </thead>
              <tbody>
                {REQUIREMENTS.map((r, i) => (
                  <tr key={i}>
                    <td><strong>{r.platform}</strong></td>
                    <td>{r.os}</td>
                    <td>{r.cpu}</td>
                    <td>{r.ram}</td>
                    <td>{r.disk}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* CTA */}
      <div className="yc-cta-section">
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="yc-cta-title">需要企业定制方案？</h2>
          <p style={{ color: 'var(--text-inverse-secondary)', marginBottom: 24, maxWidth: 500, marginLeft: 'auto', marginRight: 'auto' }}>
            我们为园区和产业服务机构提供私有化部署和白标方案，联系我们获取详细信息。
          </p>
          <div className="yc-cta-actions" style={{ justifyContent: 'center' }}>
            <Link href="/login?register=1" className="yc-btn-primary">预约诊断</Link>
            <a href="mailto:contact@yance.ai" className="yc-btn-outline-white">联系销售</a>
          </div>
        </div>
      </div>
    </>
  );
}
