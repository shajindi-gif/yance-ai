import type { Metadata } from 'next';
import DemoExperience from './DemoExperience';

export const metadata: Metadata = {
  title: 'Investor Demo | Yance.ai',
  description: '使用明确标注的合成数据，体验企业画像到申报文件的完整 Yance.ai 工作流。',
};

export default function DemoPage() { return <DemoExperience />; }
