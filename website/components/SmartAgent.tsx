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

/* --- Mock Response Engine --- */
function getMockResponse(input: string): string {
  const lower = input.toLowerCase();

  if (lower.includes('ai') || lower.includes('人工智能') || lower.includes('大模型')) {
    return `根据您的描述，AI 企业可能匹配以下政策方向：

**1. 高新技术企业认定** — 企业所得税减免 15%，研发费用加计扣除
**2. 上海市人工智能专项** — 最高 500 万元项目补贴
**3. 专精特新"小巨人"** — 国家级认定后可获 50-200 万元奖励

建议下一步：完善知识产权布局（至少 6 项软著或 1 项发明专利），确保研发费用占比 ≥ 3%。

如需详细匹配报告，请使用首页的智能输入框或联系我们的顾问团队。`;
  }

  if (lower.includes('专精特新')) {
    return `**专精特新中小企业认定条件概览：**

- 营业收入：上年度 ≥ 1000 万元（创新型中小企业无此要求）
- 研发费用：近两年占比 ≥ 3%
- 知识产权：至少 2 项有效 I 类或 5 项 II 类
- 主导产品：属于制造业核心基础零部件、关键基础材料等
- 市场占有率：省内或细分领域排名前列

**"小巨人"升级版要求更高：** 营收 ≥ 5000 万，研发投入 ≥ 600 万，I 类知识产权 ≥ 2 项。

上海市级专精特新奖励约 10-30 万元，国家级"小巨人"奖励 50-200 万元（各区政策有差异）。`;
  }

  if (lower.includes('高新技术') || lower.includes('高企')) {
    return `**高新技术企业认定核心要求：**

**知识产权：** 至少 1 项发明专利 或 6 项实用新型/软著
**研发费用占比：** 营收 < 5000 万 → ≥ 5%；5000 万-2 亿 → ≥ 4%；> 2 亿 → ≥ 3%
**高新收入占比：** ≥ 60%
**科技人员占比：** ≥ 10%
**创新能力评分：** ≥ 71 分（满分 100）

**申报材料清单：**
1. 高新技术企业认定申请书
2. 企业营业执照
3. 知识产权证书
4. 近三年研发费用专项审计报告
5. 近一年高新技术产品（服务）收入专项审计报告
6. 科技成果转化说明
7. 研发组织管理制度

认定通过后企业所得税由 25% 降至 15%，有效期 3 年。`;
  }

  if (lower.includes('园区') || lower.includes('张江') || lower.includes('漕河泾')) {
    return `**上海重点科技园区扶持政策概览：**

**张江高科技园区：**
- 租金补贴：前两年最高 50% 租金减免
- 人才公寓：符合条件可申请
- 研发补贴：按研发投入给予配套资金

**漕河泾开发区：**
- 创业扶持：最高 100 万元天使投资配套
- 房租补贴：首年 30-50% 减免
- 技术服务平台：免费使用共享实验室

**临港新片区：**
- 企业所得税：重点产业企业 15%
- 人才落户：直接落户绿色通道
- 购房补贴：最高 500 万元

建议根据您的行业方向和企业阶段选择最合适的园区。我们可以帮助做详细的园区对比分析。`;
  }

  if (lower.includes('材料') || lower.includes('申报') || lower.includes('流程')) {
    return `**政策申报通用材料清单：**

**基础材料：**
- 企业营业执照（三证合一）
- 近一年财务审计报告
- 企业信用报告
- 法定代表人身份证明

**技术能力证明：**
- 知识产权证书（专利、软著）
- 科技成果转化证明
- 产学研合作协议
- 技术检测报告

**研发管理材料：**
- 研发项目立项文件
- 研发费用辅助账
- 研发人员花名册
- 研发组织管理制度

不同政策项目可能有额外要求，建议使用我们的 Grant Copilot 模块生成定制化材料清单。`;
  }

  // Default response
  return `感谢您的提问！根据您输入的内容"${input}"，以下是我的初步分析：

衍策引擎AI 平台可以帮助您完成以下工作：
- **政策匹配** — 从全国政策库中筛选适合您企业的政策
- **企业画像** — 分析企业的技术能力、资质条件和发展阶段
- **申报辅助** — 生成材料清单、预审申报条件
- **产业研究** — 提供行业趋势分析和竞争格局报告

建议您提供更详细的企业信息（行业、规模、所在地、核心产品），我可以给出更精准的政策建议。也可以直接在首页输入框中填写企业信息，获取完整的 Policy Intelligence Report。`;
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
      text: '你好！我是衍策引擎AI 智能助手。告诉我你的企业情况，我可以帮你初步分析可申报的政策方向。',
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
            reply = getMockResponse(msg);
          }
          const botMsg: Message = { id: Date.now() + 1, role: 'bot', text: reply, time: now() };
          setMessages((prev) => [...prev, botMsg]);
          setLoading(false);
        })
        .catch(() => {
          const reply = getMockResponse(msg);
          const botMsg: Message = { id: Date.now() + 1, role: 'bot', text: reply, time: now() };
          setMessages((prev) => [...prev, botMsg]);
          setLoading(false);
        });
    } else {
      setTimeout(() => {
        const reply = getMockResponse(msg);
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
