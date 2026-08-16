/** Map processed result lines back to character ranges in the original source. */

export type TextRange = { start: number; end: number };

export type LocatePunctuationOptions = {
  punctuation_remove?: string[];
  punctuation_keep?: string[];
};

function sortTokensLongestFirst(tokens: string[]): string[] {
  return [...new Set(tokens.filter(Boolean))].sort((a, b) => b.length - a.length);
}

function isWhitespace(ch: string): boolean {
  return /\s/u.test(ch);
}

/** True if `haystack` at `index` starts with a removable punctuation token. */
function matchRemovableAt(
  haystack: string,
  index: number,
  removeTokens: string[],
  keepSet: Set<string>,
): string | null {
  for (const token of removeTokens) {
    if (keepSet.has(token)) continue;
    if (haystack.startsWith(token, index)) return token;
  }
  return null;
}

function canSkipInOriginal(
  haystack: string,
  index: number,
  removeTokens: string[],
  keepSet: Set<string>,
): number {
  const ch = haystack[index];
  if (!ch) return 0;
  if (isWhitespace(ch)) return 1;
  const removable = matchRemovableAt(haystack, index, removeTokens, keepSet);
  return removable ? removable.length : 0;
}

/**
 * Find the earliest span in `haystack` at/after `from` where `needle` is an
 * ordered subsequence, skipping whitespace and removable punctuation in the
 * haystack. Unexpected content characters cause a restart from the next index.
 */
function findSubsequenceSpan(
  haystack: string,
  needle: string,
  from: number,
  removeTokens: string[],
  keepSet: Set<string>,
): TextRange | null {
  if (!needle) return null;

  const maxStart = haystack.length;
  for (let attemptStart = from; attemptStart < maxStart; attemptStart++) {
    let i = attemptStart;
    let j = 0;
    let rangeStart = -1;

    while (i < haystack.length && j < needle.length) {
      const needleCh = needle[j]!;
      const hayCh = haystack[i]!;

      if (needleCh === hayCh) {
        if (rangeStart < 0) rangeStart = i;
        i += 1;
        j += 1;
        continue;
      }

      // Needle expects whitespace: consume one or more whitespace in haystack.
      if (isWhitespace(needleCh)) {
        if (!isWhitespace(hayCh)) break;
        while (i < haystack.length && isWhitespace(haystack[i]!)) i += 1;
        j += 1;
        continue;
      }

      const skip = canSkipInOriginal(haystack, i, removeTokens, keepSet);
      if (skip > 0) {
        i += skip;
        continue;
      }

      // Unexpected content — abandon this attemptStart.
      break;
    }

    if (j === needle.length && rangeStart >= 0) {
      return { start: rangeStart, end: i };
    }
  }

  return null;
}

/** Expand range rightward over contiguous removable punctuation (not whitespace). */
function expandOverPunctuation(
  haystack: string,
  range: TextRange,
  removeTokens: string[],
  keepSet: Set<string>,
): TextRange {
  let { start, end } = range;

  while (end < haystack.length) {
    const removable = matchRemovableAt(haystack, end, removeTokens, keepSet);
    if (!removable) break;
    end += removable.length;
  }

  return { start, end };
}

/**
 * Build per-line ranges in `original` for each line of `processed` (split on `\n`).
 * Lines are matched left-to-right so duplicate phrases map to successive spans.
 */
export function locateProcessedLines(
  original: string,
  processed: string,
  options: LocatePunctuationOptions = {},
): Array<TextRange | null> {
  const removeTokens = sortTokensLongestFirst(options.punctuation_remove ?? []);
  const keepSet = new Set(options.punctuation_keep ?? []);
  const lines = processed.split("\n");
  const ranges: Array<TextRange | null> = [];
  let cursor = 0;

  for (const line of lines) {
    if (!line) {
      ranges.push(null);
      continue;
    }

    const found = findSubsequenceSpan(
      original,
      line,
      cursor,
      removeTokens,
      keepSet,
    );
    if (!found) {
      ranges.push(null);
      continue;
    }

    const expanded = expandOverPunctuation(
      original,
      found,
      removeTokens,
      keepSet,
    );
    ranges.push(expanded);
    cursor = expanded.end;
  }

  return ranges;
}
