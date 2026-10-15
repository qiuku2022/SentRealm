import {
  ChevronDownIcon,
  ChevronUpIcon,
  CopyIcon,
  DownloadIcon,
  PanelRightCloseIcon,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { countLineChars, formatLineNumber } from "@/lib/text-utils";
import type { FlowState, PreprocessResult } from "@/lib/types";

type ResultPanelProps = {
  result: PreprocessResult | null;
  flowState: FlowState;
  streaming?: boolean;
  copied: boolean;
  isStale?: boolean;
  activeLineIndex?: number | null;
  onLineClick?: (index: number) => void;
  onCopy: () => void;
  onExport?: () => void;
  onToggleFold?: () => void;
  showFold?: boolean;
};

export function ResultPanel({
  result,
  flowState,
  streaming = false,
  copied,
  isStale = false,
  activeLineIndex = null,
  onLineClick,
  onCopy,
  onExport,
  onToggleFold,
  showFold = false,
}: ResultPanelProps) {
  const lines = result?.processed.split("\n") ?? [];
  const flaggedLines = result?.flagged_lines ?? [];
  const flaggedSet = new Set(flaggedLines);
  const listEndRef = useRef<HTMLDivElement>(null);
  const [flaggedCursor, setFlaggedCursor] = useState<number | null>(null);

  useEffect(() => {
    setFlaggedCursor(null);
  }, [result?.processed]);

  useEffect(() => {
    if (!streaming || !result?.processed) return;
    listEndRef.current?.scrollIntoView({ block: "end" });
  }, [result?.processed, streaming]);

  const jumpToNextFlagged = () => {
    if (flaggedLines.length === 0) return;
    const nextCursor =
      flaggedCursor === null || flaggedCursor >= flaggedLines.length - 1
        ? 0
        : flaggedCursor + 1;
    setFlaggedCursor(nextCursor);
    const targetLineIndex = flaggedLines[nextCursor];
    const el = document.getElementById(`result-line-${targetLineIndex}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    onLineClick?.(targetLineIndex);
  };

  const jumpToPrevFlagged = () => {
    if (flaggedLines.length === 0) return;
    const prevCursor =
      flaggedCursor === null || flaggedCursor <= 0
        ? flaggedLines.length - 1
        : flaggedCursor - 1;
    setFlaggedCursor(prevCursor);
    const targetLineIndex = flaggedLines[prevCursor];
    const el = document.getElementById(`result-line-${targetLineIndex}`);
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
    onLineClick?.(targetLineIndex);
  };

  const emptyMessage =
    flowState === "error"
      ? "本轮未产生结果。请查看上方提示后重试。"
      : streaming
        ? "正在生成断句结果…"
        : "处理完成后，分行结果会显示在这里。超长行将以橙色标记。";

  return (
    <>
      <div className="shell-right-head">
        <div className="shell-right-title">
          处理结果
          {isStale && (
            <span className="shell-right-stale-tag" title="原文已变动，需重新处理">
              待刷新
            </span>
          )}
          {streaming && (
            <span className="shell-right-live">更新中</span>
          )}
        </div>
        <div className="shell-right-head-actions">
          {flaggedLines.length > 0 && (
            <div className="shell-flagged-nav" title="超长行快速巡检">
              <button
                type="button"
                className="shell-flagged-btn"
                title="上一处超长行"
                aria-label="上一处超长行"
                onClick={jumpToPrevFlagged}
              >
                <ChevronUpIcon className="size-3" />
              </button>
              <span className="shell-flagged-nav-count">
                {flaggedCursor !== null
                  ? `${flaggedCursor + 1}/${flaggedLines.length}`
                  : `${flaggedLines.length}超长`}
              </span>
              <button
                type="button"
                className="shell-flagged-btn"
                title="下一处超长行"
                aria-label="下一处超长行"
                onClick={jumpToNextFlagged}
              >
                <ChevronDownIcon className="size-3" />
              </button>
            </div>
          )}
          {showFold && onToggleFold && (
            <button
              type="button"
              className="shell-icon-btn"
              title="收起结果栏"
              onClick={onToggleFold}
            >
              <PanelRightCloseIcon />
            </button>
          )}
          <button
            type="button"
            className="shell-icon-btn"
            title="导出 .txt"
            disabled={!result?.processed || streaming || !onExport}
            onClick={() => onExport?.()}
          >
            <DownloadIcon />
          </button>
        </div>
      </div>

      <div className="shell-right-body">
        {!result ? (
          <div className="shell-right-empty">
            <p>{emptyMessage}</p>
          </div>
        ) : (
          <div className={`shell-results-list ${isStale ? "is-stale" : ""}`}>
            {lines.map((line, index) => {
              const isLong = flaggedSet.has(index);
              const isActive = activeLineIndex === index;
              const clickable = Boolean(onLineClick && line);
              return (
                <div
                  key={`${index}-${line.slice(0, 12)}`}
                  id={`result-line-${index}`}
                  className={[
                    "shell-result-line",
                    isLong ? "is-long" : "",
                    clickable ? "is-clickable" : "",
                    isActive ? "is-active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  role={clickable ? "button" : undefined}
                  tabIndex={clickable ? 0 : undefined}
                  aria-label={
                    clickable
                      ? `定位原文第 ${index + 1} 行`
                      : undefined
                  }
                  onClick={
                    clickable
                      ? () => {
                          onLineClick?.(index);
                        }
                      : undefined
                  }
                  onKeyDown={
                    clickable
                      ? (event) => {
                          if (event.key === "Enter" || event.key === " ") {
                            event.preventDefault();
                            onLineClick?.(index);
                          }
                        }
                      : undefined
                  }
                >
                  <span className="shell-result-num">{formatLineNumber(index)}</span>
                  <span className="shell-result-body">
                    {line}
                    {isLong && (
                      <span className="shell-result-tag">
                        超长 · 复制前请检查
                      </span>
                    )}
                  </span>
                  <span className="shell-result-ct">{countLineChars(line)}字</span>
                </div>
              );
            })}
            <div ref={listEndRef} />
          </div>
        )}
      </div>

      <div className="shell-right-foot">
        <div className="shell-stat">
          <span className="shell-stat-v">{result?.line_count ?? "—"}</span>
          <span className="shell-stat-lbl">行数</span>
        </div>
        <div
          className={`shell-stat ${
            flaggedLines.length > 0 ? "is-warn is-interactive" : ""
          }`}
          role={flaggedLines.length > 0 ? "button" : undefined}
          tabIndex={flaggedLines.length > 0 ? 0 : undefined}
          title={flaggedLines.length > 0 ? "点击巡检下一处超长行" : undefined}
          onClick={flaggedLines.length > 0 ? jumpToNextFlagged : undefined}
          onKeyDown={
            flaggedLines.length > 0
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    jumpToNextFlagged();
                  }
                }
              : undefined
          }
        >
          <span className="shell-stat-v">
            {result?.flagged_lines.length ?? "—"}
          </span>
          <span className="shell-stat-lbl">
            {flaggedLines.length > 0 ? "超长行 (点击定位)" : "超长行"}
          </span>
        </div>
      </div>
      <div className="shell-right-actions">
        <button
          type="button"
          className={`shell-btn-copy ${copied ? "is-copied" : ""}`}
          disabled={!result?.processed || streaming}
          title={result?.processed ? "复制结果 (Ctrl+Shift+C)" : undefined}
          onClick={onCopy}
        >
          <CopyIcon />
          {copied ? "已复制" : "复制结果"}
        </button>
      </div>
    </>
  );
}
