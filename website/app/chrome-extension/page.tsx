'use client';

import { useState } from 'react';
import Link from 'next/link';

/* --- Extraction Fields --- */
const EXTRACTION_FIELDS = [
  { icon: '\u{1F4CB}', name: '政策名称', key: 'policy_name', desc: '自动识别政策文件标题和正式名称' },
  { icon: '\u{1F3DB}', name: '发文机关', key: 'issuing_authority', desc: '提取发布政策的政府部门或机构' },
  { icon: '\u{1F3ED}', name: '目标产业', key: 'target_industry', desc: '识别政策适用的行业和产业方向' },
  { icon: '\u{1F4B0}', name: '补贴金额', key: 'subsidy_amount', desc: '提取资金支持额度和比例信息' },
  { icon: '\u{1F4C5}', name: '申报截止', key: 'application_deadline', desc: '捕获申报时间节点和有效期' },
  { icon: '\u{1F4C4}', name: '材料要求', key: 'material_requirements', desc: '汇总申报所需材料清单' },
];

/* --- Workflow Steps --- */
const WORKFLOW = [
  { step: 1, title: '浏览政策页面', desc: '在任意政府网站或政策发布平台上浏览政策文件' },
  { step: 2, title: '智能识别采集', desc: '插件自动识别页面中的政策关键信息并高亮标注' },
  { step: 3, title: '一键保存到平台', desc: '确认采集结果，一键同步到 衍策引擎AI 企业账户' },
  { step: 4, title: '匹配与申报', desc: '在平台中自动匹配企业画像，生成申报建议' },
];

/* --- Tech Specs --- */
const TECH_SPECS = [
  { label: 'Manifest 版本', value: 'Manifest V3' },
  { label: '权限', value: 'activeTab, sidePanel, storage, clipboardWrite' },
  { label: '数据处理', value: '本地处理，不上传至第三方' },
  { label: '兼容浏览器', value: 'Chrome 90+, Edge 90+, Arc, Brave' },
  { label: '框架', value: 'React 18 + TypeScript' },
  { label: '包大小', value: '侧边栏 ~295KB, 内容脚本 ~14KB' },
];

/* --- Side Panel Mockup Component --- */
function SidePanelMockup() {
  return (
    <div className="yc-ext-mockup-browser">
      <div className="yc-ext-mockup-toolbar">
        <div className="yc-ext-mockup-dots">
          <span /><span /><span />
        </div>
        <div className="yc-ext-mockup-url">
          https://www.shstc.gov.cn/policy/2026-ai-special
        </div>
      </div>
      <div className="yc-ext-mockup-body">
        {/* Main content area */}
        <div className="yc-ext-mockup-content">
          <div className="yc-ext-mockup-page-title">
            上海市科学技术委员会关于 2026 年度人工智能专项资金项目申报的通知
          </div>
          <div className="yc-ext-mockup-page-text">
            <p>各有关单位：</p>
            <p>根据《上海市促进人工智能产业发展若干规定》，现启动 2026 年度人工智能专项资金项目申报工作。</p>
            <p className="yc-ext-highlighted">
              <span className="yc-ext-highlight-label">补贴金额</span>
              单个项目资助金额不超过 500 万元，资助比例不超过项目总投资的 30%。
            </p>
            <p className="yc-ext-highlighted">
              <span className="yc-ext-highlight-label">申报截止</span>
              项目申报截止日期为 2026 年 9 月 30 日。
            </p>
            <p>申报单位应为在本市注册的独立法人单位，具有良好信用记录...</p>
          </div>
        </div>
        {/* Side panel */}
        <div className="yc-ext-mockup-sidebar">
          <div className="yc-ext-sidebar-header">
            <img src="/logo.png" alt="" width={20} height={20} style={{ borderRadius: '4px', verticalAlign: 'middle', marginRight: '6px' }} />
            <span className="yc-ext-sidebar-logo">衍策引擎AI</span>
            <span className="yc-ext-sidebar-badge">6 项已识别</span>
          </div>
          <div className="yc-ext-sidebar-section">
            <div className="yc-ext-sidebar-label">提取结果</div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">政策名称</span>
              <span className="yc-ext-field-val">2026 年度人工智能专项资金项目申报</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">发文机关</span>
              <span className="yc-ext-field-val">上海市科学技术委员会</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">目标产业</span>
              <span className="yc-ext-field-val">人工智能</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">补贴金额</span>
              <span className="yc-ext-field-val yc-ext-val-highlight">≤ 500 万元 (30%)</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">申报截止</span>
              <span className="yc-ext-field-val yc-ext-val-warning">2026-09-30</span>
            </div>
            <div className="yc-ext-sidebar-field">
              <span className="yc-ext-field-key">材料要求</span>
              <span className="yc-ext-field-val">项目申报书、财务审计报告、知识产权证明...</span>
            </div>
          </div>
          <button className="yc-ext-sidebar-btn">保存到 衍策引擎AI</button>
        </div>
      </div>
    </div>
  );
}

/* --- Page Component --- */
export default function ChromeExtensionPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'install'>('overview');

  return (
    <>
      {/* Hero */}
      <div className="yc-ext-hero">
        <div className="container">
          <span className="yc-ext-hero-badge">Chrome Extension · Manifest V3</span>
          <h1 className="yc-ext-hero-title">衍策引擎AI 政策助手</h1>
          <p className="yc-ext-hero-subtitle">
            在任意政策页面上直接使用 衍策引擎AI 的 AI 政策匹配与企业画像能力。侧边栏实时查询，网页内容智能采集，让政策研究效率提升 10 倍。
          </p>
          <div className="yc-ext-hero-ctas">
            <Link href="/downloads" className="yc-btn-primary">
              前往下载
            </Link>
            <a href="#features" className="yc-btn-outline-white">
              了解功能
            </a>
          </div>
        </div>
      </div>

      {/* Feature Mockup */}
      <section className="section" id="features">
        <div className="container">
          <div className="section-header">
            <span className="section-label">核心功能</span>
            <h2 className="section-title">网页内容智能采集</h2>
            <p className="section-subtitle">
              浏览政策文件时，插件自动识别并提取关键信息，高亮标注在页面上，一键保存到您的 衍策引擎AI 账户。
            </p>
          </div>
          <SidePanelMockup />
        </div>
      </section>

      {/* Extraction Fields */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">智能提取</span>
            <h2 className="section-title">6 大结构化字段</h2>
            <p className="section-subtitle">
              基于中文语义理解引擎，从非结构化政策文本中精准提取关键信息
            </p>
          </div>
          <div className="yc-ext-fields-grid">
            {EXTRACTION_FIELDS.map((f, i) => (
              <div key={i} className="yc-ext-field-card">
                <div className="yc-ext-field-icon">{f.icon}</div>
                <h3 className="yc-ext-field-name">{f.name}</h3>
                <code className="yc-ext-field-key-code">{f.key}</code>
                <p className="yc-ext-field-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Sidebar Query Feature */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">侧边栏查询</span>
            <h2 className="section-title">随时调起 AI 政策匹配</h2>
            <p className="section-subtitle">
              在任何网页上打开侧边栏，输入企业信息即可获取政策匹配建议、企业画像和申报方向。
            </p>
          </div>
          <div className="yc-ext-capabilities">
            <div className="yc-ext-cap-card">
              <div className="yc-ext-cap-icon">{'\u{1F50D}'}</div>
              <h3>政策查询</h3>
              <p>输入企业行业和地区，AI 从政策库中筛选最匹配的申报方向</p>
            </div>
            <div className="yc-ext-cap-card">
              <div className="yc-ext-cap-icon">{'\u{1F3E2}'}</div>
              <h3>企业画像</h3>
              <p>输入企业名称，自动生成技术能力、资质条件和发展阶段分析</p>
            </div>
            <div className="yc-ext-cap-card">
              <div className="yc-ext-cap-icon">{'\u{1F4E6}'}</div>
              <h3>采集管理</h3>
              <p>已采集的政策自动归类到企业账户，支持搜索、标注和导出</p>
            </div>
          </div>
        </div>
      </section>

      {/* Workflow */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">使用流程</span>
            <h2 className="section-title">4 步完成政策采集</h2>
          </div>
          <div className="yc-ext-workflow">
            {WORKFLOW.map((w, i) => (
              <div key={i} className="yc-ext-workflow-step">
                <div className="yc-ext-workflow-num">{w.step}</div>
                <h3>{w.title}</h3>
                <p>{w.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tabs: Overview / Install */}
      <section className="section">
        <div className="container container-narrow">
          <div className="yc-ext-tabs">
            <button
              className={`yc-ext-tab${activeTab === 'overview' ? ' yc-ext-tab-active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              技术规格
            </button>
            <button
              className={`yc-ext-tab${activeTab === 'install' ? ' yc-ext-tab-active' : ''}`}
              onClick={() => setActiveTab('install')}
            >
              安装指南
            </button>
          </div>

          {activeTab === 'overview' && (
            <div className="yc-ext-tab-panel">
              <table className="yc-ext-specs-table">
                <tbody>
                  {TECH_SPECS.map((s, i) => (
                    <tr key={i}>
                      <td className="yc-ext-spec-label">{s.label}</td>
                      <td className="yc-ext-spec-value">{s.value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="yc-ext-security-note">
                <strong>数据安全：</strong>所有政策数据采集和处理均在本地完成。插件不会将您浏览的网页内容上传至任何第三方服务器。仅当您主动点击"保存到 衍策引擎AI"时，提取结果才会通过加密通道同步到您的账户。
              </div>
            </div>
          )}

          {activeTab === 'install' && (
            <div className="yc-ext-tab-panel">
              <div className="yc-ext-install-steps">
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">1</span>
                  <div>
                    <h4>下载插件</h4>
                    <p>前往 <Link href="/downloads">下载页面</Link> 获取 Chrome 插件压缩包并解压到本地文件夹。</p>
                  </div>
                </div>
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">2</span>
                  <div>
                    <h4>打开扩展管理</h4>
                    <p>在 Chrome 浏览器中访问 <code>chrome://extensions/</code></p>
                  </div>
                </div>
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">3</span>
                  <div>
                    <h4>启用开发者模式</h4>
                    <p>打开页面右上角的"开发者模式"开关。</p>
                  </div>
                </div>
                <div className="yc-ext-install-step">
                  <span className="yc-ext-install-num">4</span>
                  <div>
                    <h4>加载插件</h4>
                    <p>点击"加载已解压的扩展程序"，选择解压后的 <code>dist</code> 文件夹。安装完成！</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* CTA */}
      <div className="yc-cta-section">
        <div className="container" style={{ textAlign: 'center' }}>
          <h2 className="yc-cta-title">开始使用 衍策引擎AI 政策助手</h2>
          <p style={{ color: 'var(--text-inverse-secondary)', marginBottom: 24, maxWidth: 520, marginLeft: 'auto', marginRight: 'auto' }}>
            安装浏览器插件，在任何政策页面上获得 AI 驱动的政策匹配与采集能力。
          </p>
          <div className="yc-cta-actions" style={{ justifyContent: 'center' }}>
            <Link href="/downloads" className="yc-btn-primary">下载插件</Link>
            <Link href="/login?register=1" className="yc-btn-outline-white">体验 Demo</Link>
          </div>
        </div>
      </div>
    </>
  );
}
