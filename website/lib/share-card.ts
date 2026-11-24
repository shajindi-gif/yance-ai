// Shareable policy-opportunity card: pure model (testable) + Canvas painter (browser only).
// Wording stays neutral: a match record is never presented as an eligibility result.

export const SHARE_CARD_WIDTH = 1080;
export const SHARE_CARD_HEIGHT = 1440;
export const SHARE_SITE_LABEL = 'yance.ai';
export const SHARE_DISCLAIMER =
  '匹配记录仅用于初筛，不代表政府认定或资格结论；资格、金额与截止时间以原文和主管部门为准。';
export const SHARE_ANONYMOUS_LABEL = '一家科技企业';
const SAME_REGION_FIT = 16;
const TOP_N = 3;

type OpportunityLike = {
  title: string;
  score: number | null;
  eligibility_status: string;
  policy_snapshot_json: {
    title?: string;
    issuing_authority?: string | null;
    jurisdiction?: string | null;
    district?: string | null;
    city?: string | null;
    deadline?: string | null;
  };
  evidence_json: { [key: string]: unknown };
};

function featuresOf(opportunity: OpportunityLike): Record<string, unknown> {
  const features = opportunity.evidence_json?.rank_features;
  return features && typeof features === 'object' ? (features as Record<string, unknown>) : {};
}

export interface ShareItem {
  title: string;
  authority: string | null;
  region: string | null;
  deadline: string | null;
  sameRegion: boolean;
  rank: number;
}

export interface ShareCardModel {
  headline: string;
  subhead: string;
  companyLabel: string;
  generatedOn: string;
  reviewable: number;
  total: number;
  cityMatched: number;
  withDeadline: number;
  items: ShareItem[];
}

function finiteNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function plainDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : null;
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

export function formatChineseDate(now: Date): string {
  return `${now.getFullYear()}年${pad(now.getMonth() + 1)}月${pad(now.getDate())}日`;
}

/** Stable ordering for share: effectiveness score (rank_features.final_score) then legacy score. */
export function opportunityRank(opportunity: OpportunityLike): number {
  const final = finiteNumber(featuresOf(opportunity).final_score);
  if (final !== null) return final;
  const legacy = finiteNumber(opportunity.score);
  return legacy === null ? 0 : legacy * 100;
}

function isReviewable(opportunity: OpportunityLike): boolean {
  if (opportunity.eligibility_status === 'NOT_ELIGIBLE') return false;
  const note = String(featuresOf(opportunity).ranking_note ?? '');
  return !note.includes('弱匹配');
}

function sameRegion(opportunity: OpportunityLike): boolean {
  const fit = finiteNumber(featuresOf(opportunity).region_fit);
  return fit !== null && fit >= SAME_REGION_FIT;
}

export function buildShareModel(
  opportunities: OpportunityLike[],
  options: { companyName?: string | null; showCompany?: boolean; now?: Date } = {},
): ShareCardModel {
  const now = options.now ?? new Date();
  const total = opportunities.length;
  const reviewableList = opportunities.filter(isReviewable);
  const reviewable = reviewableList.length;
  const cityMatched = reviewableList.filter(sameRegion).length;
  const withDeadline = reviewableList.filter(item => plainDate(item.policy_snapshot_json?.deadline)).length;
  const top = [...reviewableList]
    .sort((a, b) => opportunityRank(b) - opportunityRank(a))
    .slice(0, TOP_N)
    .map<ShareItem>(item => {
      const snapshot = item.policy_snapshot_json ?? {};
      const region = [snapshot.jurisdiction, snapshot.city, snapshot.district].filter(Boolean).join(' · ') || null;
      return {
        title: (snapshot.title || item.title || '未命名政策').trim(),
        authority: snapshot.issuing_authority?.trim() || null,
        region,
        deadline: plainDate(snapshot.deadline),
        sameRegion: sameRegion(item),
        rank: Math.round(opportunityRank(item)),
      };
    });
  const name = options.companyName?.trim();
  const companyLabel = options.showCompany && name ? name : SHARE_ANONYMOUS_LABEL;
  return {
    headline: reviewable > 0 ? `本次扫描找到 ${reviewable} 条可优先核对的政策机会` : '本次扫描暂无可优先核对的政策机会',
    subhead: `${companyLabel} · ${cityMatched} 条同城/同省 · ${withDeadline} 条有截止窗口`,
    companyLabel,
    generatedOn: formatChineseDate(now),
    reviewable,
    total,
    cityMatched,
    withDeadline,
    items: top,
  };
}

export function shareCopy(model: ShareCardModel): string {
  const lines = [
    `我用衍策引擎做了一次政策机会扫描：${model.reviewable} 条可优先核对（${model.cityMatched} 条同城/同省，${model.withDeadline} 条有截止窗口）。`,
  ];
  model.items.forEach((item, index) => {
    const title = item.title.length > 40 ? `${item.title.slice(0, 39)}…` : item.title;
    lines.push(`${index + 1}. ${title}`);
  });
  lines.push(SHARE_DISCLAIMER, SHARE_SITE_LABEL);
  return lines.join('\n');
}

const FONT_STACK = '"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",system-ui,sans-serif';
const INK = '#0f172a';
const MUTED = '#64748b';
const ACCENT = '#126a9a';
const LINE = '#e2e8f0';
const PANEL = '#f8fafc';

/** Wrap by characters (CJK-safe). Returns at most `maxLines`, adding an ellipsis when truncated. */
export function wrapText(
  measure: (text: string) => number,
  text: string,
  maxWidth: number,
  maxLines: number,
): string[] {
  const lines: string[] = [];
  let current = '';
  for (const char of Array.from(text)) {
    const next = current + char;
    if (measure(next) > maxWidth && current) {
      lines.push(current);
      current = char;
      if (lines.length === maxLines) break;
    } else {
      current = next;
    }
  }
  if (lines.length < maxLines && current) lines.push(current);
  const consumed = lines.join('').length;
  if (consumed < text.length && lines.length > 0) {
    let last = lines[lines.length - 1];
    while (last.length > 1 && measure(`${last}…`) > maxWidth) last = last.slice(0, -1);
    lines[lines.length - 1] = `${last}…`;
  }
  return lines;
}

/** Paints the card. Caller owns the canvas size (SHARE_CARD_WIDTH × SHARE_CARD_HEIGHT). */
export function drawShareCard(ctx: CanvasRenderingContext2D, model: ShareCardModel): void {
  const W = SHARE_CARD_WIDTH;
  const P = 80;
  const inner = W - P * 2;
  const font = (size: number, weight = 400) => `${weight} ${size}px ${FONT_STACK}`;
  const measure = (text: string) => ctx.measureText(text).width;

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, SHARE_CARD_HEIGHT);
  ctx.fillStyle = ACCENT;
  ctx.fillRect(0, 0, W, 12);

  ctx.textBaseline = 'top';
  ctx.fillStyle = ACCENT;
  ctx.font = font(26, 700);
  ctx.fillText('衍策引擎 · 政策机会', P, 96);
  ctx.fillStyle = MUTED;
  ctx.font = font(22);
  ctx.fillText(model.generatedOn, P, 136);

  ctx.fillStyle = INK;
  ctx.font = font(56, 700);
  let y = 210;
  for (const line of wrapText(measure, model.headline, inner, 2)) {
    ctx.fillText(line, P, y);
    y += 74;
  }

  ctx.fillStyle = MUTED;
  ctx.font = font(26);
  ctx.fillText(model.subhead, P, y + 6);

  const statsY = 430;
  const stats = [
    [model.reviewable, '可优先核对'],
    [model.cityMatched, '同城/同省'],
    [model.withDeadline, '有截止窗口'],
  ] as const;
  const cellW = inner / 3;
  stats.forEach(([value, label], index) => {
    const x = P + index * cellW;
    ctx.fillStyle = PANEL;
    ctx.fillRect(x, statsY, cellW - 16, 150);
    ctx.fillStyle = ACCENT;
    ctx.font = font(60, 700);
    ctx.fillText(String(value), x + 28, statsY + 24);
    ctx.fillStyle = MUTED;
    ctx.font = font(22);
    ctx.fillText(label, x + 28, statsY + 102);
  });

  ctx.strokeStyle = LINE;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(P, 640);
  ctx.lineTo(W - P, 640);
  ctx.stroke();

  ctx.fillStyle = INK;
  ctx.font = font(28, 700);
  ctx.fillText('优先核对 TOP 3', P, 676);

  const cardH = 166;
  const gap = 18;
  let cardY = 730;
  if (model.items.length === 0) {
    ctx.fillStyle = MUTED;
    ctx.font = font(26);
    ctx.fillText('完善企业画像并重新扫描后，这里会显示可优先核对的政策。', P, cardY + 20);
  }
  model.items.forEach((item, index) => {
    ctx.fillStyle = PANEL;
    ctx.fillRect(P, cardY, inner, cardH);
    ctx.fillStyle = ACCENT;
    ctx.fillRect(P, cardY, 8, cardH);
    ctx.fillStyle = ACCENT;
    ctx.font = font(34, 700);
    ctx.fillText(String(index + 1), P + 30, cardY + 26);

    const textX = P + 90;
    const textW = inner - 120;
    ctx.fillStyle = INK;
    ctx.font = font(28, 700);
    let lineY = cardY + 22;
    for (const line of wrapText(measure, item.title, textW, 2)) {
      ctx.fillText(line, textX, lineY);
      lineY += 38;
    }
    const meta = [
      item.sameRegion ? '同城/同省' : null,
      item.authority,
      item.deadline ? `截止 ${item.deadline}` : '截止待核实',
    ]
      .filter(Boolean)
      .join(' · ');
    ctx.fillStyle = MUTED;
    ctx.font = font(22);
    for (const line of wrapText(measure, meta, textW, 1)) {
      ctx.fillText(line, textX, cardY + cardH - 44);
    }
    cardY += cardH + gap;
  });

  const footerY = 1318;
  ctx.strokeStyle = LINE;
  ctx.beginPath();
  ctx.moveTo(P, footerY);
  ctx.lineTo(W - P, footerY);
  ctx.stroke();
  ctx.fillStyle = MUTED;
  ctx.font = font(20);
  wrapText(measure, SHARE_DISCLAIMER, inner, 2).forEach((line, index) => {
    ctx.fillText(line, P, footerY + 24 + index * 30);
  });
  ctx.fillStyle = ACCENT;
  ctx.font = font(24, 700);
  ctx.textAlign = 'right';
  ctx.fillText(SHARE_SITE_LABEL, W - P, 1386);
  ctx.textAlign = 'left';
}
