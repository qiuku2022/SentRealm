import { invoke } from "@tauri-apps/api/core";

import { ApiError } from "@/lib/api-error";
import type {
  BreakLexiconSettings,
  Document,
  DocumentDetail,
  DocumentResult,
  ExportDocumentResponse,
  HealthResponse,
  LlmKeyStatus,
  LlmTestResult,
  PreprocessResult,
  PreprocessStreamProgress,
  Settings,
  WorkspaceResponse,
} from "@/lib/types";

const HEALTH_POLL_MS = 200;
const HEALTH_TIMEOUT_MS = 30_000;

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    // ignore
  }
  return `${fallback}：HTTP ${res.status}`;
}

async function ensureOk(res: Response, fallback: string): Promise<void> {
  if (res.ok) return;
  throw new ApiError(await parseError(res, fallback), res.status);
}

export async function getApiBaseUrl(): Promise<string> {
  return invoke<string>("get_api_base_url");
}

export async function getBackendStartupError(): Promise<string | null> {
  const err = await invoke<string | null>("get_backend_startup_error");
  return err?.trim() ? err : null;
}

export async function fetchHealth(baseUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl}/health`);
    if (!res.ok) return false;
    const body = (await res.json()) as HealthResponse;
    return body.status === "ok";
  } catch {
    return false;
  }
}

export async function waitForHealth(baseUrl: string): Promise<boolean> {
  const deadline = Date.now() + HEALTH_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await fetchHealth(baseUrl)) return true;
    await new Promise((r) => setTimeout(r, HEALTH_POLL_MS));
  }
  return false;
}

export async function fetchSettings(baseUrl: string): Promise<Settings> {
  const res = await fetch(`${baseUrl}/api/v1/settings`);
  await ensureOk(res, "读取 settings 失败");
  return res.json() as Promise<Settings>;
}

export async function saveSettings(
  baseUrl: string,
  settings: Settings,
): Promise<Settings> {
  const res = await fetch(`${baseUrl}/api/v1/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  await ensureOk(res, "保存 settings 失败");
  return res.json() as Promise<Settings>;
}

export async function fetchBreakLexiconDefaults(
  baseUrl: string,
): Promise<BreakLexiconSettings> {
  const res = await fetch(`${baseUrl}/api/v1/break-lexicon/defaults`);
  await ensureOk(res, "读取内置词表失败");
  return res.json() as Promise<BreakLexiconSettings>;
}

export async function fetchLlmKeyStatus(baseUrl: string): Promise<LlmKeyStatus> {
  const res = await fetch(`${baseUrl}/api/v1/settings/llm-key-status`);
  if (!res.ok) {
    return { configured: false };
  }
  return res.json() as Promise<LlmKeyStatus>;
}

export async function testLlmConnection(baseUrl: string): Promise<LlmTestResult> {
  const res = await fetch(`${baseUrl}/api/v1/settings/llm-test`, {
    method: "POST",
  });
  if (res.status === 404) {
    throw new ApiError(
      "后端未加载 LLM 预检接口（Not Found）。请完全关闭 SentRealm 后重新打开。",
      404,
    );
  }
  await ensureOk(res, "LLM 连通性检测失败");
  return res.json() as Promise<LlmTestResult>;
}

export async function preprocessText(
  baseUrl: string,
  text: string,
): Promise<PreprocessResult> {
  const res = await fetch(`${baseUrl}/api/v1/preprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  await ensureOk(res, "preprocess 失败");
  return res.json() as Promise<PreprocessResult>;
}

function parseSseEvents(
  chunk: string,
  onEvent: (payload: Record<string, unknown>) => void,
): string {
  const blocks = chunk.split("\n\n");
  const remainder = blocks.pop() ?? "";
  for (const block of blocks) {
    for (const line of block.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      onEvent(JSON.parse(line.slice(6)) as Record<string, unknown>);
    }
  }
  return remainder;
}

export async function preprocessTextStream(
  baseUrl: string,
  text: string,
  onProgress: (progress: PreprocessStreamProgress) => void,
): Promise<PreprocessResult> {
  const res = await fetch(`${baseUrl}/api/v1/preprocess/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (res.status === 404) {
    const result = await preprocessText(baseUrl, text);
    onProgress({
      ...result,
      phase: "rules",
    });
    return result;
  }
  if (!res.ok) {
    throw new ApiError(await parseError(res, "preprocess 失败"), res.status);
  }
  if (!res.body) {
    throw new Error("preprocess 流式响应不可用");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: PreprocessResult | null = null;

  let streamError: ApiError | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = parseSseEvents(buffer, (payload) => {
      if (payload.type === "error") {
        streamError = new ApiError(String(payload.detail ?? "preprocess 失败"), 400);
        return;
      }
      if (payload.type === "progress") {
        onProgress(payload as unknown as PreprocessStreamProgress);
        return;
      }
      if (payload.type === "done") {
        finalResult = {
          original: String(payload.original),
          processed: String(payload.processed),
          line_count: Number(payload.line_count),
          flagged_lines: (payload.flagged_lines as number[]) ?? [],
        };
      }
    });
    if (streamError) throw streamError;
  }

  if (buffer.trim()) {
    parseSseEvents(`${buffer}\n\n`, (payload) => {
      if (payload.type === "error") {
        streamError = new ApiError(String(payload.detail ?? "preprocess 失败"), 400);
        return;
      }
      if (payload.type === "done") {
        finalResult = {
          original: String(payload.original),
          processed: String(payload.processed),
          line_count: Number(payload.line_count),
          flagged_lines: (payload.flagged_lines as number[]) ?? [],
        };
      }
    });
  }
  if (streamError) throw streamError;

  if (!finalResult) {
    throw new Error("preprocess 未完成");
  }
  return finalResult;
}

export async function fetchWorkspace(baseUrl: string): Promise<WorkspaceResponse> {
  const res = await fetch(`${baseUrl}/api/v1/workspace`);
  if (!res.ok) {
    throw new Error(await parseError(res, "读取 workspace 失败"));
  }
  return res.json() as Promise<WorkspaceResponse>;
}

export async function setWorkspaceActive(
  baseUrl: string,
  projectId: string,
  documentId: string,
): Promise<WorkspaceResponse> {
  const res = await fetch(`${baseUrl}/api/v1/workspace/active`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, document_id: documentId }),
  });
  if (!res.ok) {
    throw new Error(await parseError(res, "切换文稿失败"));
  }
  return res.json() as Promise<WorkspaceResponse>;
}

export async function createDocument(
  baseUrl: string,
  projectId: string,
  title = "未命名文稿",
): Promise<Document> {
  const res = await fetch(`${baseUrl}/api/v1/projects/${projectId}/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    throw new Error(await parseError(res, "新建文稿失败"));
  }
  return res.json() as Promise<Document>;
}

export async function fetchDocument(
  baseUrl: string,
  projectId: string,
  documentId: string,
): Promise<DocumentDetail> {
  const res = await fetch(
    `${baseUrl}/api/v1/projects/${projectId}/documents/${documentId}`,
  );
  if (!res.ok) {
    throw new Error(await parseError(res, "读取文稿失败"));
  }
  return res.json() as Promise<DocumentDetail>;
}

export async function updateDocument(
  baseUrl: string,
  projectId: string,
  documentId: string,
  payload: { title?: string; source_text?: string },
): Promise<DocumentDetail> {
  const res = await fetch(
    `${baseUrl}/api/v1/projects/${projectId}/documents/${documentId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  await ensureOk(res, "保存文稿失败");
  return res.json() as Promise<DocumentDetail>;
}

export async function deleteDocument(
  baseUrl: string,
  projectId: string,
  documentId: string,
): Promise<void> {
  const res = await fetch(
    `${baseUrl}/api/v1/projects/${projectId}/documents/${documentId}`,
    { method: "DELETE" },
  );
  await ensureOk(res, "删除文稿失败");
}

export async function saveDocumentResult(
  baseUrl: string,
  projectId: string,
  documentId: string,
  result: Omit<DocumentResult, "schema_version" | "processed_at"> & {
    processed_at?: string;
  },
): Promise<DocumentResult> {
  const body: DocumentResult = {
    schema_version: 1,
    processed_at: result.processed_at ?? new Date().toISOString(),
    line_count: result.line_count,
    flagged_lines: result.flagged_lines,
    processed: result.processed,
  };
  const res = await fetch(
    `${baseUrl}/api/v1/projects/${projectId}/documents/${documentId}/result`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
  if (!res.ok) {
    throw new Error(await parseError(res, "保存处理结果失败"));
  }
  return res.json() as Promise<DocumentResult>;
}

export async function exportDocumentTxt(
  baseUrl: string,
  projectId: string,
  documentId: string,
  processed: string,
): Promise<ExportDocumentResponse> {
  const res = await fetch(
    `${baseUrl}/api/v1/projects/${projectId}/documents/${documentId}/export`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ processed }),
    },
  );
  if (!res.ok) {
    throw new Error(await parseError(res, "导出失败"));
  }
  return res.json() as Promise<ExportDocumentResponse>;
}
