import type { Metadata } from "next";
import "./globals.css";
import "./design-system.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import SmartAgent from "@/components/SmartAgent";
import SiteChrome from "@/components/SiteChrome";

export const metadata: Metadata = {
  metadataBase: new URL('https://yance.ai'),
  title: "衍策引擎AI — 企业政策与资源证据工作台",
  description:
    "重点服务新质生产力与科技企业，也面向各类有政策需求的企业。根据地域、行业与经营情况，查找可能适用的政策，核对申报条件，整理所需材料，生成可追溯的初筛报告。",
  keywords:
    "新质生产力, 政策申报, 产业研究, AI 企业, 高新技术企业, 专精特新, 政策匹配, 补贴申报, 园区入驻, 科技企业服务, 衍策引擎AI",
  icons: {
    icon: '/favicon.png',
  },
  openGraph: {
    title: "衍策引擎AI — 企业政策与资源证据工作台",
    description: "聚焦新质生产力与科技企业，也帮助各类有政策需求的企业查找机会、核对条件与准备材料。",
    url: "https://yance.ai",
    siteName: "衍策引擎AI",
    locale: "zh_CN",
    type: "website",
    images: [
      {
        url: '/og-brand.png',
        width: 1200,
        height: 630,
        alt: '衍策引擎AI',
      },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" data-scroll-behavior="smooth">
      <body>
        <a href="#main-content" className="skip-link">
          跳转到主要内容
        </a>
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
          "@context": "https://schema.org", "@type": "Organization",
          name: "上海衍策引擎人工智能科技有限公司", url: "https://yance.ai",
          logo: "https://yance.ai/logo.png",
        }) }} />
        <SiteChrome
          marketingHeader={<Header />}
          marketingFooter={
            <>
              <Footer />
              <SmartAgent />
            </>
          }
        >
          {children}
        </SiteChrome>
      </body>
    </html>
  );
}
