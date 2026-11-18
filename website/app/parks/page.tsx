import type { Metadata } from "next";
import { SolutionView } from "@/components/marketing/SolutionView";
import { getSolution } from "@/lib/solutions";

export const metadata: Metadata = {
  title: "园区与孵化器 | 衍策引擎 AI",
  description: "园区和孵化器使用同一套企业档案、政策检索、资格核对和项目记录服务入驻企业。不承诺入驻、补贴或满意度。",
};

export default function ParksPage() {
  const item = getSolution("parks");
  if (!item) return null;
  return <SolutionView item={item} />;
}
