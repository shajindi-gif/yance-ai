"""企业政策机会分析报告 PDF 生成器（10章节专业版）

Master task section 7: 报告必须包含 10 个章节。
"""

from datetime import UTC, datetime
from io import BytesIO

from weasyprint import HTML

from app.models.models import Company, Opportunity, Policy
from app.services.report.schema import PolicyOpportunityReportDocument
from app.services.safe_rendering import deny_external_url_fetcher, escape_html

_ELIGIBILITY_TAG = {
    "ELIGIBLE": ("tag-green", "符合（待客户复核）"),
    "POTENTIALLY_ELIGIBLE": ("tag-blue", "可能符合（待客户复核）"),
    "NOT_ELIGIBLE": ("tag-red", "不符合"),
    "NEED_MORE_INFORMATION": ("tag-yellow", "证据不足"),
}

# ── CSS 样式 ─────────────────────────────────────────────────
REPORT_CSS = """
  @page { size: A4; margin: 15mm; @bottom-center { content: counter(page) " / " counter(pages); font-size: 9px; color: #999; } }
  @page :first { @bottom-center { content: none; } }
  body { font-family: "Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif; font-size: 11px; color: #1e293b; line-height: 1.6; }
  h1 { color: #0d1b2a; font-size: 18px; border-bottom: 3px solid #0ea5e9; padding-bottom: 8px; margin-top: 36px; margin-bottom: 16px; }
  h2 { color: #0d1b2a; font-size: 14px; margin-top: 20px; margin-bottom: 8px; }
  .cover { page-break-after: always; text-align: center; padding-top: 100px; }
  .cover .brand { font-size: 12px; color: #64748b; letter-spacing: 4px; margin-bottom: 40px; }
  .cover h1 { font-size: 32px; color: #0d1b2a; border: none; margin-bottom: 12px; }
  .cover .subtitle { font-size: 16px; color: #0ea5e9; margin-bottom: 60px; }
  .cover .company { font-size: 24px; color: #0d1b2a; font-weight: 700; margin-bottom: 60px; }
  .cover .meta { font-size: 11px; color: #64748b; line-height: 2; }
  .cover .disclaimer { font-size: 9px; color: #94a3b8; margin-top: 60px; padding: 16px; background: #f8fafc; border-radius: 8px; text-align: left; }
  .summary-box { background: linear-gradient(135deg, #f0f9ff, #eff6ff); border: 1px solid #bae6fd; border-radius: 12px; padding: 20px; margin: 20px 0; }
  .summary-box .stat { display: inline-block; text-align: center; padding: 8px 16px; margin: 4px; }
  .summary-box .stat-value { font-size: 24px; font-weight: 700; color: #0ea5e9; }
  .summary-box .stat-label { font-size: 10px; color: #64748b; }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 10px; }
  th { background: #0d1b2a; color: #fff; padding: 8px 6px; text-align: left; font-weight: 600; }
  td { padding: 7px 6px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
  tr:nth-child(even) td { background: #f8fafc; }
  .score-high { color: #16a34a; font-weight: 700; }
  .score-mid { color: #ea580c; font-weight: 700; }
  .score-low { color: #dc2626; font-weight: 700; }
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 9px; font-weight: 500; margin: 1px; }
  .tag-green { background: #dcfce7; color: #166534; }
  .tag-yellow { background: #fef9c3; color: #854d0e; }
  .tag-red { background: #fee2e2; color: #991b1b; }
  .tag-gray { background: #f1f5f9; color: #64748b; }
  .tag-blue { background: #dbeafe; color: #1e40af; }
  .priority-box { padding: 12px 16px; margin: 8px 0; border-radius: 8px; }
  .priority-p0 { background: #fef2f2; border-left: 4px solid #dc2626; }
  .priority-p1 { background: #fff7ed; border-left: 4px solid #ea580c; }
  .priority-p2 { background: #fffbeb; border-left: 4px solid #ca8a04; }
  .priority-p3 { background: #f0fdf4; border-left: 4px solid #16a34a; }
  .priority-label { font-weight: 700; font-size: 12px; margin-bottom: 4px; }
  .section-intro { color: #64748b; font-size: 11px; margin-bottom: 12px; }
  .footer { margin-top: 40px; padding: 16px; background: #f8fafc; border-radius: 8px; font-size: 9px; color: #64748b; }
  .footer strong { color: #334155; }
  .page-break { page-break-before: always; }
"""


def _score_class(pct: int) -> str:
    if pct >= 70:
        return "score-high"
    if pct >= 50:
        return "score-mid"
    return "score-low"


def _level_cn(level: str) -> str:
    return {
        "national": "国家级",
        "provincial": "省级",
        "municipal": "市级",
        "district": "区级",
    }.get(level, level or "—")


def generate_match_report_pdf(
    company: Company,
    opportunities: list[Opportunity],
    policies: list[Policy],
    *,
    decision_evidence: dict | None = None,
    report_document: PolicyOpportunityReportDocument | None = None,
) -> bytes:
    """生成 10 章节企业政策机会分析报告 PDF。

    When ``report_document`` is provided, eligibility matrix / gaps / materials /
    next steps render from frozen ReportCards (structured DB facts), not static
    templates or matcher heuristics.
    """
    policy_map = {p.id: p for p in policies}
    now = datetime.now(UTC)
    meta = company.metadata_json or {}
    cards = list(report_document.opportunities) if report_document is not None else []

    # ── 统计数据 ──
    scores = [round(o.score * 100) for o in opportunities]
    total = len(opportunities)
    high = sum(1 for s in scores if s >= 70)
    mid = sum(1 for s in scores if 50 <= s < 70)
    low = total - high - mid
    avg_score = round(sum(scores) / total) if total else 0
    max_score = max(scores) if scores else 0

    # ── 按层级统计 ──
    level_counts = {"national": 0, "provincial": 0, "municipal": 0, "district": 0}
    for opp in opportunities:
        p = policy_map.get(opp.policy_id)
        if p and p.level in level_counts:
            level_counts[p.level] += 1

    # ── 01 企业画像 ──
    profile_items = [
        ("企业名称", company.name),
        ("所在地", f"{company.province or '—'} {company.city or ''}".strip()),
        ("行业", company.industry or "—"),
        ("统一信用代码", company.unified_credit_code or "—"),
        ("企业规模", meta.get("scale", "—")),
        ("成立时间", meta.get("founded_year", "—")),
        ("注册资本", meta.get("registered_capital", "—")),
        ("人员规模", meta.get("headcount", "—")),
        ("研发人员占比", meta.get("rd_ratio", "—")),
        ("研发费用占比", f"{meta.get('rd_expense_ratio', '—')}%"),
        ("年营业收入", meta.get("annual_revenue", "—")),
        ("核心产品/技术", meta.get("core_tech", "—")),
        ("已有资质", "、".join(meta.get("qualifications", [])) or "—"),
        ("知识产权", meta.get("ip_count", "—")),
        ("融资阶段", meta.get("funding_stage", "—")),
    ]
    profile_html = (
        "<table>"
        + "".join(
            f'<tr><td style="width:30%;font-weight:600;background:#f8fafc">'
            f"{escape_html(k)}</td><td>{escape_html(v)}</td></tr>"
            for k, v in profile_items
        )
        + "</table>"
    )

    # ── 02 政策机会总览 ──
    overview_html = f"""
    <div class="summary-box">
      <div style="text-align:center">
        <div class="stat"><div class="stat-value">{total}</div><div class="stat-label">匹配政策</div></div>
        <div class="stat"><div class="stat-value" style="color:#16a34a">{high}</div><div class="stat-label">高度匹配(≥70)</div></div>
        <div class="stat"><div class="stat-value" style="color:#ea580c">{mid}</div><div class="stat-label">中度匹配</div></div>
        <div class="stat"><div class="stat-value" style="color:#dc2626">{low}</div><div class="stat-label">低度匹配</div></div>
      </div>
      <div style="text-align:center;margin-top:12px;font-size:10px;color:#64748b">
        国家级 {level_counts["national"]} · 省级 {level_counts["provincial"]} · 市级 {level_counts["municipal"]} · 区级 {level_counts["district"]}
        &nbsp;|&nbsp; 平均匹配度 {avg_score}% · 最高 {max_score}%
      </div>
    </div>"""

    # ── 03 Top 政策推荐 ──
    top_rows = []
    for i, opp in enumerate(opportunities[:10], 1):
        p = policy_map.get(opp.policy_id)
        if not p:
            continue
        pct = round(opp.score * 100)
        ev = opp.evidence_json or {}
        grade = "★★★★★" if pct >= 80 else ("★★★★" if pct >= 70 else ("★★★" if pct >= 50 else "★★"))
        top_rows.append(f"""<tr>
          <td>{i}</td>
          <td>{escape_html(p.title[:40])}{"..." if len(p.title) > 40 else ""}</td>
          <td>{escape_html(_level_cn(p.level))}</td>
          <td>{escape_html(p.province or ("全国" if p.level == "national" else "地域待核实"))}</td>
          <td>{escape_html(p.support_amount or "—")}</td>
          <td class="{_score_class(pct)}">{pct}%</td>
          <td>{grade}</td>
        </tr>""")
    top_table = f"""<table>
      <thead><tr><th>#</th><th>政策名称</th><th>层级</th><th>地区</th><th>支持金额</th><th>匹配度</th><th>推荐</th></tr></thead>
      <tbody>{"".join(top_rows)}</tbody>
    </table>"""

    # ── 04 企业为什么匹配（Top 3 政策的条件分析）──
    why_html = ""
    for opp in opportunities[:3]:
        p = policy_map.get(opp.policy_id)
        if not p:
            continue
        ev = opp.evidence_json or {}
        bd = ev.get("score_breakdown", {})
        why_html += f"""
        <div class="priority-box priority-p1">
          <div class="priority-label">{escape_html(p.title[:35])}</div>
          <div style="font-size:10px;color:#475569">
            评分构成：地区 {escape_html(bd.get("region", 0))}/20 · 行业 {escape_html(bd.get("industry", 0))}/15 · 规模 {escape_html(bd.get("scale", 0))}/10 ·
            资质 {escape_html(bd.get("qualification", 0))}/20 · 技术 {escape_html(bd.get("tech", 0))}/15 · 财务 {escape_html(bd.get("finance", 0))}/10 · 语义 {escape_html(bd.get("semantic", 0))}/10
          </div>
          <div style="font-size:10px;margin-top:4px">
            <span class="tag tag-gray">地区与行业分数仅用于排序</span>
            <span class="tag tag-yellow">资质须核验证明材料</span>
            <span class="tag tag-gray">资格状态：{escape_html(opp.eligibility_status or 'NEED_MORE_INFORMATION')}</span>
          </div>
        </div>"""

    # ── 05 企业政策资格矩阵（优先 ReportCard 结构化条件）──
    if cards:
        matrix_blocks = []
        for card in cards[:10]:
            tag_cls, tag_label = _ELIGIBILITY_TAG.get(
                card.eligibility_status, ("tag-gray", card.eligibility_status)
            )
            if card.criteria:
                rows = "".join(
                    f"<tr><td style=\"font-weight:600\">{escape_html(c.name)}</td>"
                    f"<td>{escape_html(c.actual if c.actual is not None else '—')}</td>"
                    f"<td>{escape_html(c.expected if c.expected is not None else '—')}</td>"
                    f"<td><span class=\"tag tag-gray\">{escape_html(c.status)}</span>"
                    f"{' · 硬门槛' if c.is_hard_gate else ''}</td></tr>"
                    for c in card.criteria
                )
            else:
                rows = (
                    "<tr><td colspan=\"4\">本机会尚无结构化规则条目；"
                    f"资格状态为 <span class=\"tag {tag_cls}\">{escape_html(tag_label)}</span>。"
                    "不得据此宣称已符合。</td></tr>"
                )
            matrix_blocks.append(
                f"<h2>{escape_html(card.policy_title[:40])}</h2>"
                f"<p>policy_id：{escape_html(card.policy_id)} · "
                f"<span class=\"tag {tag_cls}\">{escape_html(tag_label)}</span> · "
                f"{escape_html(card.eligibility_summary)}</p>"
                f"<table><thead><tr><th>条件</th><th>企业事实</th><th>规则期望</th><th>状态</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
                f"<p><strong>下一步：</strong>{escape_html(card.next_step)}</p>"
            )
        matrix_html = "".join(matrix_blocks)
    else:
        matrix_html = (
            "<p>本快照未写入结构化资格卡片，故不渲染条件矩阵占位行；"
            "请以逐条资格证据章节为准。</p>"
        )

    # ── 06 企业当前差距（优先 EligibilityResult.missing_information）──
    if cards:
        gap_items = []
        for card in cards:
            for gap in card.gaps:
                gap_items.append(f"{card.policy_title[:24]}：{gap}")
        gaps_html = (
            "<ul>" + "".join(f"<li>{escape_html(item)}</li>" for item in gap_items) + "</ul>"
            if gap_items
            else "<p>结构化缺口字段为空。这不表示条件已全部满足，仅表示引擎未列出待补信息。</p>"
        )
    else:
        gaps_html = "<p>本快照无 ReportCard，不根据启发式材料清单推断差距。</p>"

    # ── 07 政策行动路线图 ──
    p0, p1, p2, p3 = [], [], [], []
    for opp in opportunities:
        p = policy_map.get(opp.policy_id)
        if not p:
            continue
        pct = round(opp.score * 100)
        item = f"{escape_html(p.title[:30])}（{pct}%）"
        if p.deadline:
            deadline = p.deadline.replace(tzinfo=UTC) if p.deadline.tzinfo is None else p.deadline
            days_left = (deadline - now).days
            if days_left < 0:
                continue
            if days_left <= 30:
                p0.append(item)
            elif days_left <= 90:
                p1.append(item)
            elif days_left <= 180:
                p2.append(item)
            else:
                p3.append(item)
        else:
            if pct >= 70:
                p1.append(item)
            elif pct >= 50:
                p2.append(item)
            else:
                p3.append(item)

    roadmap_html = ""
    for label, items, cls, desc in [
        ("P0：优先复核", p0, "priority-p0", "30天内截止，先核实资格与当前批次"),
        ("P1：未来3个月", p1, "priority-p1", "优先核实条件、来源和申报窗口"),
        ("P2：未来6个月", p2, "priority-p2", "中期规划，开始准备材料"),
        ("P3：未来12个月", p3, "priority-p3", "长期布局，逐步补齐条件"),
    ]:
        items_html = "<br>".join(f"• {item}" for item in items) if items else "暂无"
        roadmap_html += f"""<div class="priority-box {cls}">
          <div class="priority-label">{label}</div>
          <div style="font-size:10px;color:#64748b;margin-bottom:4px">{desc}</div>
          <div style="font-size:10px">{items_html}</div>
        </div>"""

    # ── 08 政策申报日历 ──
    calendar_rows = []
    for opp in opportunities[:8]:
        p = policy_map.get(opp.policy_id)
        if not p:
            continue
        deadline_str = p.deadline.strftime("%Y-%m-%d") if p.deadline else "申报截止日待核实"
        start_str = p.start_date.strftime("%Y-%m-%d") if p.start_date else "—"
        calendar_rows.append(f"""<tr>
          <td>{escape_html(p.title[:30])}</td>
          <td>{start_str}</td>
          <td>{deadline_str}</td>
          <td>建议提前30天启动</td>
        </tr>""")
    calendar_html = f"""<table>
      <thead><tr><th>政策名称</th><th>开放时间</th><th>截止时间</th><th>建议启动</th></tr></thead>
      <tbody>{"".join(calendar_rows)}</tbody>
    </table>"""

    # ── 09 材料准备建议（只列结构化缺口，不用通用静态清单充数）──
    if cards:
        material_rows = []
        for card in cards:
            if not card.gaps:
                continue
            material_rows.append(
                f"<h2>{escape_html(card.policy_title[:40])}</h2><ul>"
                + "".join(f"<li>{escape_html(gap)}</li>" for gap in card.gaps)
                + f"</ul><p>{escape_html(card.next_step)}</p>"
            )
        materials_html = (
            "".join(material_rows)
            if material_rows
            else "<p>无结构化待补材料条目。请客户按原文申报通知自行核对材料清单。</p>"
        )
    else:
        materials_html = (
            "<p>未绑定 ReportCard 时不展示通用材料模板，避免把静态清单当成企业缺口。</p>"
        )

    # ── 10 风险说明 ──
    risk_html = """
    <p><strong>衍策引擎AI 提供以下服务：</strong></p>
    <ul>
      <li>政策信息检索与结构化整理</li>
      <li>基于企业画像的 AI 辅助匹配</li>
      <li>政策资格条件的辅助判断</li>
      <li>政策规划与行动路线图建议</li>
      <li>申报材料整理与初稿辅助</li>
    </ul>
    <p><strong>衍策引擎AI 不做以下承诺：</strong></p>
    <ul>
      <li>不承诺 100% 申报成功</li>
      <li>不承诺 100% 获得补贴</li>
      <li>不是政府指定服务机构</li>
      <li>不声称拥有内部渠道或特殊政府关系</li>
      <li>不伪造审计报告、财务报表、银行流水、营业执照等需要第三方鉴证的材料</li>
    </ul>
    <p style="color:#64748b;font-size:10px;margin-top:16px">
      具体申报条件、申报结果和补贴金额以主管部门、园区、政策文件和审核结果为准。
      本报告基于公开政策数据和用户提供的企业画像生成，仅供参考。
    </p>
    """

    citations = []
    for opp in opportunities:
        details = (decision_evidence or {}).get(opp.id, {})
        quotes = details.get("quotes", [])
        citations.append(
            f"<h2>{escape_html(opp.title)}</h2>"
            f"<p>资格状态：{escape_html(opp.eligibility_status or 'NEED_MORE_INFORMATION')}；"
            f"政策来源版本：{escape_html(opp.policy_version_id or '待核实')}；"
            f"企业画像版本：{escape_html(opp.profile_version_id or '待核实')}；人工复核：待完成</p>"
            + ("".join(
                f"<blockquote>{escape_html(q['quote'])}<br>条款：{escape_html(q.get('article') or '未标明')}；"
                f"来源：{escape_html(q.get('source_url') or '待核实')}；"
                f"原文字符区间：{escape_html(q.get('start'))}–{escape_html(q.get('end'))}</blockquote>"
                for q in quotes
            ) if quotes else "<p>暂无逐字核验的条款证据，不能确认符合。</p>")
        )
    citations_html = "".join(citations) or "<p>暂无政策资格证据。</p>"

    # ── 组装完整 HTML ──
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><style>{REPORT_CSS}</style></head>
<body>

<!-- 封面 -->
<div class="cover">
  <div class="brand">YANCE ENGINE AI</div>
  <h1>企业政策机会分析报告</h1>
  <div class="subtitle">Enterprise Policy Intelligence Report</div>
  <div class="company">{escape_html(company.name)}</div>
  <div class="meta">
    报告编号：YR-{now.strftime("%Y%m%d")}-{company.id.hex[:8].upper()}<br>
    生成时间（UTC）：{(report_document.generated_at if report_document else now).strftime("%Y-%m-%d %H:%M")}<br>
    企业ID：{escape_html(company.id)}<br>
    画像版本：{escape_html(report_document.profile_version_id if report_document else (opportunities[0].profile_version_id if opportunities else "未绑定"))}<br>
    扫描ID：{escape_html(report_document.scan_id if report_document else (opportunities[0].scan_id if opportunities else "未绑定"))}<br>
    schema：{escape_html(report_document.schema_version if report_document else "legacy-unstructured")}<br>
    匹配政策数：{total} 项
  </div>
  <div class="disclaimer">
    <strong>免责声明：</strong>
    {escape_html(report_document.disclaimer if report_document else "本报告基于企业提供资料与已入库政策快照生成，仅供客户自行复核。核对结果不代表政府认定或获批；匹配分不是获批概率。")}
    具体申报条件、结果和金额以主管部门审核为准。Yance 不承诺申报成功率或补贴金额。
  </div>
</div>

<!-- 01 企业画像 -->
<h1>01 企业画像</h1>
<p class="section-intro">基于您填写的企业信息，以下是系统对您的企业画像概要。</p>
{profile_html}

<!-- 02 政策机会总览 -->
<h1 class="page-break">02 政策机会总览</h1>
<p class="section-intro">系统从全局政策库中为您匹配到以下政策机会。</p>
{overview_html}

<!-- 03 Top 政策推荐 -->
<h1>03 Top 政策推荐</h1>
<p class="section-intro">按匹配度排序的前 10 项政策机会。</p>
{top_table}

<!-- 04 企业为什么匹配 -->
<h1 class="page-break">04 企业为什么匹配</h1>
<p class="section-intro">以下展示 Top 3 政策的具体评分构成和匹配理由。</p>
{why_html}

<!-- 05 企业政策资格矩阵 -->
<h1>05 企业政策资格矩阵</h1>
<p class="section-intro">企业现状与政策要求的逐项对比。</p>
{matrix_html}
<h2>逐条资格证据与版本</h2>
{citations_html}

<!-- 06 企业当前差距 -->
<h1 class="page-break">06 企业当前差距</h1>
<p class="section-intro">基于匹配分析，以下是您当前需要补齐的材料和条件。</p>
{gaps_html}

<!-- 07 政策行动路线图 -->
<h1>07 政策行动路线图</h1>
<p class="section-intro">按紧迫度分级的行动建议。</p>
{roadmap_html}

<!-- 08 政策申报日历 -->
<h1 class="page-break">08 政策申报日历</h1>
<p class="section-intro">关键政策的时间节点。</p>
{calendar_html}

<!-- 09 材料准备建议 -->
<h1>09 材料准备建议</h1>
<p class="section-intro">申报各类政策通常需要准备的材料清单。</p>
{materials_html}

<!-- 10 风险说明 -->
<h1 class="page-break">10 风险说明</h1>
{risk_html}

<!-- 页脚 -->
<div class="footer">
  <strong>衍策引擎AI</strong><br>
  数据处理与存储位置以实际部署配置和客户协议为准<br>
  © 2026 Yance Engine AI. 本报告版权归用户所有，未经许可不得用于商业传播。
</div>

</body>
</html>"""

    pdf_bytes = BytesIO()
    HTML(string=html_content, url_fetcher=deny_external_url_fetcher).write_pdf(pdf_bytes)
    return pdf_bytes.getvalue()
