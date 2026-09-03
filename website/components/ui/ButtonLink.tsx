import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./ui.module.css";

type ButtonVariant = "primary" | "secondary";

const variantClass: Record<ButtonVariant, string> = {
  primary: styles.buttonPrimary,
  secondary: styles.buttonSecondary,
};

interface ButtonLinkProps {
  children: ReactNode;
  href: string;
  variant?: ButtonVariant;
  className?: string;
}

export function ButtonLink({
  children,
  href,
  variant = "primary",
  className = "",
}: ButtonLinkProps) {
  return (
    <Link href={href} className={`${styles.buttonLink} ${variantClass[variant]} ${className}`}>
      {children}
    </Link>
  );
}
