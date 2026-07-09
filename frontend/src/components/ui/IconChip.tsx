import type { ReactNode } from "react";

// Round emoji/icon chip (meal rows, list items).
export function IconChip({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <span className={"icon-chip" + (className ? ` ${className}` : "")}>{children}</span>;
}
