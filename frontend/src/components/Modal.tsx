import { useEffect } from "react";
import type { ReactNode } from "react";

// A reusable overlay: a bottom sheet on mobile, a centered dialog on desktop. Closes on Esc,
// on backdrop click, and via the header ✕. Pass `bare` to drop the header when the child
// already provides its own (e.g. SuggestPanel / PhotoEstimatePanel render their own Card).
export function Modal({
  title,
  onClose,
  children,
  footer,
  bare = false,
}: {
  title?: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  bare?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden"; // lock background scroll while open
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className="modal" onClick={onClose}>
      <div className="modal__panel" onClick={(e) => e.stopPropagation()}>
        {!bare && (
          <div className="modal__head">
            <strong className="modal__title">{title}</strong>
            <button className="icon-btn" onClick={onClose} aria-label="close">
              ✕
            </button>
          </div>
        )}
        <div className={bare ? "modal__body modal__body--bare" : "modal__body"}>{children}</div>
        {footer && <div className="modal__footer">{footer}</div>}
      </div>
    </div>
  );
}
