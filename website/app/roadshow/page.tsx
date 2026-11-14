import Link from 'next/link';
import pageStyles from './page.module.css';

export default function RoadshowPage() {
  return (
    <>
      {/* Page Banner */}
      <section
        className={["page-banner", pageStyles.section].filter(Boolean).join(' ')}

      >
        <div className="container">
          <span
            className={["badge", pageStyles.label].filter(Boolean).join(' ')}

          >
            路演与试点
          </span>
          <h1>园区试点方案</h1>
          <p>
            以下内容是可讨论的试点模板，不代表已签约客户、政府合作或已开放活动。
          </p>
        </div>
      </section>

      {/* Pilot Overview */}
      <section className="section">
        <div className="container">
          <div className="split">
            <div className="split-content">
              <span className="section-label">试点提案</span>
              <h2 className="section-title mb-4">园区 Policy Agent 验证方案</h2>
              <p>
                面向产业园区、孵化器和专业服务机构，围绕真实企业资料、政策证据、资格判断与材料工作流设计受控验证。
              </p>
              <p>
                试点范围、数据处理位置、交付周期、服务团队和价格均需在双方确认后写入协议。
              </p>
              <div className="mt-8">
                <Link
                  href="/login?register=1"
                  className={["btn btn-primary", pageStyles.link].filter(Boolean).join(' ')}

                >
                  提交试点需求
                </Link>
              </div>
            </div>
            <div>
              <div className="pilot-card">
                <h3>试点权益</h3>
                <div className={pageStyles.layout}>
                  {[
                    { icon: '\u{26A1}', title: '范围确认', desc: '共同确认数据、流程、权限和验收边界' },
                    { icon: '\u{1F464}', title: '人工复核', desc: '为关键资格结论和材料设置复核责任人' },
                    { icon: '\u{1F4B0}', title: '成本测量', desc: '记录真实模型成本、时延和任务完成率' },
                    { icon: '\u{1F91D}', title: '产品共建', desc: '深度参与产品需求定义和功能迭代' },
                  ].map((benefit) => (
                    <div
                      key={benefit.title}
                      className={pageStyles.layout2}
                    >
                      <span className={pageStyles.label2}>{benefit.icon}</span>
                      <div>
                        <h4 className={pageStyles.heading}>
                          {benefit.title}
                        </h4>
                        <p className={pageStyles.description}>
                          {benefit.desc}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pilot Timeline */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">试点路线</span>
            <h2 className="section-title">3 个月试点时间表</h2>
          </div>

          <div className="container-narrow">
            <div className="timeline">
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 1-2 周：需求对接与数据准备</h3>
                <p className="timeline-item-desc">
                  深入了解园区业务需求，对接企业数据源，初始化政策知识库。完成系统配置和环境搭建。
                </p>
              </div>
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 3-4 周：基础模块部署</h3>
                <p className="timeline-item-desc">
                  部署 PolicyCopilot 和 CompanyProfile 模块，覆盖核心企业的政策问答和画像服务。园区团队培训。
                </p>
              </div>
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 5-8 周：智能匹配上线</h3>
                <p className="timeline-item-desc">
                  接入 SubsidyMatch 和 BriefMaker 模块，实现企业-政策自动匹配和材料清单自动生成。收集反馈持续优化。
                </p>
              </div>
              <div className="timeline-item">
                <h3 className="timeline-item-title">第 9-12 周：全面运营</h3>
                <p className="timeline-item-desc">
                  上线 ParkOps 工作台，整合所有模块。评估试点成果，制定推广计划。
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* KPI Targets */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">验收框架</span>
            <h2 className="section-title">指标必须来自真实试点</h2>
          </div>

          <div className={["grid grid-4", pageStyles.section2].filter(Boolean).join(' ')} >
            {[
              { value: '待测量', label: '覆盖企业数', desc: '数据库真实企业记录' },
              { value: '待评测', label: '匹配准确率', desc: '冻结评测集结果' },
              { value: '待测量', label: '服务响应时间', desc: '真实工作流时延' },
              { value: '待测量', label: '效率变化', desc: '与试点基线对比' },
            ].map((kpi) => (
              <div key={kpi.label} className={["stat-card", pageStyles.section3].filter(Boolean).join(' ')} >
                <div className={["stat-value", pageStyles.section4].filter(Boolean).join(' ')} >
                  {kpi.value}
                </div>
                <div className={["stat-label", pageStyles.section5].filter(Boolean).join(' ')} >
                  {kpi.label}
                </div>
                <p className={pageStyles.description2}>
                  {kpi.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Roadshow Timeline */}
      <section className="section section-alt">
        <div className="container">
          <div className="section-header">
            <span className="section-label">DEMO</span>
            <h2 className="section-title">示例路演主题</h2>
            <p className="section-subtitle">
              下列城市与议题仅用于展示可能的行业场景，目前没有公开活动日程。
            </p>
          </div>

          <div className="container-narrow">
            <div className="timeline">
              {[
                { city: '上海 - 综合场景', desc: '展示政策问答、企业画像和证据工作流。', status: 'DEMO', badge: 'badge-primary' },
                { city: '上海 - 科技产业', desc: '展示生物医药、集成电路等行业的资料与政策匹配流程。', status: 'DEMO', badge: 'badge-primary' },
                { city: '杭州 - 数字经济', desc: '展示数字经济企业资料解析与机会扫描。', status: 'DEMO', badge: 'badge-primary' },
                { city: '深圳 - 科技创新', desc: '展示跨区域政策元数据和证据核对。', status: 'DEMO', badge: 'badge-primary' },
                { city: '北京 - 园区服务', desc: '展示多企业工作区与任务执行设计。', status: 'DEMO', badge: 'badge-primary' },
              ].map((event) => (
                <div key={event.city} className="timeline-item">
                  <h3 className="timeline-item-title">{event.city}</h3>
                  <p className="timeline-item-desc">{event.desc}</p>
                  <div className={pageStyles.section6}>
                    <span className={`badge ${event.badge}`}>{event.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Partnership Models */}
      <section className="section">
        <div className="container">
          <div className="section-header">
            <span className="section-label">合作模式</span>
            <h2 className="section-title">灵活的合作模式</h2>
          </div>

          <div className={["grid grid-3", pageStyles.section7].filter(Boolean).join(' ')} >
            <div className={["card", pageStyles.section8].filter(Boolean).join(' ')} >
              <div className={["card-icon", pageStyles.section9].filter(Boolean).join(' ')} >
                &#x1F91D;
              </div>
              <h3 className="card-title">试点合作</h3>
              <p className="card-desc">
                成为首批试点园区，享受优先部署和优惠价格，共同验证和优化产品。适合愿意深度参与产品共建的园区。
              </p>
            </div>
            <div className={["card", pageStyles.section10].filter(Boolean).join(' ')} >
              <div className={["card-icon", pageStyles.section11].filter(Boolean).join(' ')} >
                &#x1F3EB;
              </div>
              <h3 className="card-title">渠道合作</h3>
              <p className="card-desc">
                面向园区服务商、咨询机构和行业协会，成为 Policy Agent 的渠道合作伙伴，共同推广智能政策服务。
              </p>
            </div>
            <div className={["card", pageStyles.section8].filter(Boolean).join(' ')} >
              <div className={["card-icon", pageStyles.section12].filter(Boolean).join(' ')} >
                &#x1F4E1;
              </div>
              <h3 className="card-title">技术合作</h3>
              <p className="card-desc">
                面向政务平台和大型系统集成商，提供 API 和 SDK 集成能力，将政策智能服务嵌入现有业务系统。
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section
        className={["cta-section", pageStyles.section13].filter(Boolean).join(' ')}

      >
        <div className="container">
          <h2 className="cta-title">加入 Policy Agent 园区智能服务生态</h2>
          <p className="cta-subtitle">
            无论你是园区运营方、服务商还是技术集成商，我们都欢迎你的合作意向。
          </p>
          <div className="cta-actions">
            <Link
              href="/login?register=1"
              className={["btn btn-lg", pageStyles.link2].filter(Boolean).join(' ')}

            >
              预约演示
            </Link>
            <a href="mailto:yanceai@163.com" className="btn btn-outline-white btn-lg">
              联系合作
            </a>
          </div>
        </div>
      </section>
    </>
  );
}
