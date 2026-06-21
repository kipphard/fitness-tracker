import type { ReactNode } from "react";

export function Card({
  title,
  action,
  className,
  children,
}: {
  title?: string;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={"card " + (className ?? "")}>
      {(title || action) && (
        <header className="card__head">
          {title && <h2>{title}</h2>}
          {action && <div className="card__actions">{action}</div>}
        </header>
      )}
      <div className="card__body">{children}</div>
    </section>
  );
}
