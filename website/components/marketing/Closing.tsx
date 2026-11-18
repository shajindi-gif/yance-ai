import Link from "next/link";
import type { ReactNode } from "react";
import styles from "./Closing.module.css";

type Action = { href: string; label: string };

function ActionLink({ action, primary }: { action: Action; primary?: boolean }) {
  const className = primary ? "btn btn-primary" : styles.textLink;
  if (action.href.startsWith("/")) {
    return <Link href={action.href} className={className}>{action.label}</Link>;
  }
  return <a href={action.href} className={className}>{action.label}</a>;
}

export function Closing({
  eyebrow = "下一步",
  title,
  primary,
  links = [],
}: {
  eyebrow?: string;
  title: ReactNode;
  primary: Action;
  links?: Action[];
}) {
  return (
    <section className={styles.closing}>
      <span className={styles.eyebrow}>{eyebrow}</span>
      <h2>{title}</h2>
      <div className={styles.actions}>
        <ActionLink action={primary} primary />
        {links.map((action) => <ActionLink key={action.label} action={action} />)}
      </div>
    </section>
  );
}
