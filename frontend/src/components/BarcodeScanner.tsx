import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { BrowserMultiFormatReader, type IScannerControls } from "@zxing/browser";
import { BarcodeFormat, DecodeHintType } from "@zxing/library";

// Restrict the decoder to retail product barcodes and try harder per frame. The default
// multi-format reader scans every 1D/2D symbology each frame, which is slow and unreliable
// on a live video feed — locking it to EAN/UPC/Code128 makes it lock on quickly.
const hints = new Map<DecodeHintType, unknown>();
hints.set(DecodeHintType.POSSIBLE_FORMATS, [
  BarcodeFormat.EAN_13,
  BarcodeFormat.EAN_8,
  BarcodeFormat.UPC_A,
  BarcodeFormat.UPC_E,
  BarcodeFormat.CODE_128,
]);
hints.set(DecodeHintType.TRY_HARDER, true);

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
    const reader = new BrowserMultiFormatReader(hints, { delayBetweenScanAttempts: 150 });

    reader
      .decodeFromConstraints(
        {
          video: {
            facingMode: "environment",
            // Higher resolution so small barcodes have enough pixels to decode.
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        },
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
        <div className="scanner__frame">
          <video ref={videoRef} className="scanner__video" muted playsInline />
          <div className="scanner__reticle" aria-hidden="true" />
        </div>
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
