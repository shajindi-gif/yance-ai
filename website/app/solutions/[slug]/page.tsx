import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SolutionView } from "@/components/marketing/SolutionView";
import { SOLUTIONS, getSolution } from "@/lib/solutions";

export function generateStaticParams() {
  return SOLUTIONS.map((item) => ({ slug: item.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const item = getSolution(slug);
  if (!item) return { title: "行业方案 | 衍策引擎 AI" };
  return {
    title: `${item.title} | 衍策引擎 AI`,
    description: item.summary,
  };
}

export default async function SolutionPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = getSolution(slug);
  if (!item) notFound();
  return <SolutionView item={item} />;
}
