import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import SmartAgent from "@/components/SmartAgent";
import SiteChrome from "@/components/SiteChrome";

export const metadata: Metadata = {
  metadataBase: new URL('https://yance.ai'),
  title: "衍策引擎AI — 企业政策匹配、申报辅助与产业研究平台",
  description:
    "根据企业所在地区、行业与经营情况，查找可能适用的扶持政策，核对申报条件，整理所需材料，生成可追溯的初筛报告。",
  keywords:
    "新质生产力, 政策申报, 产业研究, AI 企业, 高新技术企业, 专精特新, 政策匹配, 补贴申报, 园区入驻, 科技企业服务, 衍策引擎AI",
  icons: {
    icon: '/favicon.png',
  },
  openGraph: {
    title: "衍策引擎AI — 企业政策匹配、申报辅助与产业研究平台",
    description: "帮助科技企业更快找到政策、资金、资源和增长路径。",
    url: "https://yance.ai",
    siteName: "衍策引擎AI",
    locale: "zh_CN",
    type: "website",
    images: [
      {
        url: '/logo.png',
        width: 1254,
        height: 1254,
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
