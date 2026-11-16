import type { ProductCatalogItem } from './api';

// Display copy only. The API owns prices, order amounts and entitlement decisions.
const copy: Record<string, { name: string; unit: string; features: string[]; boundary: string }> = {
  FREE_POLICY_MATCH: { name: '免费体验', unit: '', features: ['确认企业资料，开始政策初筛', '在现有账户配额内查看机会与来源', '查看缺失资料与下一步'], boundary: '匹配度用于初筛，不是获批概率。具体额度以账户权益为准。' },
  POLICY_REPORT: { name: '企业政策机会简报', unit: '/ 份', features: ['围绕所选企业查看政策机会汇总', '核对来源、相关条件与缺失信息', '购买前确认报告范围及下载方式'], boundary: '报告辅助准备与判断；政策窗口和企业事实仍需客户核对。' },
  POLICY_DIAGNOSIS: { name: '单项政策条件核对包', unit: '/ 项目', features: ['目标：逐项对照条件与企业事实', '目标：列出支持条款与补证清单', '独立交付及付费链路仍待验收'], boundary: '待开通。目录金额不代表该交付已验收；不承诺衍策提供人工业务审核。' },
  APPLICATION_PLAN: { name: '申报材料工作稿包', unit: '/ 项目', features: ['目标：基于已支持模板整理工作稿', '目标：关联材料目录与证据索引', '模板深度及版本交付仍待验收'], boundary: '待开通。不包含官方提交、证明文件代造或获批保证。' },
};
export function productPresentation(product: ProductCatalogItem) {
  return copy[product.code] ?? { name: product.name, unit: '/ 项', features: ['交付范围与购买条件待核对'], boundary: '请先核对该产品的实际交付范围。' };
}
