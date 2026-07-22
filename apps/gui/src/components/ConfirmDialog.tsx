import { useModalAnimation } from "@/hooks/useModalAnimation";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "删除",
  cancelLabel = "取消",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { present, active, handleScrimTransitionEnd } = useModalAnimation(open);

  if (!present) return null;

  return (
    <>
      <div
        className={`shell-scrim shell-scrim-modal ${active ? "is-open" : ""}`}
        onClick={onCancel}
        aria-hidden="true"
        onTransitionEnd={handleScrimTransitionEnd}
      />
      <div
        className={`shell-dialog shell-dialog-modal ${active ? "is-open" : ""}`}
        role="alertdialog"
        aria-labelledby="shell-dialog-title"
        aria-describedby="shell-dialog-desc"
      >
        <div className="shell-dialog-head">
          <strong id="shell-dialog-title">{title}</strong>
        </div>
        <p id="shell-dialog-desc" className="shell-dialog-body">
          {message}
        </p>
        <div className="shell-dialog-foot">
          <button type="button" className="shell-btn-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button type="button" className="shell-btn-danger" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </>
  );
}
