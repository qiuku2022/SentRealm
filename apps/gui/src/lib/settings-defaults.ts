/** Mirrors sentrealm_core.models defaults for GUI-only restore. */

export const DEFAULT_PUNCTUATION_REMOVE: string[] = [
  "，",
  "。",
  "！",
  "？",
  "：",
  "；",
  "——",
  "、",
  ",",
  ".",
  "!",
  "?",
  ";",
  ":",
  "“",
  "”",
  "‘",
  "’",
  '"',
  "'",
  "（",
  "）",
  "(",
  ")",
  "…",
  "％",
];

export const DEFAULT_PUNCTUATION_KEEP: string[] = ["%", "."];

export const PRESET_MAX_CHARS = {
  landscape: 15,
  portrait: 10,
} as const;

/** Mirrors sentrealm_core.models.DEFAULT_MIN_CHARS */
export const DEFAULT_MIN_CHARS = 5;

export const DEFAULT_DOCUMENT_TITLES = ["未命名文稿", "新建文稿"] as const;
