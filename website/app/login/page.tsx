'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api from '@/lib/api';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (searchParams.get('register') === '1') {
      setIsLogin(false);
    }
  }, [searchParams]);

  // Login state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register state
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [province, setProvince] = useState('');
  const [city, setCity] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [ownerPassword, setOwnerPassword] = useState('');
  const [agreed, setAgreed] = useState(false);

  const TERMS_VERSION = '2026-09-19';

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.login(loginEmail, loginPassword);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.register({
        company_name: companyName,
        industry: industry || undefined,
        province: province || undefined,
        city: city || undefined,
        owner_name: ownerName,
        owner_email: ownerEmail,
        owner_password: ownerPassword,
        agreed_terms_version: agreed ? TERMS_VERSION : undefined,
      });
      router.push('/onboarding');
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="yc-auth-page">
      <div className="yc-auth-container">
        <div className="yc-auth-card">
          <div className="yc-auth-header">
            <img src="/logo.png" alt="衍策引擎AI" className="yc-auth-logo" />
            <h1>衍策引擎AI</h1>
            <p className="yc-auth-subtitle">新质生产力企业的政策匹配与申报 Agent</p>
          </div>

          <div className="yc-auth-tabs">
            <button className={`yc-auth-tab ${isLogin ? 'active' : ''}`} onClick={() => { setIsLogin(true); setError(''); }}>登录</button>
            <button className={`yc-auth-tab ${!isLogin ? 'active' : ''}`} onClick={() => { setIsLogin(false); setError(''); }}>免费注册</button>
          </div>

          {error && <div className="yc-auth-error">{error}</div>}

          {isLogin ? (
            <form onSubmit={handleLogin} className="yc-auth-form">
              <div className="yc-form-group">
                <label>邮箱</label>
                <input type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="your@company.com" required />
              </div>
              <div className="yc-form-group">
                <label>密码</label>
                <input type="password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} placeholder="输入密码" required />
              </div>
              <button type="submit" className="yc-btn-primary yc-btn-full" disabled={loading}>
                {loading ? '登录中...' : '登录'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister} className="yc-auth-form">
              <div className="yc-form-group">
                <label>企业全称 <span className="yc-required">*</span></label>
                <input type="text" value={companyName} onChange={e => setCompanyName(e.target.value)} placeholder="如：上海某某科技有限公司" required />
              </div>
              <div className="yc-form-row-2">
                <div className="yc-form-group">
                  <label>行业</label>
                  <select value={industry} onChange={e => setIndustry(e.target.value)}>
                    <option value="">请选择（可选）</option>
                    <option value="人工智能">人工智能</option>
                    <option value="集成电路">集成电路 / 半导体</option>
                    <option value="新能源">新能源 / 储能</option>
                    <option value="新材料">新材料</option>
                    <option value="生物医药">生物医药</option>
                    <option value="高端装备">高端装备 / 智能制造</option>
                    <option value="航空航天">航空航天 / 低空经济</option>
                    <option value="软件信息">软件与信息技术</option>
                    <option value="数字经济">数字经济</option>
                    <option value="其他">其他</option>
                  </select>
                </div>
                <div className="yc-form-group">
                  <label>省份</label>
                  <input type="text" value={province} onChange={e => setProvince(e.target.value)} placeholder="如：上海市" />
                </div>
              </div>
              <div className="yc-form-group">
                <label>城市</label>
                <input type="text" value={city} onChange={e => setCity(e.target.value)} placeholder="如：徐汇区（可选）" />
              </div>
              <div className="yc-form-group">
                <label>联系人姓名 <span className="yc-required">*</span></label>
                <input type="text" value={ownerName} onChange={e => setOwnerName(e.target.value)} placeholder="您的姓名" required />
              </div>
              <div className="yc-form-group">
                <label>工作邮箱 <span className="yc-required">*</span></label>
                <input type="email" value={ownerEmail} onChange={e => setOwnerEmail(e.target.value)} placeholder="your@company.com" required />
              </div>
              <div className="yc-form-group">
                <label>密码 <span className="yc-required">*</span></label>
                <input type="password" value={ownerPassword} onChange={e => setOwnerPassword(e.target.value)} placeholder="至少 12 位，含字母和数字" minLength={12} required />
              </div>
              <div className="yc-agree-group">
                <label className="yc-agree-label">
                  <input
                    type="checkbox"
                    checked={agreed}
                    onChange={e => setAgreed(e.target.checked)}
                  />
                  <span>
                    我已阅读并同意
                    <a href="/terms" target="_blank" rel="noopener noreferrer">《服务条款》</a>
                    与
                    <a href="/privacy" target="_blank" rel="noopener noreferrer">《隐私政策》</a>
                  </span>
                </label>
              </div>
              <button type="submit" className="yc-btn-primary yc-btn-full" disabled={loading || !agreed}>
                {loading ? '注册中...' : '立即注册'}
              </button>
              {!agreed ? (
                <p className="yc-auth-hint">请先勾选同意《服务条款》与《隐私政策》后再注册</p>
              ) : null}
            </form>
          )}
        </div>
      </div>

      <style jsx>{`
        .yc-auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0d1b2a 0%, #1b2d45 50%, #142842 100%); padding: 40px 20px; }
        .yc-auth-container { width: 100%; max-width: 480px; }
        .yc-auth-card { background: rgba(255, 255, 255, 0.98); border-radius: 20px; padding: 40px 36px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3); }
        .yc-auth-header { text-align: center; margin-bottom: 28px; }
        .yc-auth-logo { width: 56px; height: 56px; margin-bottom: 12px; }
        .yc-auth-header h1 { font-size: 22px; font-weight: 700; color: #0d1b2a; margin: 0 0 6px; }
        .yc-auth-subtitle { color: #64748b; font-size: 13px; margin: 0; }
        .yc-auth-tabs { display: flex; background: #f1f5f9; border-radius: 10px; padding: 4px; margin-bottom: 20px; }
        .yc-auth-tab { flex: 1; padding: 10px; border: none; background: transparent; border-radius: 8px; font-size: 14px; font-weight: 500; color: #64748b; cursor: pointer; transition: all 0.2s; }
        .yc-auth-tab.active { background: #fff; color: #0d1b2a; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .yc-auth-error { background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
        .yc-auth-form { display: flex; flex-direction: column; gap: 14px; }
        .yc-form-group label { display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 4px; }
        .yc-required { color: #f97316; }
        .yc-form-group input, .yc-form-group select { width: 100%; padding: 11px 14px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 14px; outline: none; background: #fff; }
        .yc-form-group input:focus, .yc-form-group select:focus { border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1); }
        .yc-form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .yc-btn-full { width: 100%; padding: 13px; font-size: 15px; margin-top: 4px; }
        .yc-auth-hint { text-align: center; font-size: 12px; color: #94a3b8; margin: 8px 0 0; }
        .yc-agree-group { margin-top: 2px; }
        .yc-agree-label { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #374151; cursor: pointer; line-height: 1.5; }
        .yc-agree-label input[type='checkbox'] { width: 16px; height: 16px; margin-top: 2px; flex-shrink: 0; cursor: pointer; accent-color: #0ea5e9; }
        .yc-agree-label a { color: #0ea5e9; text-decoration: none; }
        .yc-agree-label a:hover { text-decoration: underline; }
        @media (max-width: 500px) { .yc-form-row-2 { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>加载中...</div>}>
      <LoginContent />
    </Suspense>
  );
}
