import { LoaderCircleIcon, XIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { useModalAnimation } from "@/hooks/useModalAnimation";
import { fetchBreakLexiconDefaults } from "@/lib/api";
import {
  cloneBreakLexicon,
  formatLexiconLines,
  LEXICON_CATEGORIES,
  lexiconDraftEquals,
  parseLexiconTextarea,
  validateLexiconDraft,
  type LexiconCategoryKey,
} from "@/lib/break-lexicon";
import type { BreakLexiconSettings, Settings } from "@/lib/types";

type RulesEditorModalProps = {
  open: boolean;
  baseUrl: string;
  settings: Settings;
  saving: boolean;
  onClose: () => void;
  onSave: (next: Settings) => void;
  onPresentChange?: (present: boolean) => void;
};

export function RulesEditorModal({
  open,
  baseUrl,
  settings,
  saving,
  onClose,
  onSave,
  onPresentChange,
}: RulesEditorModalProps) {
  const { present, active, handleScrimTransitionEnd } = useModalAnimation(open);
  const [activeKey, setActiveKey] = useState<LexiconCategoryKey>("protected_words");
  const [draftLexicon, setDraftLexicon] = useState<BreakLexiconSettings>(() =>
    cloneBreakLexicon(settings.break_lexicon),
  );
  const [baselineLexicon, setBaselineLexicon] = useState<BreakLexiconSettings>(() =>
    cloneBreakLexicon(settings.break_lexicon),
  );
  const [validationError, setValidationError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [discardConfirmOpen, setDiscardConfirmOpen] = useState(false);

  const dirty = !lexiconDraftEquals(draftLexicon, baselineLexicon);
  const activeCategory =
    LEXICON_CATEGORIES.find((item) => item.key === activeKey) ??
    LEXICON_CATEGORIES[0];
  const activeWords = draftLexicon[activeKey];

  useEffect(() => {
    onPresentChange?.(present);
  }, [onPresentChange, present]);

  useEffect(() => {
    if (!open) return;
    const next = cloneBreakLexicon(settings.break_lexicon);
    setDraftLexicon(next);
    setBaselineLexicon(cloneBreakLexicon(next));
    setActiveKey("protected_words");
    setValidationError(null);
    setDiscardConfirmOpen(false);
  }, [open, settings.break_lexicon]);

  const requestClose = useCallback(() => {
    if (dirty) {
      setDiscardConfirmOpen(true);
      return;
    }
    onClose();
  }, [dirty, onClose]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (discardConfirmOpen) return;
      event.preventDefault();
      requestClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [discardConfirmOpen, open, requestClose]);

  const updateActiveWords = (text: string) => {
    const words = parseLexiconTextarea(text);
    setDraftLexicon((current) => ({
      ...current,
      [activeKey]: words,
    }));
    setValidationError(null);
  };

  const handleRestoreDefaults = async () => {
    if (!baseUrl) return;
    setRestoring(true);
    try {
      const defaults = await fetchBreakLexiconDefaults(baseUrl);
      setDraftLexicon(cloneBreakLexicon(defaults));
      setValidationError(null);
    } catch {
      setValidationError("读取内置词表失败");
    } finally {
      setRestoring(false);
    }
  };

  const handleSave = () => {
    const error = validateLexiconDraft(draftLexicon);
    if (error) {
      setValidationError(error);
      return;
    }
    onSave({
      ...settings,
      break_lexicon: cloneBreakLexicon(draftLexicon),
    });
  };

  if (!present) return null;

  return (
    <>
      <div
        className={`shell-scrim shell-scrim-modal ${active ? "is-open" : ""}`}
        aria-hidden="true"
        onClick={requestClose}
        onTransitionEnd={handleScrimTransitionEnd}
      />
      <div
        className={`shell-dialog shell-dialog-modal shell-dialog-rules ${
          active ? "is-open" : ""
        }`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="shell-rules-title"
      >
        <div className="shell-rules-head">
          <div>
            <div className="shell-rules-title" id="shell-rules-title">
              编辑断句规则
            </div>
            <div className="shell-rules-subtitle">
              一行一词；保存后下次处理生效
            </div>
          </div>
          <button
            type="button"
            className="shell-drawer-act-btn"
            aria-label="关闭"
            onClick={requestClose}
          >
            <XIcon className="size-4" />
          </button>
        </div>

        <div className="shell-rules-body">
          <nav className="shell-rules-nav" aria-label="词表分类">
            {LEXICON_CATEGORIES.map((category) => (
              <button
                key={category.key}
                type="button"
                className={`shell-rules-nav-item ${
                  activeKey === category.key ? "is-active" : ""
                }`}
                onClick={() => setActiveKey(category.key)}
              >
                <span className="shell-rules-nav-label">{category.label}</span>
                <span className="shell-rules-nav-file">{category.file}</span>
              </button>
            ))}
          </nav>

          <div className="shell-rules-panel">
            <div className="shell-rules-panel-head">
              <div className="shell-rules-panel-title">{activeCategory.label}</div>
              <div className="shell-rules-panel-desc">
                {activeCategory.description}
              </div>
            </div>
            <textarea
              className="shell-rules-textarea"
              value={formatLexiconLines(activeWords)}
              spellCheck={false}
              onChange={(event) => updateActiveWords(event.target.value)}
            />
            <div className="shell-rules-meta">共 {activeWords.length} 条</div>
            {validationError && (
              <div className="shell-rules-error" role="alert">
                {validationError}
              </div>
            )}
          </div>
        </div>

        <div className="shell-rules-foot">
          <button
            type="button"
            className="shell-btn-secondary"
            disabled={restoring || saving}
            onClick={() => void handleRestoreDefaults()}
          >
            {restoring ? (
              <>
                <LoaderCircleIcon className="size-4 animate-spin inline" />{" "}
                恢复中…
              </>
            ) : (
              "恢复默认"
            )}
          </button>
          <div className="shell-rules-foot-actions">
            <button
              type="button"
              className="shell-btn-secondary"
              disabled={saving}
              onClick={requestClose}
            >
              取消
            </button>
            <button
              type="button"
              className="shell-drawer-btn-primary"
              disabled={saving || !dirty}
              onClick={handleSave}
            >
              {saving ? (
                <>
                  <LoaderCircleIcon className="size-4 animate-spin" /> 保存中…
                </>
              ) : (
                "保存"
              )}
            </button>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={discardConfirmOpen}
        title="放弃未保存的修改？"
        message="断句规则有未保存的更改，确定关闭吗？"
        confirmLabel="放弃"
        cancelLabel="继续编辑"
        onConfirm={() => {
          setDiscardConfirmOpen(false);
          onClose();
        }}
        onCancel={() => setDiscardConfirmOpen(false)}
      />
    </>
  );
}
