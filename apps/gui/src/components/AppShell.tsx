import {
  FileUpIcon,
  MonitorIcon,
  PanelRightOpenIcon,
  PlusIcon,
  SlidersHorizontalIcon,
  SmartphoneIcon,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { toast } from "sonner";

import { AlertDialog } from "@/components/AlertDialog";
import { BackendBanner } from "@/components/BackendBanner";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { DocTitleInput } from "@/components/DocTitleInput";
import { EditorMetaBar } from "@/components/EditorMetaBar";
import { ExportDialog } from "@/components/ExportDialog";
import { FabBar } from "@/components/FabBar";
import { ResultPanel } from "@/components/ResultPanel";
import { RulesEditorModal } from "@/components/RulesEditorModal";
import { SidebarPanel } from "@/components/SidebarPanel";
import { SettingsDrawer } from "@/components/SettingsDrawer";
import { useAppHotkeys } from "@/hooks/useAppHotkeys";
import { useBackend } from "@/hooks/useBackend";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { formatUserError, isNetworkError } from "@/lib/api-error";
import {
  bannerContent,
  mapHealthToBannerKind,
  mapProcessError,
  type BannerKind,
} from "@/lib/banner";
import {
  createDocument,
  deleteDocument,
  exportDocumentTxt,
  fetchDocument,
  fetchLlmKeyStatus,
  fetchSettings,
  fetchWorkspace,
  preprocessTextStream,
  saveDocumentResult,
  saveSettings,
  setWorkspaceActive,
  testLlmConnection,
  updateDocument,
} from "@/lib/api";
import { isLlmProcessingEnabled } from "@/lib/llm";
import { emptyBreakLexicon } from "@/lib/break-lexicon";
import {
  downloadTxtBlob,
  exportFilenameFromTitle,
  isTauriRuntime,
} from "@/lib/export-file";
import { locateProcessedLines } from "@/lib/locate-processed-line";
import {
  DEFAULT_DOCUMENT_TITLES,
  DEFAULT_PUNCTUATION_KEEP,
  DEFAULT_PUNCTUATION_REMOVE,
} from "@/lib/settings-defaults";
import {
  pulseTextareaRange,
  type HighlightHandle,
} from "@/lib/textarea-range-highlight";
import {
  parsePunctuationKeep,
  suggestTitleFromText,
} from "@/lib/text-utils";
import type {
  DocumentDetail,
  FlowState,
  PreprocessResult,
  RecentDocumentItem,
  PreprocessStreamProgress,
  Settings,
  WorkspaceResponse,
} from "@/lib/types";

function normalizeSettings(raw: Settings): Settings {
  return {
    ...raw,
    punctuation_keep: parsePunctuationKeep(raw.punctuation_keep.join("")),
    break_lexicon: raw.break_lexicon ?? emptyBreakLexicon(),
  };
}

export function AppShell() {
  const { status, baseUrl, error, wasEverReady, refresh } = useBackend();
  const [workspace, setWorkspace] = useState<WorkspaceResponse | null>(null);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [draftSettings, setDraftSettings] = useState<Settings | null>(null);
  const [llmKeyStatus, setLlmKeyStatus] = useState({ configured: false });
  const [sourceText, setSourceText] = useState("");
  const [result, setResult] = useState<PreprocessResult | null>(null);
  const [flowState, setFlowState] = useState<FlowState>("new");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsPresent, setSettingsPresent] = useState(false);
  const [rulesOpen, setRulesOpen] = useState(false);
  const [rulesPresent, setRulesPresent] = useState(false);
  const [presetMenuOpen, setPresetMenuOpen] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingRules, setSavingRules] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processingLabel, setProcessingLabel] = useState<string | undefined>();
  const [resultStreaming, setResultStreaming] = useState(false);
  const [llmConnectAlert, setLlmConnectAlert] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [activeResultLine, setActiveResultLine] = useState<number | null>(null);
  const [bootError, setBootError] = useState<string | null>(null);
  const editorRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const highlightHandleRef = useRef<HighlightHandle | null>(null);
  const activeLineTimerRef = useRef<number | null>(null);
  const [healthBannerDismissed, setHealthBannerDismissed] = useState(false);
  const [processBanner, setProcessBanner] = useState<{
    kind: BannerKind;
    detail?: string;
  } | null>(null);
  const [processBannerDismissed, setProcessBannerDismissed] = useState(false);
  const [lastDurationMs, setLastDurationMs] = useState<number | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [sideCollapsed, setSideCollapsed] = useState(() => {
    try {
      return localStorage.getItem("sentrealm:side-collapsed") === "1";
    } catch {
      return false;
    }
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [rightDrawerOpen, setRightDrawerOpen] = useState(false);
  const [rightPanelHidden, setRightPanelHidden] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<RecentDocumentItem | null>(
    null,
  );
  const [exportOpen, setExportOpen] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const processStartedAtRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const saveTimerRef = useRef<number | null>(null);
  const titleTouchedRef = useRef(false);

  const isNarrow = useMediaQuery("(max-width: 1024px)");

  const activeProjectId = workspace?.active_project_id ?? null;
  const activeDocumentId = workspace?.active_document_id ?? null;

  const presetLabel = useMemo(() => {
    if (!settings) return "";
    if (settings.preset === "landscape") return "横屏 · 15 字";
    if (settings.preset === "portrait") return "竖屏 · 10 字";
    return `自定义 · ${settings.max_chars} 字`;
  }, [settings]);

  const PresetIcon =
    settings?.preset === "portrait"
      ? SmartphoneIcon
      : settings?.preset === "custom"
        ? SlidersHorizontalIcon
        : MonitorIcon;

  const punctuationEnabled = (settings?.punctuation_remove.length ?? 0) > 0;

  const healthBannerKind = mapHealthToBannerKind(status, wasEverReady);
  const activeBannerKind: BannerKind = useMemo(() => {
    if (
      healthBannerKind !== "none" &&
      !healthBannerDismissed &&
      (healthBannerKind !== "starting" || !bootError)
    ) {
      return healthBannerKind;
    }
    if (processBanner && !processBannerDismissed) {
      return processBanner.kind;
    }
    return "none";
  }, [
    bootError,
    healthBannerDismissed,
    healthBannerKind,
    processBanner,
    processBannerDismissed,
  ]);

  const activeBannerDetail = useMemo(() => {
    if (activeBannerKind === healthBannerKind) {
      return bootError ?? error ?? undefined;
    }
    return processBanner?.detail;
  }, [
    activeBannerKind,
    bootError,
    error,
    healthBannerKind,
    processBanner?.detail,
  ]);

  const loadWorkspaceBundle = useCallback(async () => {
    if (!baseUrl) return;
    const ws = await fetchWorkspace(baseUrl);
    setWorkspace(ws);
    const doc = await fetchDocument(
      baseUrl,
      ws.active_project_id,
      ws.active_document_id,
    );
    setDocument(doc);
    setSourceText(doc.source_text);
    titleTouchedRef.current = !DEFAULT_DOCUMENT_TITLES.includes(
      doc.title as (typeof DEFAULT_DOCUMENT_TITLES)[number],
    );
    if (doc.result) {
      setResult({
        original: doc.source_text,
        processed: doc.result.processed,
        line_count: doc.result.line_count,
        flagged_lines: doc.result.flagged_lines,
      });
      setFlowState(doc.source_text.trim() ? "done" : "new");
    } else {
      setResult(null);
      setFlowState(doc.source_text.trim() ? "ready" : "new");
    }
  }, [baseUrl]);

  const bootstrap = useCallback(async () => {
    if (!baseUrl || status !== "ready") return;
    setBootError(null);
    try {
      const [loadedSettings, keyStatus] = await Promise.all([
        fetchSettings(baseUrl),
        fetchLlmKeyStatus(baseUrl),
      ]);
      setSettings(normalizeSettings(loadedSettings));
      setDraftSettings(normalizeSettings(loadedSettings));
      setLlmKeyStatus(keyStatus);
      await loadWorkspaceBundle();
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setBootError(message);
      setFlowState("error");
      setProcessBanner({
        kind: isNetworkError(e) ? "network" : "unavailable",
        detail: message,
      });
      setProcessBannerDismissed(false);
    }
  }, [baseUrl, loadWorkspaceBundle, status]);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (status === "error") setFlowState("error");
    if (status !== "error") setHealthBannerDismissed(false);
  }, [status]);

  useEffect(() => {
    if (flowState !== "running" || processStartedAtRef.current == null) return;
    const timer = window.setInterval(() => {
      setElapsedMs(performance.now() - (processStartedAtRef.current ?? 0));
    }, 100);
    return () => window.clearInterval(timer);
  }, [flowState]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "sentrealm:side-collapsed",
        sideCollapsed ? "1" : "0",
      );
    } catch {
      // ignore
    }
  }, [sideCollapsed]);

  useEffect(() => {
    if (flowState === "done" && isNarrow && result) {
      setRightDrawerOpen(true);
    }
  }, [flowState, isNarrow, result]);

  useEffect(() => {
    return () => {
      highlightHandleRef.current?.cancel();
      if (activeLineTimerRef.current !== null) {
        window.clearTimeout(activeLineTimerRef.current);
      }
    };
  }, []);

  const toggleSettings = useCallback(() => {
    setSettingsOpen((open) => {
      if (open && settings) setDraftSettings(settings);
      const next = !open;
      if (next) setPresetMenuOpen(false);
      return next;
    });
  }, [settings]);

  const focusSearch = useCallback(() => {
    if (sideCollapsed) setSideCollapsed(false);
    window.setTimeout(() => searchInputRef.current?.focus(), 0);
  }, [sideCollapsed]);

  const handleEscape = useCallback(() => {
    if (deleteTarget) {
      setDeleteTarget(null);
      return;
    }
    if (presetMenuOpen) {
      setPresetMenuOpen(false);
      return;
    }
    if (rulesOpen) {
      return;
    }
    if (settingsOpen) {
      setSettingsOpen(false);
      if (settings) setDraftSettings(settings);
      return;
    }
    if (isNarrow && rightDrawerOpen) {
      setRightDrawerOpen(false);
    }
  }, [
    deleteTarget,
    isNarrow,
    presetMenuOpen,
    rightDrawerOpen,
    rulesOpen,
    settings,
    settingsOpen,
  ]);

  useAppHotkeys({
    onToggleSettings: toggleSettings,
    onFocusSearch: focusSearch,
    onEscape: handleEscape,
  });

  const scheduleSaveSource = useCallback(
    (text: string) => {
      if (!baseUrl || !activeProjectId || !activeDocumentId) return;
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
      saveTimerRef.current = window.setTimeout(() => {
        void updateDocument(baseUrl, activeProjectId, activeDocumentId, {
          source_text: text,
        }).catch((err) => {
          toast.error(formatUserError(err));
        });
      }, 500);
    },
    [activeDocumentId, activeProjectId, baseUrl],
  );

  const maybeAutoTitle = useCallback(
    async (text: string) => {
      if (
        !baseUrl ||
        !activeProjectId ||
        !activeDocumentId ||
        !document ||
        titleTouchedRef.current
      ) {
        return;
      }
      if (
        !DEFAULT_DOCUMENT_TITLES.includes(
          document.title as (typeof DEFAULT_DOCUMENT_TITLES)[number],
        )
      ) {
        return;
      }
      const suggested = suggestTitleFromText(text);
      if (!suggested || suggested === document.title) return;
      try {
        const updated = await updateDocument(
          baseUrl,
          activeProjectId,
          activeDocumentId,
          { title: suggested },
        );
        setDocument(updated);
        setWorkspace((prev) =>
          prev
            ? {
                ...prev,
                recent_documents: prev.recent_documents.map((item) =>
                  item.document_id === activeDocumentId
                    ? { ...item, title: suggested }
                    : item,
                ),
              }
            : prev,
        );
      } catch {
        // non-blocking
      }
    },
    [activeDocumentId, activeProjectId, baseUrl, document],
  );

  const resultLineRanges = useMemo(() => {
    if (!result?.processed || !result.original) return [];
    return locateProcessedLines(result.original, result.processed, {
      punctuation_remove:
        settings?.punctuation_remove ?? DEFAULT_PUNCTUATION_REMOVE,
      punctuation_keep: settings?.punctuation_keep ?? DEFAULT_PUNCTUATION_KEEP,
    });
  }, [result, settings?.punctuation_keep, settings?.punctuation_remove]);

  const clearSourceHighlight = useCallback(() => {
    highlightHandleRef.current?.cancel();
    highlightHandleRef.current = null;
    if (activeLineTimerRef.current !== null) {
      window.clearTimeout(activeLineTimerRef.current);
      activeLineTimerRef.current = null;
    }
    setActiveResultLine(null);
  }, []);

  useEffect(() => {
    if (!result) clearSourceHighlight();
  }, [result, clearSourceHighlight]);

  const handleResultLineClick = useCallback(
    (index: number) => {
      const range = resultLineRanges[index];
      const textarea = textareaRef.current;
      const editor = editorRef.current;
      if (!range || !textarea || !editor) {
        if (!range) {
          console.warn("[SentRealm] 无法定位结果行到原文", index);
        }
        return;
      }

      highlightHandleRef.current?.cancel();
      if (activeLineTimerRef.current !== null) {
        window.clearTimeout(activeLineTimerRef.current);
      }

      setActiveResultLine(null);
      window.requestAnimationFrame(() => {
        setActiveResultLine(index);
      });
      highlightHandleRef.current = pulseTextareaRange({
        container: editor,
        textarea,
        start: range.start,
        end: range.end,
      });
      activeLineTimerRef.current = window.setTimeout(() => {
        setActiveResultLine(null);
        activeLineTimerRef.current = null;
      }, 520);
    },
    [resultLineRanges],
  );

  const handleSourceChange = (text: string) => {
    setSourceText(text);
    if (!text.trim()) {
      setFlowState("new");
      setResult(null);
      clearSourceHighlight();
    } else if (flowState === "done" || flowState === "new") {
      setFlowState("ready");
      setResult(null);
      clearSourceHighlight();
    }
    scheduleSaveSource(text);
  };

  const handleEditorBlur = () => {
    void maybeAutoTitle(sourceText);
  };

  const handleTitleCommit = async (title: string) => {
    titleTouchedRef.current = true;
    if (!baseUrl || !activeProjectId || !activeDocumentId) return;
    try {
      const updated = await updateDocument(
        baseUrl,
        activeProjectId,
        activeDocumentId,
        { title },
      );
      setDocument(updated);
      setWorkspace((prev) =>
        prev
          ? {
              ...prev,
              recent_documents: prev.recent_documents.map((item) =>
                item.document_id === activeDocumentId
                  ? { ...item, title }
                  : item,
              ),
            }
          : prev,
      );
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleSelectDocument = async (item: RecentDocumentItem) => {
    if (!baseUrl) return;
    try {
      await setWorkspaceActive(baseUrl, item.project_id, item.document_id);
      await loadWorkspaceBundle();
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleCreateDocument = async () => {
    if (!baseUrl || !activeProjectId) return;
    try {
      const created = await createDocument(baseUrl, activeProjectId);
      await setWorkspaceActive(
        baseUrl,
        activeProjectId,
        created.meta.id,
      );
      titleTouchedRef.current = false;
      await loadWorkspaceBundle();
      toast.success("已新建文稿");
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleImportTxt = async (file: File) => {
    const text = await file.text();
    handleSourceChange(text);
    toast.success(`已导入 ${file.name}`);
  };

  const handlePresetSelect = async (preset: Settings["preset"]) => {
    if (!settings || !baseUrl) return;
    if (preset === "custom") {
      setDraftSettings({ ...settings, preset: "custom" });
      setSettingsOpen(true);
      return;
    }
    const nextMax = preset === "landscape" ? 15 : 10;
    const next: Settings = {
      ...settings,
      preset,
      max_chars: nextMax,
      min_chars: Math.min(settings.min_chars, nextMax),
    };
    try {
      const saved = await saveSettings(baseUrl, next);
      setSettings(saved);
      setDraftSettings(saved);
      if (flowState === "done") setFlowState("ready");
      toast.success("预设已更新");
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleProcess = async () => {
    if (!baseUrl || !sourceText.trim()) {
      toast.error("文稿不能为空");
      setProcessBanner({ kind: "process_validation", detail: "文稿不能为空" });
      setProcessBannerDismissed(false);
      return;
    }
    setProcessing(true);
    setProcessingLabel(undefined);
    setProcessBanner(null);
    setProcessBannerDismissed(false);
    try {
      if (isLlmProcessingEnabled(settings, llmKeyStatus)) {
        setProcessingLabel("检测 LLM…");
        const llmTest = await testLlmConnection(baseUrl);
        if (!llmTest.ok) {
          setLlmConnectAlert(
            llmTest.message?.trim() ||
              "无法连接 LLM，请检查设置中的端点、模型与环境变量密钥。",
          );
          return;
        }
      }

      setProcessingLabel(undefined);
      setFlowState("running");
      processStartedAtRef.current = performance.now();
      setElapsedMs(0);
      setResult(null);
      setResultStreaming(true);
      setCopied(false);
      setRightPanelHidden(false);
      if (isNarrow) setRightDrawerOpen(true);

      const applyProgress = (progress: PreprocessStreamProgress) => {
        setResult({
          original: progress.original,
          processed: progress.processed,
          line_count: progress.line_count,
          flagged_lines: progress.flagged_lines,
        });
        if (
          progress.phase === "llm" &&
          progress.llm_current != null &&
          progress.llm_total != null &&
          progress.llm_total > 0
        ) {
          setProcessingLabel(
            `LLM 断句 ${progress.llm_current}/${progress.llm_total}`,
          );
        } else if (progress.phase === "rules") {
          setProcessingLabel("规则断句…");
        }
      };

      const data = await preprocessTextStream(
        baseUrl,
        sourceText,
        applyProgress,
      );
      const duration = performance.now() - (processStartedAtRef.current ?? 0);
      setLastDurationMs(duration);
      setResult(data);
      setFlowState("done");
      setResultStreaming(false);
      setProcessingLabel(undefined);
      if (activeProjectId && activeDocumentId) {
        await saveDocumentResult(
          baseUrl,
          activeProjectId,
          activeDocumentId,
          {
            processed: data.processed,
            line_count: data.line_count,
            flagged_lines: data.flagged_lines,
          },
        );
      }
      toast.success(`处理完成 · ${data.line_count} 行`);
    } catch (err) {
      const message = formatUserError(err);
      const kind = mapProcessError(err);
      setProcessBanner({ kind, detail: message });
      setProcessBannerDismissed(false);
      setFlowState(status === "ready" ? "ready" : "error");
      toast.error(message);
      if (kind === "process_http") {
        // keep toast + banner for 5xx
      }
    } finally {
      setProcessing(false);
      setProcessingLabel(undefined);
      setResultStreaming(false);
      processStartedAtRef.current = null;
    }
  };

  const handleCopy = async () => {
    if (!result?.processed) return;
    try {
      await navigator.clipboard.writeText(result.processed);
      setCopied(true);
      toast.success("已复制到剪贴板");
      window.setTimeout(() => setCopied(false), 1600);
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleExportToDocumentDir = async () => {
    if (!result?.processed || !baseUrl || !activeProjectId || !activeDocumentId) {
      toast.error("无法导出：缺少当前文稿或后端连接");
      return;
    }
    setExportBusy(true);
    try {
      const exported = await exportDocumentTxt(
        baseUrl,
        activeProjectId,
        activeDocumentId,
        result.processed,
      );
      setExportOpen(false);
      toast.success(`已导出到文稿目录 · ${exported.filename}`);
    } catch (err) {
      toast.error(formatUserError(err));
    } finally {
      setExportBusy(false);
    }
  };

  const handleExportCustom = async () => {
    if (!result?.processed) return;
    const filename = exportFilenameFromTitle(document?.title);
    setExportBusy(true);
    try {
      if (isTauriRuntime()) {
        const { save } = await import("@tauri-apps/plugin-dialog");
        const { writeTextFile } = await import("@tauri-apps/plugin-fs");
        const path = await save({
          defaultPath: filename,
          filters: [{ name: "Text", extensions: ["txt"] }],
        });
        if (!path) return;
        await writeTextFile(path, result.processed);
        setExportOpen(false);
        toast.success("已导出");
      } else {
        downloadTxtBlob(result.processed, filename);
        setExportOpen(false);
        toast.success(`已下载 · ${filename}`);
      }
    } catch (err) {
      toast.error(formatUserError(err));
    } finally {
      setExportBusy(false);
    }
  };

  const handleRenameDocument = async (
    item: RecentDocumentItem,
    title: string,
  ) => {
    if (!baseUrl) return;
    try {
      await updateDocument(baseUrl, item.project_id, item.document_id, {
        title,
      });
      setWorkspace((prev) =>
        prev
          ? {
              ...prev,
              recent_documents: prev.recent_documents.map((doc) =>
                doc.document_id === item.document_id ? { ...doc, title } : doc,
              ),
            }
          : prev,
      );
      if (
        item.document_id === activeDocumentId &&
        item.project_id === activeProjectId
      ) {
        setDocument((prev) => (prev ? { ...prev, title } : prev));
        titleTouchedRef.current = true;
      }
      toast.success("已重命名");
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleDeleteConfirm = async () => {
    if (!baseUrl || !deleteTarget) return;
    const target = deleteTarget;
    setDeleteTarget(null);
    try {
      await deleteDocument(baseUrl, target.project_id, target.document_id);
      await loadWorkspaceBundle();
      toast.success("已删除文稿");
    } catch (err) {
      toast.error(formatUserError(err));
    }
  };

  const handleSaveSettings = async () => {
    if (!baseUrl || !draftSettings) return;
    setSavingSettings(true);
    try {
      const saved = normalizeSettings(await saveSettings(baseUrl, draftSettings));
      setSettings(saved);
      setDraftSettings(saved);
      if (flowState === "done") setFlowState("ready");
      setSettingsOpen(false);
      toast.success("设置已保存");
    } catch (err) {
      toast.error(formatUserError(err));
    } finally {
      setSavingSettings(false);
    }
  };

  const handleSaveRules = async (next: Settings) => {
    if (!baseUrl) return;
    setSavingRules(true);
    try {
      const saved = normalizeSettings(await saveSettings(baseUrl, next));
      setSettings(saved);
      setDraftSettings(saved);
      if (flowState === "done") setFlowState("ready");
      setRulesOpen(false);
      toast.success("断句规则已保存");
    } catch (err) {
      toast.error(formatUserError(err));
    } finally {
      setSavingRules(false);
    }
  };

  const handleOpenRules = () => {
    if (settings) setDraftSettings(normalizeSettings(settings));
    setPresetMenuOpen(false);
    setRulesOpen(true);
  };

  const canProcess =
    status === "ready" &&
    !!sourceText.trim() &&
    !processing &&
    flowState !== "error";

  const healthClass =
    status === "ready"
      ? "is-ready"
      : status === "starting"
        ? "is-starting"
        : "is-error";

  const healthLabel =
    status === "ready"
      ? "后端已就绪"
      : status === "starting"
        ? "正在连接后端…"
        : wasEverReady
          ? "后端已停止"
          : "后端未就绪";

  const healthMeta = status === "ready" ? "17300" : undefined;

  const dismissBanner = () => {
    if (activeBannerKind === healthBannerKind) {
      setHealthBannerDismissed(true);
      return;
    }
    setProcessBannerDismissed(true);
  };

  const bannerRetry =
    activeBannerKind === healthBannerKind ||
    activeBannerKind === "network" ||
    activeBannerKind === "stopped" ||
    activeBannerKind === "unavailable"
      ? () => {
          setHealthBannerDismissed(false);
          setProcessBannerDismissed(false);
          void refresh();
        }
      : undefined;

  const colsClass = [
    "shell-cols",
    sideCollapsed ? "is-collapsed" : "",
    !isNarrow && rightPanelHidden ? "no-right" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const rightClass = [
    "shell-right",
    isNarrow && rightDrawerOpen ? "is-open" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={`shell-app ${
        settingsOpen || settingsPresent || rulesOpen || rulesPresent
          ? "is-dimmed"
          : ""
      }`}
    >
      {activeBannerKind !== "none" && bannerContent(activeBannerKind) && (
        <BackendBanner
          kind={activeBannerKind}
          detail={activeBannerDetail}
          onClose={dismissBanner}
          onRetry={bannerRetry}
        />
      )}

      <header className="shell-appbar">
        <div className="shell-appbar-title">SentRealm · 文稿预处理</div>
      </header>

      <div className={colsClass}>
        <SidebarPanel
          collapsed={sideCollapsed}
          onToggleCollapsed={() => setSideCollapsed((v) => !v)}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          searchInputRef={searchInputRef}
          documents={workspace?.recent_documents ?? []}
          activeDocumentId={activeDocumentId}
          healthClass={healthClass}
          healthLabel={healthLabel}
          healthMeta={healthMeta}
          onCreateDocument={() => void handleCreateDocument()}
          onSelectDocument={(item) => void handleSelectDocument(item)}
          onRenameDocument={(item, title) =>
            void handleRenameDocument(item, title)
          }
          onDeleteDocument={setDeleteTarget}
          onOpenSettings={() => setSettingsOpen(true)}
        />

        <main className="shell-canvas">
          <div className="shell-canvas-head">
            <DocTitleInput
              title={document?.title ?? "未命名文稿"}
              disabled={status !== "ready" || processing}
              onCommit={(title) => void handleTitleCommit(title)}
            />
            <div className="shell-head-actions">
              <button
                type="button"
                className="shell-import-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                <FileUpIcon className="size-4 inline" /> 导入 .txt
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,text/plain"
                hidden
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void handleImportTxt(file);
                  e.target.value = "";
                }}
              />
              <span className="shell-pill-chip is-active">
                <PlusIcon strokeWidth={1.6} />
                {punctuationEnabled ? "去标点" : "保留标点"}
              </span>
              <span className="shell-pill-chip is-active">
                <PresetIcon strokeWidth={1.6} />
                {presetLabel || "加载中…"}
              </span>
              {(isNarrow || rightPanelHidden) && (
                <button
                  type="button"
                  className="shell-import-btn shell-result-toggle"
                  onClick={() => {
                    if (isNarrow) setRightDrawerOpen(true);
                    else setRightPanelHidden(false);
                  }}
                >
                  <PanelRightOpenIcon className="size-4 inline" /> 结果
                </button>
              )}
            </div>
          </div>

          <div className="shell-canvas-body">
            <div className="shell-editor-wrap">
              <div
                ref={editorRef}
                className={`shell-editor ${sourceText.trim() ? "" : "is-empty"}`}
              >
                {!sourceText.trim() && (
                  <div className="shell-editor-empty">
                    <div className="shell-editor-empty-inner">
                      粘贴口播稿，或导入 <b>.txt</b> 文件后开始处理。
                    </div>
                  </div>
                )}
                <textarea
                  ref={textareaRef}
                  className="shell-editor-input"
                  value={sourceText}
                  onChange={(e) => handleSourceChange(e.target.value)}
                  onBlur={handleEditorBlur}
                  disabled={status !== "ready" || processing}
                  spellCheck={false}
                />
                <EditorMetaBar
                  sourceText={sourceText}
                  flowState={flowState}
                  result={result}
                  settings={settings}
                  llmKeyStatus={llmKeyStatus}
                />
              </div>
            </div>
          </div>

          <FabBar
            flowState={flowState}
            processing={processing}
            processingLabel={processingLabel}
            canProcess={canProcess}
            settings={settings}
            presetLabel={presetLabel}
            lastDurationMs={lastDurationMs}
            elapsedMs={elapsedMs}
            presetMenuOpen={presetMenuOpen}
            onPresetMenuOpenChange={setPresetMenuOpen}
            onOpenRules={handleOpenRules}
            onOpenSettings={() => setSettingsOpen(true)}
            onPresetSelect={(preset) => void handlePresetSelect(preset)}
            onProcess={() => void handleProcess()}
          />
        </main>

        <aside className={rightClass}>
          <div className="shell-right-inner">
            <ResultPanel
              result={result}
              flowState={flowState}
              streaming={resultStreaming}
              copied={copied}
              activeLineIndex={activeResultLine}
              onLineClick={handleResultLineClick}
              onCopy={() => void handleCopy()}
              onExport={() => setExportOpen(true)}
              showFold={!isNarrow}
              onToggleFold={() => setRightPanelHidden(true)}
            />
          </div>
        </aside>
      </div>

      {isNarrow && rightDrawerOpen && (
        <div
          className="shell-right-scrim"
          aria-hidden="true"
          onClick={() => setRightDrawerOpen(false)}
        />
      )}

      <AlertDialog
        open={llmConnectAlert !== null}
        title="无法连接 LLM"
        message={llmConnectAlert ?? ""}
        secondaryLabel="打开设置"
        onPrimary={() => setLlmConnectAlert(null)}
        onSecondary={() => {
          setLlmConnectAlert(null);
          setSettingsOpen(true);
        }}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="删除文稿"
        message={
          deleteTarget
            ? `确定删除「${deleteTarget.title}」？此操作不可撤销。`
            : ""
        }
        confirmLabel="删除"
        onConfirm={() => void handleDeleteConfirm()}
        onCancel={() => setDeleteTarget(null)}
      />

      <ExportDialog
        open={exportOpen}
        busy={exportBusy}
        onExportToDocumentDir={() => void handleExportToDocumentDir()}
        onExportCustom={() => void handleExportCustom()}
        onCancel={() => {
          if (!exportBusy) setExportOpen(false);
        }}
      />

      {draftSettings && (
        <RulesEditorModal
          open={rulesOpen}
          baseUrl={baseUrl ?? ""}
          settings={draftSettings}
          saving={savingRules}
          onPresentChange={setRulesPresent}
          onClose={() => setRulesOpen(false)}
          onSave={(next) => void handleSaveRules(next)}
        />
      )}

      {draftSettings && (
        <SettingsDrawer
          open={settingsOpen}
          settings={draftSettings}
          llmKeyStatus={llmKeyStatus}
          saving={savingSettings}
          onPresentChange={setSettingsPresent}
          onClose={() => {
            setSettingsOpen(false);
            if (settings) setDraftSettings(settings);
          }}
          onChange={setDraftSettings}
          onSave={() => void handleSaveSettings()}
        />
      )}
    </div>
  );
}
