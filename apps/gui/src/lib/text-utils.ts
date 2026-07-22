/** Character count aligned with AppShell / core display rules. */

export function countLineChars(text: string): number {
  let count = 0;
  for (const ch of text) {
    if (/[\u4e00-\u9fff\u3400-\u4dbfA-Za-z0-9]/.test(ch)) count += 1;
  }
  return count;
}

export function formatLineNumber(index: number): string {
  return String(index + 1).padStart(2, "0");
}

export function parsePunctuationKeep(raw: string): string[] {
  return raw
    .split(/[\s/]+/)
    .map((token) => token.trim())
    .filter(Boolean);
}

export function formatPunctuationKeep(tokens: string[]): string {
  return tokens.join(" ");
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  if (Number.isNaN(diffMs)) return iso;

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;

  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;

  return date.toLocaleString();
}

export function suggestTitleFromText(text: string, maxLen = 28): string {
  const firstLine = text.split("\n").find((line) => line.trim())?.trim() ?? "";
  if (!firstLine) return "";
  return firstLine.length <= maxLen ? firstLine : firstLine.slice(0, maxLen);
}
