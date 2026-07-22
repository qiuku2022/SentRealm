/** Settings shape aligned with OpenAPI / sentrealm_core.models.Settings */

export type Preset = "landscape" | "portrait" | "custom";

export interface BreakLexiconSettings {
  protected_words: string[];
  break_after_words: string[];
  break_after_chars: string[];
  break_before_words: string[];
}

export interface Settings {
  preset: Preset;
  max_chars: number;
  /** Minimum chars per rule/LLM segment (editable; must be <= max_chars). */
  min_chars: number;
  punctuation_remove: string[];
  punctuation_keep: string[];
  llm_enabled: boolean;
  llm_endpoint: string;
  llm_model: string;
  break_lexicon: BreakLexiconSettings;
}

export interface PreprocessResult {
  original: string;
  processed: string;
  line_count: number;
  flagged_lines: number[];
}

export type PreprocessPhase = "rules" | "llm";

export interface PreprocessStreamProgress extends PreprocessResult {
  phase: PreprocessPhase;
  llm_current?: number | null;
  llm_total?: number | null;
}

export interface HealthResponse {
  status: "ok";
}

export type BackendStatus = "starting" | "ready" | "error";

export type FlowState = "new" | "ready" | "running" | "done" | "error";

export interface WorkspaceResponse {
  root_path: string;
  schema_version: number;
  active_project_id: string;
  active_document_id: string;
  recent_projects: ProjectSummary[];
  recent_documents: RecentDocumentItem[];
}

export interface ProjectSummary {
  id: string;
  name: string;
  updated_at: string;
  document_count: number;
}

export interface RecentDocumentItem {
  project_id: string;
  document_id: string;
  title: string;
  updated_at: string;
}

export interface DocumentDetail {
  id: string;
  project_id: string;
  title: string;
  source_text: string;
  created_at: string;
  updated_at: string;
  result: DocumentResult | null;
}

export interface DocumentResult {
  schema_version: number;
  processed_at: string;
  line_count: number;
  flagged_lines: number[];
  processed: string;
}

export interface ExportDocumentResponse {
  path: string;
  filename: string;
}

export interface DocumentMeta {
  schema_version: number;
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  meta: DocumentMeta;
  source_text: string;
}

export interface LlmKeyStatus {
  configured: boolean;
}

export interface LlmTestResult {
  ok: boolean;
  skipped?: boolean;
  message?: string | null;
}
