'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import api from '@/lib/api';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    if (searchParams.get('register') === '1') {
      setIsLogin(false);
    }
  }, [searchParams]);

  // Login state（密码 / 验证码 双方式）
  const [loginMode, setLoginMode] = useState<'password' | 'code'>('password');
  const [emailLoginEnabled, setEmailLoginEnabled] = useState(false);
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Password reset state（忘记密码：邮箱验证码重置）
  const [resetMode, setResetMode] = useState(false);
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Email code state
  const [codeValue, setCodeValue] = useState('');
  const [codeSending, setCodeSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [needsProfile, setNeedsProfile] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [profileCompany, setProfileCompany] = useState('');
  const [codeAgreed, setCodeAgreed] = useState(false);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  // 验证码 tab 由后端能力开关控制：Resend 通道未配置时不展示
  useEffect(() => {
    let active = true;
    api.getAuthConfig().then(cfg => {
      if (active) setEmailLoginEnabled(cfg.email_login_enabled);
    });
    return () => {
      active = false;
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []);

  const startCountdown = (seconds = 60) => {
    setCountdown(seconds);
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          if (countdownRef.current) clearInterval(countdownRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setNotice('');
    try {
      await api.login(loginEmail, loginPassword);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSendResetCode = async () => {
    setError('');
    setNotice('');
    if (!loginEmail.trim()) {
      setError('请先输入注册邮箱');
      return;
    }
    setCodeSending(true);
    try {
      await api.requestPasswordReset(loginEmail.trim());
      setNotice('如果该邮箱已注册，重置验证码已发送，请查收邮箱（10 分钟内有效）');
      startCountdown(60);
    } catch (err) {
      setError(err instanceof Error ? err.message : '验证码发送失败');
    } finally {
      setCodeSending(false);
    }
  };

  const handleResetSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 12) {
      setError('新密码至少 12 位');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    setLoading(true);
    setError('');
    setNotice('');
    try {
      await api.resetPassword({
        email: loginEmail.trim(),
        code: resetCode.trim(),
        new_password: newPassword,
      });
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : '密码重置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSendCode = async () => {
    setError('');
    setNotice('');
    if (!loginEmail.trim()) {
      setError('请先输入邮箱');
      return;
    }
    setCodeSending(true);
    try {
      await api.sendEmailCode(loginEmail.trim());
      setNotice('验证码已发送，请查收邮箱（10 分钟内有效）');
      startCountdown(60);
    } catch (err) {
      setError(err instanceof Error ? err.message : '验证码发送失败');
    } finally {
      setCodeSending(false);
    }
  };

  const handleCodeLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setNotice('');
    try {
      await api.verifyEmailCode({
        email: loginEmail.trim(),
        code: codeValue.trim(),
        ...(needsProfile
          ? {
              owner_name: profileName.trim() || undefined,
              company_name: profileCompany.trim() || undefined,
              agreed_terms_version: codeAgreed ? TERMS_VERSION : undefined,
            }
          : {}),
      });
      router.push('/dashboard');
    } catch (err) {
      const msg = err instanceof Error ? err.message : '验证码校验失败';
      if (msg.includes('首次登录')) {
        // 新邮箱：后端要求补充信息（验证码未被消耗，补齐后直接重新提交）
        setNeedsProfile(true);
        setError('这是您的首次登录，将自动为您创建工作区，请补充以下信息');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setNotice('');
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
            <p className="yc-auth-subtitle">新质生产力企业的政策与资源证据工作台</p>
          </div>

          <div className="yc-auth-tabs">
            <button className={`yc-auth-tab ${isLogin ? 'active' : ''}`} onClick={() => { setIsLogin(true); setError(''); setNotice(''); }}>登录</button>
            <button className={`yc-auth-tab ${!isLogin ? 'active' : ''}`} onClick={() => { setIsLogin(false); setError(''); setNotice(''); }}>免费注册</button>
          </div>

          {error && <div role="alert" className="yc-auth-error">{error}</div>}
          {notice && <div role="status" className="yc-auth-notice">{notice}</div>}

          {isLogin ? (
            <>
              {emailLoginEnabled && (
                <div className="yc-auth-subtabs">
                  <button
                    type="button"
                    className={`yc-auth-subtab ${loginMode === 'password' ? 'active' : ''}`}
                    onClick={() => { setLoginMode('password'); setError(''); setNotice(''); }}
                  >
                    密码登录
                  </button>
                  <button
                    type="button"
                    className={`yc-auth-subtab ${loginMode === 'code' ? 'active' : ''}`}
                    onClick={() => { setLoginMode('code'); setResetMode(false); setError(''); setNotice(''); }}
                  >
                    验证码登录
                  </button>
                </div>
              )}

              {loginMode === 'password' && !resetMode ? (
                <form onSubmit={handleLogin} className="yc-auth-form">
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-1">邮箱</label>
                    <input id="auth-field-1" type="email" autoComplete="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="your@company.com" required />
                  </div>
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-2">密码</label>
                    <input id="auth-field-2" type="password" autoComplete="current-password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} placeholder="输入密码" required />
                  </div>
                  <button type="submit" className="yc-btn-primary yc-btn-full" disabled={loading}>
                    {loading ? '登录中...' : '登录'}
                  </button>
                  {emailLoginEnabled && (
                    <p className="yc-auth-hint">
                      <button type="button" className="yc-link-btn" onClick={() => { setResetMode(true); setError(''); setNotice(''); }}>
                        忘记密码？
                      </button>
                    </p>
                  )}
                </form>
              ) : loginMode === 'password' && resetMode ? (
                <form onSubmit={handleResetSubmit} className="yc-auth-form">
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-3">注册邮箱</label>
                    <input id="auth-field-3" type="email" autoComplete="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="your@company.com" required />
                  </div>
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-4">重置验证码</label>
                    <div className="yc-code-row">
                      <input id="auth-field-4"
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={resetCode}
                        onChange={e => setResetCode(e.target.value.replace(/\D/g, ''))}
                        placeholder="6 位验证码"
                        required
                      />
                      <button
                        type="button"
                        className="yc-code-send"
                        onClick={handleSendResetCode}
                        disabled={countdown > 0 || codeSending}
                      >
                        {codeSending ? '发送中...' : countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                      </button>
                    </div>
                  </div>
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-5">新密码 <span className="yc-required">*</span></label>
                    <input id="auth-field-5" type="password" autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} placeholder="至少 12 位，含字母和数字" minLength={12} required />
                  </div>
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-6">确认新密码 <span className="yc-required">*</span></label>
                    <input id="auth-field-6" type="password" autoComplete="new-password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder="再次输入新密码" required />
                  </div>
                  <button
                    type="submit"
                    className="yc-btn-primary yc-btn-full"
                    disabled={loading || !resetCode || newPassword.length < 12 || newPassword !== confirmPassword}
                  >
                    {loading ? '重置中...' : '重置密码并登录'}
                  </button>
                  <p className="yc-auth-hint">
                    <button type="button" className="yc-link-btn" onClick={() => { setResetMode(false); setError(''); setNotice(''); }}>
                      返回登录
                    </button>
                  </p>
                </form>
              ) : loginMode === 'code' ? (
                <form onSubmit={handleCodeLogin} className="yc-auth-form">
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-7">邮箱</label>
                    <input id="auth-field-7" type="email" autoComplete="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="your@company.com" required />
                  </div>
                  <div className="yc-form-group">
                    <label htmlFor="auth-field-8">验证码</label>
                    <div className="yc-code-row">
                      <input id="auth-field-8"
                        type="text"
                        inputMode="numeric"
                        maxLength={6}
                        value={codeValue}
                        onChange={e => setCodeValue(e.target.value.replace(/\D/g, ''))}
                        placeholder="6 位验证码"
                        required
                      />
                      <button
                        type="button"
                        className="yc-code-send"
                        onClick={handleSendCode}
                        disabled={countdown > 0 || codeSending}
                      >
                        {codeSending ? '发送中...' : countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                      </button>
                    </div>
                  </div>

                  {needsProfile && (
                    <>
                      <div className="yc-form-group">
                        <label htmlFor="auth-field-9">您的姓名 <span className="yc-required">*</span></label>
                        <input id="auth-field-9" type="text" value={profileName} onChange={e => setProfileName(e.target.value)} placeholder="联系人姓名" required />
                      </div>
                      <div className="yc-form-group">
                        <label htmlFor="auth-field-10">企业名称 <span className="yc-required">*</span></label>
                        <input id="auth-field-10" type="text" value={profileCompany} onChange={e => setProfileCompany(e.target.value)} placeholder="如：上海某某科技有限公司" required />
                      </div>
                      <div className="yc-agree-group">
                        <label className="yc-agree-label">
                          <input type="checkbox" checked={codeAgreed} onChange={e => setCodeAgreed(e.target.checked)} />
                          <span>
                            我已阅读并同意
                            <a href="/terms" target="_blank" rel="noopener noreferrer">《服务条款》</a>
                            与
                            <a href="/privacy" target="_blank" rel="noopener noreferrer">《隐私政策》</a>
                          </span>
                        </label>
                      </div>
                    </>
                  )}

                  <button
                    type="submit"
                    className="yc-btn-primary yc-btn-full"
                    disabled={loading || !codeValue || (needsProfile && (!profileName.trim() || !profileCompany.trim() || !codeAgreed))}
                  >
                    {loading ? '登录中...' : needsProfile ? '创建并开始使用' : '登录'}
                  </button>
                  <p className="yc-auth-hint">未注册过的邮箱验证后会自动创建工作区</p>
                </form>
              ) : null}
            </>
          ) : (
            <form onSubmit={handleRegister} className="yc-auth-form">
              <div className="yc-form-group">
                <label htmlFor="auth-field-11">企业全称 <span className="yc-required">*</span></label>
                <input id="auth-field-11" type="text" value={companyName} onChange={e => setCompanyName(e.target.value)} placeholder="如：上海某某科技有限公司" required />
              </div>
              <div className="yc-form-row-2">
                <div className="yc-form-group">
                  <label htmlFor="auth-field-12">行业</label>
                  <select id="auth-field-12" value={industry} onChange={e => setIndustry(e.target.value)}>
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
                  <label htmlFor="auth-field-13">省份</label>
                  <input id="auth-field-13" type="text" value={province} onChange={e => setProvince(e.target.value)} placeholder="如：上海市" />
                </div>
              </div>
              <div className="yc-form-group">
                <label htmlFor="auth-field-14">城市</label>
                <input id="auth-field-14" type="text" value={city} onChange={e => setCity(e.target.value)} placeholder="如：徐汇区（可选）" />
              </div>
              <div className="yc-form-group">
                <label htmlFor="auth-field-15">联系人姓名 <span className="yc-required">*</span></label>
                <input id="auth-field-15" type="text" value={ownerName} onChange={e => setOwnerName(e.target.value)} placeholder="您的姓名" required />
              </div>
              <div className="yc-form-group">
                <label htmlFor="auth-field-16">工作邮箱 <span className="yc-required">*</span></label>
                <input id="auth-field-16" type="email" autoComplete="email" value={ownerEmail} onChange={e => setOwnerEmail(e.target.value)} placeholder="your@company.com" required />
              </div>
              <div className="yc-form-group">
                <label htmlFor="auth-field-17">密码 <span className="yc-required">*</span></label>
                <input id="auth-field-17" type="password" autoComplete="new-password" value={ownerPassword} onChange={e => setOwnerPassword(e.target.value)} placeholder="至少 12 位，含字母和数字" minLength={12} required />
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
        .yc-auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--paper); padding: 110px 20px 60px; }
        .yc-auth-container { width: 100%; max-width: 480px; }
        .yc-auth-card { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 40px 36px; box-shadow: 0 8px 30px rgba(32,48,56,.04); }
        .yc-auth-header { text-align: center; margin-bottom: 28px; }
        .yc-auth-logo { width: 56px; height: 56px; margin-bottom: 12px; }
        .yc-auth-header h1 { font-size: 22px; font-weight: 700; color: #0d1b2a; margin: 0 0 6px; }
        .yc-auth-subtitle { color: #64748b; font-size: 13px; margin: 0; }
        .yc-auth-tabs { display: flex; background: #f1f5f9; border-radius: 10px; padding: 4px; margin-bottom: 20px; }
        .yc-auth-tab { flex: 1; padding: 10px; border: none; background: transparent; border-radius: 8px; font-size: 14px; font-weight: 500; color: #64748b; cursor: pointer; transition: all 0.2s; }
        .yc-auth-tab.active { background: #fff; color: #0d1b2a; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
        .yc-auth-subtabs { display: flex; gap: 16px; border-bottom: 1px solid #e2e8f0; margin-bottom: 16px; }
        .yc-auth-subtab { padding: 8px 2px; border: none; background: transparent; font-size: 13px; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
        .yc-auth-subtab.active { color: #126a9a; font-weight: 600; border-bottom-color: #126a9a; }
        .yc-auth-error { background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
        .yc-auth-notice { background: #f0f9ff; border: 1px solid #bae6fd; color: #0369a1; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; }
        .yc-auth-form { display: flex; flex-direction: column; gap: 14px; }
        .yc-form-group label { display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 4px; }
        .yc-required { color: #f97316; }
        .yc-form-group input, .yc-form-group select { width: 100%; padding: 11px 14px; border: 1px solid #e2e8f0; border-radius: 10px; font-size: 14px; outline: none; background: #fff; }
        .yc-form-group input:focus, .yc-form-group select:focus { border-color: #126a9a; box-shadow: 0 0 0 3px rgba(18, 106, 154, 0.12); }
        .yc-form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .yc-code-row { display: flex; gap: 10px; }
        .yc-code-row input { flex: 1; }
        .yc-code-send { flex-shrink: 0; padding: 0 16px; border: 1px solid #126a9a; border-radius: 10px; background: #fff; color: #126a9a; font-size: 13px; font-weight: 500; cursor: pointer; white-space: nowrap; transition: all 0.2s; }
        .yc-code-send:hover:not(:disabled) { background: #f0f7fb; }
        .yc-code-send:disabled { border-color: #cbd5e1; color: #94a3b8; cursor: not-allowed; }
        .yc-link-btn { background: none; border: none; color: #126a9a; font-size: 12px; cursor: pointer; padding: 0; text-decoration: underline; }
        .yc-link-btn:hover { color: #0d4f74; }
        .yc-btn-full { width: 100%; padding: 13px; font-size: 15px; margin-top: 4px; }
        .yc-auth-hint { text-align: center; font-size: 12px; color: var(--muted); margin: 8px 0 0; }
        .yc-agree-group { margin-top: 2px; }
        .yc-agree-label { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #374151; cursor: pointer; line-height: 1.5; }
        .yc-agree-label input[type='checkbox'] { width: 16px; height: 16px; margin-top: 2px; flex-shrink: 0; cursor: pointer; accent-color: #126a9a; }
        .yc-agree-label a { color: #126a9a; text-decoration: none; }
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
