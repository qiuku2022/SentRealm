/** Browser / WebView fallback when Tauri save dialog is unavailable. */
export function downloadTxtBlob(content: string, filename: string): void {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function isTauriRuntime(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

/** Safe default filename for save dialog / blob download. */
export function exportFilenameFromTitle(title: string | undefined | null): string {
  const cleaned = (title ?? "")
    .trim()
    .replace(/[<>:"/\\|?*]/g, "_")
    .replace(/^[.\s]+|[.\s]+$/g, "");
  const stem = cleaned || "processed";
  const reserved = new Set(["source.txt", "result.json", "document.json"]);
  const filename = `${stem}.txt`;
  if (reserved.has(filename.toLowerCase())) {
    return `${stem}-processed.txt`;
  }
  return filename;
}
