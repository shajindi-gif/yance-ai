import type { ReactNode } from "react";
import { Surface } from "./Surface";
import styles from "./ui.module.css";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon = "—", action }: EmptyStateProps) {
  return (
    <Surface className={styles.emptyState}>
      <div className={styles.emptyStateInner}>
        <span className={styles.emptyIcon} aria-hidden="true">
          {icon}
        </span>
        <h2>{title}</h2>
        <p>{description}</p>
        {action}
      </div>
    </Surface>
  );
}
