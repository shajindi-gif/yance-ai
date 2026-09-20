'use client';

import { useState } from 'react';
/* --- Downloads Data --- */
const DOWNLOADS = [
  {
    icon: '\u{1F310}',
    name: 'Chrome 浏览器插件',
    desc: '侧边栏政策查询 + 网页内容智能采集，在任何政策页面上直接使用 衍策引擎AI 能力。',
    platform: 'Chrome 90+',
    version: '未发布',
    featured: true,
  },
  {
    icon: '\u{1F9ED}',
    name: 'Safari 浏览器插件',
    desc: '为 macOS / iOS Safari 用户提供的浏览器扩展，功能与 Chrome 版一致。',
    platform: 'Safari 16+',
    version: '未发布',
    featured: false,
  },
  {
    icon: '\u{1F4BB}',
    name: 'Mac 客户端',
    desc: 'macOS 原生应用，系统托盘快捷入口 + 桌面通知，随时获取政策更新。',
    platform: 'macOS 12+',
    version: '未发布',
    featured: false,
  },
  {
    icon: '\u{1F5A5}',
    name: 'Windows 客户端',
    desc: 'Windows 桌面应用，任务栏固定入口，原生通知推送政策动态。',
    platform: 'Windows 10+',
    version: '未发布',
    featured: false,
  },
  {
    icon: '\u{1F4F1}',
    name: 'iOS App',
    desc: 'iPhone / iPad 移动应用，随时随地查看政策匹配结果和申报进度。',
    platform: 'iOS 16+',
    version: '未发布',
    featured: false,
  },
  {
    icon: '\u{1F4F2}',
    name: 'Android App',
    desc: 'Android 移动应用，支持推送通知，第一时间获取新政策发布提醒。',
    platform: 'Android 12+',
    version: '未发布',
    featured: false,
  },
];

/* --- Installation Guides --- */
const GUIDES = [
  {
    q: '当前有可下载的安装包吗？',
    a: '没有。仓库和发布流程尚未生成经过签名与验证的浏览器、桌面或移动端安装包。',
  },
  {
    q: '现在如何使用衍策引擎AI？',
    a: '请使用 Web 工作区。客户端版本、商店上架状态和系统要求将在真实发布后更新。',
  },
  {
    q: '可以提前申请客户端试用吗？',
    a: '可以通过 contact@yance.ai 提交场景需求，但这不代表客户端已有可交付版本或确定发布时间。',
  },
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
          <h1>客户端路线图</h1>
          <p>
            当前仅提供 Web 工作区。以下客户端均未发布，不提供虚假下载入口。
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
                <span className="yc-dl-badge yc-dl-badge-soon">Roadmap / 未发布</span>
                <span className="yc-dl-btn yc-dl-btn-disabled">暂无下载</span>
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

          <div className="yc-dl-requirements" style={{ padding: 24, textAlign: 'center' }}>
            客户端发布后，此处将提供经过签名的安装包与版本说明。
          </div>
        </div>
      </section>

      {/* CTA */}
      <div className="yc-cta-section">
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="yc-cta-title">需要企业定制方案？</h2>
          <p style={{ color: 'var(--text-inverse-secondary)', marginBottom: 24, maxWidth: 500, marginLeft: 'auto', marginRight: 'auto' }}>
            如需评估私有化部署或白标需求，请联系我们确认当前能力、范围与交付条件。
          </p>
          <div className="yc-cta-actions" style={{ justifyContent: 'center' }}>
            <a href="/login?register=1" className="yc-btn-primary">打开 Web 工作区</a>
            <a href="mailto:contact@yance.ai" className="yc-btn-outline-white">联系销售</a>
          </div>
        </div>
      </div>
    </>
  );
}
