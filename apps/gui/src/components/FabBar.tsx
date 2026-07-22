import {
  ChevronDownIcon,
  LoaderCircleIcon,
  MonitorIcon,
  Settings2Icon,
  SlidersHorizontalIcon,
  SmartphoneIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { flowLabel } from "@/components/SettingsDrawer";
import type { FlowState, Settings } from "@/lib/types";

type FabBarProps = {
  flowState: FlowState;
  processing: boolean;
  processingLabel?: string;
  canProcess: boolean;
  settings: Settings | null;
  presetLabel: string;
  lastDurationMs: number | null;
  elapsedMs: number;
  presetMenuOpen: boolean;
  onPresetMenuOpenChange: (open: boolean) => void;
  onOpenRules: () => void;
  onOpenSettings: () => void;
  onPresetSelect: (preset: Settings["preset"]) => void;
  onProcess: () => void;
};

function formatDuration(ms: number): string {
  return `${(ms / 1000).toFixed(1)}s`;
}

function statusSubline(
  flowState: FlowState,
  lastDurationMs: number | null,
  elapsedMs: number,
): string {
  switch (flowState) {
    case "new":
      return "粘贴或导入后开始";
    case "ready":
      return "本地处理 · 约数秒";
    case "running":
      return `本地处理 · ${formatDuration(elapsedMs)}`;
    case "done":
      return lastDurationMs != null
        ? `本地处理 · ${formatDuration(lastDurationMs)}`
        : "本地处理";
    case "error":
      return "请查看上方提示或检查后端";
    default:
      return "";
  }
}

export function FabBar({
  flowState,
  processing,
  processingLabel,
  canProcess,
  settings,
  presetLabel,
  lastDurationMs,
  elapsedMs,
  presetMenuOpen,
  onPresetMenuOpenChange,
  onOpenRules,
  onOpenSettings,
  onPresetSelect,
  onProcess,
}: FabBarProps) {
  const popRef = useRef<HTMLDivElement>(null);
  const [menuPresent, setMenuPresent] = useState(false);
  const [menuActive, setMenuActive] = useState(false);

  useEffect(() => {
    if (presetMenuOpen) {
      setMenuPresent(true);
      const frame = requestAnimationFrame(() => {
        requestAnimationFrame(() => setMenuActive(true));
      });
      return () => cancelAnimationFrame(frame);
    }
    setMenuActive(false);
  }, [presetMenuOpen]);

  useEffect(() => {
    if (!presetMenuOpen) return;
    const onDocClick = (event: MouseEvent) => {
      if (!popRef.current?.contains(event.target as Node)) {
        onPresetMenuOpenChange(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [onPresetMenuOpenChange, presetMenuOpen]);

  const processLabel =
    flowState === "done" && !processing
      ? "重新处理"
      : processing
        ? (processingLabel ?? "处理中")
        : "处理文稿";

  const PresetIcon =
    settings?.preset === "portrait"
      ? SmartphoneIcon
      : settings?.preset === "custom"
        ? SlidersHorizontalIcon
        : MonitorIcon;

  return (
    <div className="shell-fab">
      <div className="shell-fab-side" ref={popRef}>
        <button
          type="button"
          className="shell-fab-ic"
          title="参数设置"
          onClick={onOpenSettings}
        >
          <Settings2Icon className="size-4" strokeWidth={1.5} />
        </button>
        <div className="shell-preset-wrap">
          <button
            type="button"
            className={`shell-chip-toggle ${menuActive ? "is-open" : ""}`}
            disabled={processing || flowState === "error"}
            aria-expanded={menuActive}
            title="选择横竖屏与字数"
            onClick={() => onPresetMenuOpenChange(!presetMenuOpen)}
          >
            <span className="shell-chip-toggle-icon">
              <span
                key={settings?.preset ?? "none"}
                className="shell-chip-toggle-icon-inner"
              >
                <PresetIcon className="size-3 shrink-0 opacity-80" strokeWidth={1.6} />
              </span>
            </span>
            <span
              key={`label-${settings?.preset ?? "none"}`}
              className="shell-chip-toggle-label"
            >
              {presetLabel || "预设"}
            </span>
            <ChevronDownIcon
              className="shell-chip-toggle-chevron size-3 shrink-0 opacity-70"
              strokeWidth={1.6}
            />
          </button>
          {menuPresent && (
            <div
              className={`shell-preset-pop ${menuActive ? "is-open" : ""}`}
              role="menu"
              onTransitionEnd={(event) => {
                if (event.target !== event.currentTarget) return;
                if (!menuActive && event.propertyName === "opacity") {
                  setMenuPresent(false);
                }
              }}
            >
              {(
                [
                  ["landscape", "横屏 · 15 字"],
                  ["portrait", "竖屏 · 10 字"],
                  ["custom", "自定义…"],
                ] as const
              ).map(([preset, label]) => (
                <button
                  key={preset}
                  type="button"
                  role="menuitem"
                  className={settings?.preset === preset ? "is-active" : undefined}
                  onClick={() => {
                    onPresetSelect(preset);
                    onPresetMenuOpenChange(false);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="shell-fab-status">
        <span className="shell-fab-status-main">{flowLabel(flowState)}</span>
        <span className="shell-fab-status-sub">
          {statusSubline(flowState, lastDurationMs, elapsedMs)}
        </span>
      </div>

      <button
        type="button"
        className="shell-fab-action"
        disabled={processing || flowState === "error"}
        onClick={onOpenRules}
      >
        编辑规则
      </button>

      <button
        type="button"
        className={`shell-btn-go ${processing ? "is-running" : ""}`}
        disabled={!canProcess}
        onClick={onProcess}
      >
        {processing ? (
          <>
            <LoaderCircleIcon className="size-4 animate-spin inline" /> {processLabel}
          </>
        ) : (
          processLabel
        )}
      </button>
    </div>
  );
}
