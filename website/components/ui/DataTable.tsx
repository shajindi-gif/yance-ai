import type { ReactNode } from "react";
import styles from "./ui.module.css";

export function DataTable({ children }: { children: ReactNode }) {
  return <div className={styles.tableScroll}>{children}</div>;
}
