import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import SmartAgent from "@/components/SmartAgent";

export const metadata: Metadata = {
  metadataBase: new URL('https://yance.ai'),
  title: "衍策引擎AI — 中国新质生产力企业的 AI 产业研究与政策申报平台",
  description:
    "衍策引擎AI 帮助科技企业完成产业研究、政策匹配、补贴申报、园区入驻、项目材料生成和企业成长规划，让企业更快找到政策、资金、资源和增长路径。",
  keywords:
    "新质生产力, 政策申报, 产业研究, AI 企业, 高新技术企业, 专精特新, 政策匹配, 补贴申报, 园区入驻, 科技企业服务, 衍策引擎AI",
  icons: {
    icon: '/favicon.png',
  },
  openGraph: {
    title: "衍策引擎AI — 中国新质生产力企业的 AI 产业研究与政策申报平台",
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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <a href="#main-content" className="skip-link">
          跳转到主要内容
        </a>
        <Header />
        <main id="main-content">{children}</main>
        <Footer />
        <SmartAgent />
      </body>
    </html>
  );
}
