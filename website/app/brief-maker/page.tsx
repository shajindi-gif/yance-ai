import { ProductOverview } from '@/components/ProductOverview';
export const metadata = {title:'材料起草与客户复核 | 衍策引擎AI',description:'在项目内准备证据型工作稿、比较版本、处理评论建议，由客户自行复核后按权限导出。'};
export default function BriefMakerPage() {
  return <ProductOverview label="材料 / 版本 / 复核" title="把依据带入材料，把修改留在版本里。" description="在项目内整理材料要求、起草工作稿、比较修改与处理协作意见，由客户本人或授权团队完成复核。" sections={[
    {title:'先整理材料与证据',description:'查看项目材料清单、资料关联和未解决的证据缺口。上传或关联资料不表示内容已经解析或核验。',href:'/documents',action:'查看企业资料库'},
    {title:'起草并保留工作稿',description:'使用现有证据生成工作稿；重新生成和人工编辑创建新版本。实际可用格式和下载权限由服务端校验。',href:'/applications',action:'打开项目工作台'},
    {title:'比较版本与处理建议',description:'查看版本差异、来源变化与关联版本的评论。接受摘要建议生成新稿，仍需客户复核。',href:'/applications',action:'查看材料工作稿'},
    {title:'客户复核与授权导出',description:'由有权限的客户成员核对具体版本。证据变化或缺少必要条件时，保留复核及导出限制。下载不表示已经对外申报。',href:'/reports',action:'查看已授权报告'},
  ]} />;
}
