import styles from "./ui.module.css";

export function LoadingState({ label = "正在加载工作区" }: { label?: string }) {
  return (
    <div className={styles.loadingState} role="status" aria-label={label}>
      <div className={styles.loadingCard}>
        <span className={styles.skeleton} style={{ width: "38%" }} />
        <span className={styles.skeleton} style={{ width: "82%" }} />
        <span className={styles.skeleton} style={{ width: "64%" }} />
      </div>
    </div>
  );
}
