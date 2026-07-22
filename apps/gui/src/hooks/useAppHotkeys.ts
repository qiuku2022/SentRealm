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
  enabled?: boolean;
};

export function useAppHotkeys({
  onToggleSettings,
  onFocusSearch,
  onEscape,
  enabled = true,
}: UseAppHotkeysOptions) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onEscape();
        return;
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
  }, [enabled, onEscape, onFocusSearch, onToggleSettings]);
}
