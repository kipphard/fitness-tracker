import type { ReactNode } from "react";

import { ProgressBar } from "./ProgressBar";

// Full-screen onboarding scaffold: top bar (back + progress), scrollable body,
// and a pinned bottom footer (the CTA). `progress` is a 0..1 fraction.
export function WizardShell({
  progress,
  onBack,
  children,
  footer,
}: {
  progress: number;
  onBack?: () => void;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="wizard">
      <div className="wizard__top">
        {onBack ? (
          <button className="icon-btn wizard__back" onClick={onBack} aria-label="Back">
            ‹
          </button>
        ) : (
          <span className="wizard__back-spacer" />
        )}
        <ProgressBar value={progress} />
      </div>
      <div className="wizard__body">{children}</div>
      {footer != null && <div className="wizard__footer">{footer}</div>}
    </div>
  );
}
