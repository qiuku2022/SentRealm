import { useModalAnimation } from "@/hooks/useModalAnimation";

type ExportDialogProps = {
  open: boolean;
  onExportToDocumentDir: () => void;
  onExportCustom: () => void;
  onCancel: () => void;
  busy?: boolean;
};

export function ExportDialog({
  open,
  onExportToDocumentDir,
  onExportCustom,
  onCancel,
  busy = false,
}: ExportDialogProps) {
  const { present, active, handleScrimTransitionEnd } = useModalAnimation(open);

  if (!present) return null;

  return (
    <>
      <div
        className={`shell-scrim shell-scrim-modal ${active ? "is-open" : ""}`}
        onClick={busy ? undefined : onCancel}
        aria-hidden="true"
        onTransitionEnd={handleScrimTransitionEnd}
      />
      <div
        className={`shell-dialog shell-dialog-modal ${active ? "is-open" : ""}`}
        role="dialog"
        aria-labelledby="shell-export-title"
        aria-describedby="shell-export-desc"
      >
        <div className="shell-dialog-head">
          <strong id="shell-export-title">导出 .txt</strong>
        </div>
        <p id="shell-export-desc" className="shell-dialog-body">
          默认写入当前文稿目录；也可另选保存位置。
        </p>
        <div className="shell-dialog-foot">
          <button
            type="button"
            className="shell-btn-secondary"
            disabled={busy}
            onClick={onCancel}
          >
            取消
          </button>
          <button
            type="button"
            className="shell-btn-secondary"
            disabled={busy}
            onClick={onExportCustom}
          >
            选择其他位置…
          </button>
          <button
            type="button"
            className="shell-btn-go"
            disabled={busy}
            onClick={onExportToDocumentDir}
          >
            导出到文稿目录
          </button>
        </div>
      </div>
    </>
  );
}
