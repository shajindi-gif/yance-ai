"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { isWorkspaceRoute } from "@/lib/navigation";

interface SiteChromeProps {
  children: ReactNode;
  marketingHeader: ReactNode;
  marketingFooter: ReactNode;
}

export default function SiteChrome({
  children,
  marketingHeader,
  marketingFooter,
}: SiteChromeProps) {
  const pathname = usePathname();

  if (isWorkspaceRoute(pathname)) {
    return children;
  }

  return (
    <>
      {marketingHeader}
      <main id="main-content">{children}</main>
      {marketingFooter}
    </>
  );
}
