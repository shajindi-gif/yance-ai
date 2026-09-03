'use client';

import { useState, useRef, useEffect } from 'react';
import api from '@/lib/api';

/* --- Types --- */
interface Message {
  id: number;
  role: 'user' | 'bot';
  text: string;
  time: string;
}

/* --- Quick Actions --- */
const QUICK_ACTIONS = [
  '我是 AI 企业，有哪些政策可以申报？',
  '帮我查一下专精特新条件',
  '高新技术企业认定需要什么材料？',
  '上海张江有哪些园区扶持政策？',
];

/* --- Safe unauthenticated fallback --- */
function getUnavailableResponse(): string {
  return `当前助手没有获得可引用的政策来源，因此不会生成资格、金额或材料结论。

请登录工作区，选择企业并运行带来源的政策扫描。任何关键结论仍需核对政策原文和主管部门要求。`;
}

function now(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

/* --- Component --- */
export default function SmartAgent() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      role: 'bot',
      text: '你好！只有检索到可引用的政策来源时，我才会返回政策结果。请登录工作区并选择企业开始扫描。',
      time: now(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  function send(text?: string) {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    const userMsg: Message = { id: Date.now(), role: 'user', text: msg, time: now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    // Use real API if authenticated, otherwise mock
    if (api.isAuthenticated()) {
      api.searchPolicies(msg, 3)
        .then((results) => {
          let reply: string;
          if (results.length > 0) {
            reply = `根据您的问题，找到以下相关政策：\n\n` +
              results.map((p, i) => `**${i + 1}. ${p.title}**${p.jurisdiction ? `（${p.jurisdiction}）` : ''}`).join('\n') +
              `\n\n如需详细匹配报告，请登录工作台查看完整分析。`;
          } else {
            reply = getUnavailableResponse();
          }
          const botMsg: Message = { id: Date.now() + 1, role: 'bot', text: reply, time: now() };
          setMessages((prev) => [...prev, botMsg]);
          setLoading(false);
        })
        .catch(() => {
          const reply = getUnavailableResponse();
          const botMsg: Message = { id: Date.now() + 1, role: 'bot', text: reply, time: now() };
          setMessages((prev) => [...prev, botMsg]);
          setLoading(false);
        });
    } else {
      setTimeout(() => {
        const reply = getUnavailableResponse();
        const botMsg: Message = { id: Date.now() + 1, role: 'bot', text: reply, time: now() };
        setMessages((prev) => [...prev, botMsg]);
        setLoading(false);
      }, 600 + Math.random() * 400);
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <>
      {/* Floating Trigger */}
      {!open && (
        <button className="yc-chat-trigger" onClick={() => setOpen(true)} aria-label="打开智能助手">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span className="yc-chat-trigger-label">AI 助手</span>
        </button>
      )}

      {/* Chat Panel */}
      {open && (
        <div className="yc-chat-panel">
          {/* Header */}
          <div className="yc-chat-header">
            <div className="yc-chat-header-left">
              <div className="yc-chat-header-avatar">
                <img src="/logo.png" alt="衍策引擎AI" width={28} height={28} style={{ borderRadius: '50%' }} />
              </div>
              <div>
                <div className="yc-chat-title">衍策引擎AI 智能助手</div>
                <div className="yc-chat-subtitle">政策匹配 · 企业诊断</div>
              </div>
            </div>
            <button className="yc-chat-close" onClick={() => setOpen(false)} aria-label="关闭">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          {/* Messages */}
          <div className="yc-chat-messages" ref={listRef}>
            {messages.map((m) => (
              <div key={m.id} className={`yc-chat-bubble ${m.role === 'user' ? 'yc-chat-bubble-user' : 'yc-chat-bubble-bot'}`}>
                <div className={`yc-chat-bubble-content ${m.role === 'user' ? 'yc-chat-bubble-content-user' : 'yc-chat-bubble-content-bot'}`}>
                  {m.text.split('\n').map((line, i) => (
                    <span key={i}>
                      {line.startsWith('**') && line.endsWith('**') ? (
                        <strong>{line.slice(2, -2)}</strong>
                      ) : line.includes('**') ? (
                        line.split('**').map((seg, j) =>
                          j % 2 === 1 ? <strong key={j}>{seg}</strong> : <span key={j}>{seg}</span>
                        )
                      ) : (
                        line
                      )}
                      {i < m.text.split('\n').length - 1 && <br />}
                    </span>
                  ))}
                </div>
                <div className="yc-chat-time">{m.time}</div>
              </div>
            ))}
            {loading && (
              <div className="yc-chat-bubble yc-chat-bubble-bot">
                <div className="yc-chat-bubble-content yc-chat-bubble-content-bot">
                  <span className="yc-chat-typing">
                    <span /><span /><span />
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          {messages.length <= 1 && (
            <div className="yc-chat-quick-actions">
              {QUICK_ACTIONS.map((q) => (
                <button key={q} className="yc-chat-quick-chip" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="yc-chat-input-area">
            <input
              className="yc-chat-input"
              type="text"
              placeholder="描述你的企业或提问..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              disabled={loading}
            />
            <button
              className="yc-chat-send"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              aria-label="发送"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>

          {/* Footer */}
          <div className="yc-chat-footer">
            由 衍策引擎AI 提供 · 仅供参考，不构成申报承诺
          </div>
        </div>
      )}
    </>
  );
}
