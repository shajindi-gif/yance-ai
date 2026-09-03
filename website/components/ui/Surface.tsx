import type { HTMLAttributes } from "react";
import styles from "./ui.module.css";

interface SurfaceProps extends HTMLAttributes<HTMLDivElement> {
  padded?: boolean;
}

export function Surface({ padded = true, className = "", ...props }: SurfaceProps) {
  return (
    <div
      className={`${styles.surface} ${padded ? styles.surfacePadded : ""} ${className}`}
      {...props}
    />
  );
}
