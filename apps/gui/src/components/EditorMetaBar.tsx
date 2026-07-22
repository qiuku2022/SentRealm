import { countLineChars } from "@/lib/text-utils";
import type { FlowState, LlmKeyStatus, PreprocessResult, Settings } from "@/lib/types";

type EditorMetaBarProps = {
  sourceText: string;
  flowState: FlowState;
  result: PreprocessResult | null;
  settings: Settings | null;
  llmKeyStatus: LlmKeyStatus;
};

export function EditorMetaBar({
  sourceText,
  flowState,
  result,
  settings,
  llmKeyStatus,
}: EditorMetaBarProps) {
  const sourceLines = sourceText ? sourceText.split("\n").length : 0;
  const charCount = countLineChars(sourceText);
  const showBreakStats = flowState === "done" && result;
  const llmSkipHint =
    !settings?.llm_enabled ||
    !llmKeyStatus.configured ||
    !settings.llm_endpoint.trim() ||
    !settings.llm_model.trim();

  return (
    <div className="shell-meta-bar">
      <div className="shell-meta-stats">
        <span>
          字符 <b>{charCount}</b>
        </span>
        <span>
          行 <b>{sourceLines}</b>
        </span>
        {showBreakStats && (
          <>
            <span>
              断句 <b>{result.line_count}</b> 行
            </span>
            {result.flagged_lines.length > 0 && (
              <span className="is-warn">
                超长 <b>{result.flagged_lines.length}</b> 行
              </span>
            )}
          </>
        )}
      </div>
      {llmSkipHint && sourceText.trim() && (
        <span className="shell-llm-hint">
          <span className="dot" />
          LLM 未配置 · 超长行将仅标记
        </span>
      )}
    </div>
  );
}
