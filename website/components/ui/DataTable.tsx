import type { ReactNode } from "react";
import styles from "./ui.module.css";

export function DataTable({ children }: { children: ReactNode }) {
  return <div className={styles.tableScroll} role="region" aria-label="可横向滚动的数据表" tabIndex={0}>{children}</div>;
}
