import { useModalAnimation } from "@/hooks/useModalAnimation";

type AlertDialogProps = {
  open: boolean;
  title: string;
  message: string;
  primaryLabel?: string;
  secondaryLabel?: string;
  onPrimary: () => void;
  onSecondary?: () => void;
};

export function AlertDialog({
  open,
  title,
  message,
  primaryLabel = "知道了",
  secondaryLabel,
  onPrimary,
  onSecondary,
}: AlertDialogProps) {
  const { present, active, handleScrimTransitionEnd } = useModalAnimation(open);

  if (!present) return null;

  return (
    <>
      <div
        className={`shell-scrim shell-scrim-modal ${active ? "is-open" : ""}`}
        aria-hidden="true"
        onTransitionEnd={handleScrimTransitionEnd}
      />
      <div
        className={`shell-dialog shell-dialog-modal ${active ? "is-open" : ""}`}
        role="alertdialog"
        aria-labelledby="shell-alert-title"
        aria-describedby="shell-alert-desc"
      >
        <div className="shell-dialog-head">
          <strong id="shell-alert-title">{title}</strong>
        </div>
        <p id="shell-alert-desc" className="shell-dialog-body">
          {message}
        </p>
        <div className="shell-dialog-foot">
          {secondaryLabel && onSecondary ? (
            <button
              type="button"
              className="shell-btn-secondary"
              onClick={onSecondary}
            >
              {secondaryLabel}
            </button>
          ) : null}
          <button type="button" className="shell-btn-go" onClick={onPrimary}>
            {primaryLabel}
          </button>
        </div>
      </div>
    </>
  );
}
