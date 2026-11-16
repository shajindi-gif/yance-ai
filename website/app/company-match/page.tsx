import { ProductOverview } from '@/components/ProductOverview';
export const metadata = {title:'企业资料与政策匹配 | 衍策引擎AI',description:'从客户提供的企业事实出发，检索政策并逐条核对资格条件、来源与缺口。'};
export default function CompanyMatchPage() {
  return <ProductOverview label="企业资料 / 政策机会" title="从企业事实，找到有依据的政策机会。" description="先确认企业资料，再查看政策来源、申报条件与证据缺口。匹配分数用于辅助筛选，不是获批概率。" sections={[
    {title:'确认企业资料与版本',description:'录入企业主体、地域、经营与研发情况，补充证明材料。画像确认是客户自述确认，不替代第三方鉴证。',href:'/companies',action:'查看企业档案'},
    {title:'检索政策与申报窗口',description:'查看现有政策目录与原文来源。政策有效期和当期申报截止时间分别核对；来源缺失或时效不明时继续标注。',href:'/discover',action:'查找政策'},
    {title:'逐条核对资格与缺口',description:'对照硬条件、企业事实与原文引用，区分条件满足、不满足、证据不足和需复核，再决定是否推进项目。',href:'/opportunities',action:'查看政策机会'},
    {title:'把机会转成项目',description:'在申报工作台整理材料、补证与版本记录。园区及其他资源的可用性、费用和对接条件须另行核实。',href:'/applications',action:'进入申报工作台'},
  ]} />;
}
