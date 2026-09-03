import type { ReactNode } from "react";
import styles from "./ui.module.css";

export function InlineAlert({
  children,
  tone = "error",
}: {
  children: ReactNode;
  tone?: "error" | "info";
}) {
  return (
    <div
      className={`${styles.alert} ${tone === "error" ? styles.alertError : styles.alertInfo}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <span aria-hidden="true">{tone === "error" ? "!" : "i"}</span>
      <span>{children}</span>
    </div>
  );
}
