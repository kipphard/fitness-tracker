import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrowserMultiFormatReader, type IScannerControls } from "@zxing/browser";

// Live camera barcode scanner. Decodes EAN/UPC barcodes from the rear camera and returns the
// digits, which the diary then looks up via /api/food/barcode/{code}.
export function BarcodeScanner({
  onScan,
  onClose,
}: {
  onScan: (code: string) => void;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const videoRef = useRef<HTMLVideoElement>(null);
  const onScanRef = useRef(onScan);
  onScanRef.current = onScan;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let controls: IScannerControls | null = null;
    let cancelled = false;
    const reader = new BrowserMultiFormatReader();

    reader
      .decodeFromConstraints(
        { video: { facingMode: "environment" } },
        videoRef.current!,
        (result, _err, ctrl) => {
          controls = ctrl;
          if (cancelled) {
            ctrl.stop();
            return;
          }
          if (result) {
            ctrl.stop();
            onScanRef.current(result.getText());
          }
        },
      )
      .then((c) => {
        controls = c;
        if (cancelled) c.stop();
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));

    return () => {
      cancelled = true;
      controls?.stop();
    };
  }, []);

  return (
    <div className="scanner-overlay" role="dialog" aria-modal="true">
      <div className="scanner">
        <video ref={videoRef} className="scanner__video" muted playsInline />
        <div className="scanner__hint">
          {error ? <span className="error">{error}</span> : t("diary.scanHint")}
        </div>
        <button className="btn btn--ghost" onClick={onClose}>
          {t("diary.cancel")}
        </button>
      </div>
    </div>
  );
}
