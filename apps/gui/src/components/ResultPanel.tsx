import {
  CopyIcon,
  DownloadIcon,
  PanelRightCloseIcon,
} from "lucide-react";
import { useEffect, useRef } from "react";

import { countLineChars, formatLineNumber } from "@/lib/text-utils";
import type { FlowState, PreprocessResult } from "@/lib/types";

type ResultPanelProps = {
  result: PreprocessResult | null;
  flowState: FlowState;
  streaming?: boolean;
  copied: boolean;
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
  onCopy,
  onExport,
  onToggleFold,
  showFold = false,
}: ResultPanelProps) {
  const lines = result?.processed.split("\n") ?? [];
  const flaggedSet = new Set(result?.flagged_lines ?? []);
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!streaming || !result?.processed) return;
    listEndRef.current?.scrollIntoView({ block: "end" });
  }, [result?.processed, streaming]);

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
          {streaming && (
            <span className="shell-right-live">更新中</span>
          )}
        </div>
        <div className="shell-right-head-actions">
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
          <div className="shell-results-list">
            {lines.map((line, index) => {
              const isLong = flaggedSet.has(index);
              return (
                <div
                  key={`${index}-${line.slice(0, 12)}`}
                  className={`shell-result-line ${isLong ? "is-long" : ""}`}
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
            (result?.flagged_lines.length ?? 0) > 0 ? "is-warn" : ""
          }`}
        >
          <span className="shell-stat-v">
            {result?.flagged_lines.length ?? "—"}
          </span>
          <span className="shell-stat-lbl">超长行</span>
        </div>
      </div>
      <div className="shell-right-actions">
        <button
          type="button"
          className={`shell-btn-copy ${copied ? "is-copied" : ""}`}
          disabled={!result?.processed || streaming}
          onClick={onCopy}
        >
          <CopyIcon />
          {copied ? "已复制" : "复制结果"}
        </button>
      </div>
    </>
  );
}
