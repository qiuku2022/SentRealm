import { useEffect } from "react";

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "TEXTAREA" || tag === "INPUT" || tag === "SELECT") return true;
  return target.isContentEditable;
}

type UseAppHotkeysOptions = {
  onToggleSettings: () => void;
  onFocusSearch: () => void;
  onEscape: () => void;
  onProcess?: () => void;
  onCopyResult?: () => void;
  onCreateDocument?: () => void;
  onImportTxt?: () => void;
  enabled?: boolean;
};

export function useAppHotkeys({
  onToggleSettings,
  onFocusSearch,
  onEscape,
  onProcess,
  onCopyResult,
  onCreateDocument,
  onImportTxt,
  enabled = true,
}: UseAppHotkeysOptions) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onEscape();
        return;
      }

      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        if (onProcess) {
          event.preventDefault();
          onProcess();
          return;
        }
      }

      if (
        (event.ctrlKey || event.metaKey) &&
        event.shiftKey &&
        (event.key === "c" || event.key === "C")
      ) {
        if (onCopyResult) {
          event.preventDefault();
          onCopyResult();
          return;
        }
      }

      if (
        (event.ctrlKey || event.metaKey) &&
        !event.shiftKey &&
        (event.key === "n" || event.key === "N")
      ) {
        if (onCreateDocument) {
          event.preventDefault();
          onCreateDocument();
          return;
        }
      }

      if (
        (event.ctrlKey || event.metaKey) &&
        !event.shiftKey &&
        (event.key === "o" || event.key === "O")
      ) {
        if (onImportTxt) {
          event.preventDefault();
          onImportTxt();
          return;
        }
      }

      if ((event.ctrlKey || event.metaKey) && event.key === ",") {
        event.preventDefault();
        onToggleSettings();
        return;
      }

      if (event.key === "/" && !isEditableTarget(event.target)) {
        event.preventDefault();
        onFocusSearch();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    enabled,
    onCopyResult,
    onCreateDocument,
    onEscape,
    onFocusSearch,
    onImportTxt,
    onProcess,
    onToggleSettings,
  ]);
}
