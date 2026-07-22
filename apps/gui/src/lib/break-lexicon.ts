import type { BreakLexiconSettings } from "@/lib/types";

export const LEXICON_CATEGORIES = [
  {
    key: "protected_words",
    label: "受保护词",
    description: "禁止从中切断（最长 4 字）",
    file: "protected_words.txt",
  },
  {
    key: "break_after_words",
    label: "后可断·词",
    description: "整词结束后可换行",
    file: "break_after_words.txt",
  },
  {
    key: "break_after_chars",
    label: "后可断·字",
    description: "单字结束后可换行",
    file: "break_after_chars.txt",
  },
  {
    key: "break_before_words",
    label: "前可断",
    description: "整词开始前可换行",
    file: "break_before_words.txt",
  },
] as const;

export type LexiconCategoryKey = (typeof LEXICON_CATEGORIES)[number]["key"];

export function emptyBreakLexicon(): BreakLexiconSettings {
  return {
    protected_words: [],
    break_after_words: [],
    break_after_chars: [],
    break_before_words: [],
  };
}

export function cloneBreakLexicon(
  lexicon: BreakLexiconSettings,
): BreakLexiconSettings {
  return {
    protected_words: [...lexicon.protected_words],
    break_after_words: [...lexicon.break_after_words],
    break_after_chars: [...lexicon.break_after_chars],
    break_before_words: [...lexicon.break_before_words],
  };
}

export function formatLexiconLines(words: string[]): string {
  return words.join("\n");
}

export function parseLexiconTextarea(text: string): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || seen.has(line)) continue;
    seen.add(line);
    result.push(line);
  }
  return result;
}

export function lexiconDraftEquals(
  a: BreakLexiconSettings,
  b: BreakLexiconSettings,
): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function validateLexiconDraft(
  lexicon: BreakLexiconSettings,
): string | null {
  for (const word of lexicon.protected_words) {
    if (word.length > 4) {
      return `受保护词「${word}」超过 4 字`;
    }
  }
  for (const char of lexicon.break_after_chars) {
    if ([...char].length !== 1) {
      return `后可断·字「${char}」必须为单个字符`;
    }
  }
  return null;
}
