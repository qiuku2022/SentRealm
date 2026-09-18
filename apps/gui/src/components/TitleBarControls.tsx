import { MinusIcon, SquareIcon, XIcon } from "lucide-react";
import { useCallback } from "react";

import { isTauriRuntime } from "@/lib/export-file";

async function withAppWindow(
  action: (win: {
    minimize: () => Promise<void>;
    toggleMaximize: () => Promise<void>;
    close: () => Promise<void>;
  }) => Promise<void>,
): Promise<void> {
  if (!isTauriRuntime()) return;
  const { getCurrentWindow } = await import("@tauri-apps/api/window");
  await action(getCurrentWindow());
}

/** Native-decoration substitute: minimize / maximize / close for undecorated window. */
export function TitleBarControls() {
  const onMinimize = useCallback(() => {
    void withAppWindow((w) => w.minimize());
  }, []);
  const onMaximize = useCallback(() => {
    void withAppWindow((w) => w.toggleMaximize());
  }, []);
  const onClose = useCallback(() => {
    void withAppWindow((w) => w.close());
  }, []);

  if (!isTauriRuntime()) return null;

  return (
    <div className="shell-win-controls">
      <button
        type="button"
        className="shell-win-btn"
        aria-label="最小化"
        onClick={onMinimize}
      >
        <MinusIcon />
      </button>
      <button
        type="button"
        className="shell-win-btn"
        aria-label="最大化"
        onClick={onMaximize}
      >
        <SquareIcon />
      </button>
      <button
        type="button"
        className="shell-win-btn is-close"
        aria-label="关闭"
        onClick={onClose}
      >
        <XIcon />
      </button>
    </div>
  );
}
