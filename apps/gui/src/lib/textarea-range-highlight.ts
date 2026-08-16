/** Scroll a textarea to a character range and pulse-highlight it twice. */

export type HighlightHandle = {
  cancel: () => void;
};

type PulseOptions = {
  /** Parent of the textarea (`.shell-editor`); highlight layer mounts here. */
  container: HTMLElement;
  textarea: HTMLTextAreaElement;
  start: number;
  end: number;
};

const MIRROR_STYLE_PROPS = [
  "boxSizing",
  "width",
  "paddingTop",
  "paddingRight",
  "paddingBottom",
  "paddingLeft",
  "borderTopWidth",
  "borderRightWidth",
  "borderBottomWidth",
  "borderLeftWidth",
  "fontFamily",
  "fontSize",
  "fontWeight",
  "fontStyle",
  "letterSpacing",
  "lineHeight",
  "textTransform",
  "wordSpacing",
  "textIndent",
  "whiteSpace",
  "wordBreak",
  "overflowWrap",
  "tabSize",
] as const;

/** AE Easy Ease–like curve (smooth ease-out), matches shell motion language. */
const SCROLL_BEZIER = { x1: 0.22, y1: 1, x2: 0.36, y2: 1 } as const;
const SCROLL_DURATION_MIN_MS = 280;
const SCROLL_DURATION_MAX_MS = 560;
const SCROLL_PX_PER_MS = 2.4;

type ContentRect = { left: number; top: number; width: number; height: number };

function copyTextareaMetrics(
  source: HTMLTextAreaElement,
  target: HTMLElement,
): void {
  const style = window.getComputedStyle(source);
  for (const prop of MIRROR_STYLE_PROPS) {
    target.style[prop] = style[prop];
  }
  target.style.height = "auto";
  target.style.overflow = "hidden";
  target.style.position = "absolute";
  target.style.visibility = "hidden";
  target.style.pointerEvents = "none";
  target.style.whiteSpace = "pre-wrap";
  target.style.overflowWrap = "break-word";
  target.style.top = "0";
  target.style.left = "-99999px";
}

/** Measure target range rects in unscrolled content coordinates. */
function measureRangeInContent(
  textarea: HTMLTextAreaElement,
  start: number,
  end: number,
): ContentRect[] {
  const value = textarea.value;
  const mirror = document.createElement("div");
  copyTextareaMetrics(textarea, mirror);
  mirror.style.width = `${textarea.clientWidth}px`;

  const before = document.createTextNode(value.slice(0, start));
  const mark = document.createElement("span");
  mark.textContent = value.slice(start, end) || "\u200b";
  const after = document.createTextNode(value.slice(end));
  mirror.append(before, mark, after);
  document.body.appendChild(mirror);

  try {
    const mirrorRect = mirror.getBoundingClientRect();
    return Array.from(mark.getClientRects())
      .filter((rect) => rect.width > 0 && rect.height > 0)
      .map((rect) => ({
        left: rect.left - mirrorRect.left,
        top: rect.top - mirrorRect.top,
        width: rect.width,
        height: rect.height,
      }));
  } finally {
    mirror.remove();
  }
}

function sampleCubicBezier(
  t: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number,
): number {
  // Solve cubic Bezier x(u)=t for u, then return y(u).
  let u = t;
  for (let i = 0; i < 8; i++) {
    const xu =
      3 * (1 - u) * (1 - u) * u * x1 + 3 * (1 - u) * u * u * x2 + u * u * u;
    const dx =
      3 * (1 - u) * (1 - u) * x1 +
      6 * (1 - u) * u * (x2 - x1) +
      3 * u * u * (1 - x2);
    if (Math.abs(dx) < 1e-6) break;
    u -= (xu - t) / dx;
    u = Math.min(1, Math.max(0, u));
  }
  return (
    3 * (1 - u) * (1 - u) * u * y1 + 3 * (1 - u) * u * u * y2 + u * u * u
  );
}

function scrollDurationMs(distancePx: number): number {
  const byDistance = Math.abs(distancePx) / SCROLL_PX_PER_MS;
  return Math.min(
    SCROLL_DURATION_MAX_MS,
    Math.max(SCROLL_DURATION_MIN_MS, byDistance),
  );
}

function targetScrollTopForRange(
  textarea: HTMLTextAreaElement,
  rects: ContentRect[],
): number {
  const top = Math.min(...rects.map((r) => r.top));
  const bottom = Math.max(...rects.map((r) => r.top + r.height));
  const center = (top + bottom) / 2;
  const maxScroll = Math.max(0, textarea.scrollHeight - textarea.clientHeight);
  return Math.min(
    maxScroll,
    Math.max(0, center - textarea.clientHeight / 2),
  );
}

/**
 * Animate textarea.scrollTop with a cubic-bezier ease.
 * Returns a cancel function.
 */
function animateScrollTop(
  textarea: HTMLTextAreaElement,
  to: number,
  durationMs: number,
  onComplete: () => void,
): () => void {
  const from = textarea.scrollTop;
  if (Math.abs(to - from) < 1 || durationMs <= 0) {
    textarea.scrollTop = to;
    onComplete();
    return () => undefined;
  }

  let raf = 0;
  let cancelled = false;
  const started = performance.now();
  const { x1, y1, x2, y2 } = SCROLL_BEZIER;

  const tick = (now: number) => {
    if (cancelled) return;
    const t = Math.min(1, (now - started) / durationMs);
    const eased = sampleCubicBezier(t, x1, y1, x2, y2);
    textarea.scrollTop = from + (to - from) * eased;
    if (t < 1) {
      raf = window.requestAnimationFrame(tick);
      return;
    }
    textarea.scrollTop = to;
    onComplete();
  };

  raf = window.requestAnimationFrame(tick);
  return () => {
    cancelled = true;
    window.cancelAnimationFrame(raf);
  };
}

function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function ensureHighlightLayer(container: HTMLElement): HTMLElement {
  let layer = container.querySelector<HTMLElement>(
    ".shell-editor-highlight-layer",
  );
  if (!layer) {
    layer = document.createElement("div");
    layer.className = "shell-editor-highlight-layer";
    layer.setAttribute("aria-hidden", "true");
    container.appendChild(layer);
  }
  return layer;
}

function placePulseMarks(
  container: HTMLElement,
  textarea: HTMLTextAreaElement,
  contentRects: ContentRect[],
  reduced: boolean,
): { marks: HTMLElement[]; layer: HTMLElement } {
  const layer = ensureHighlightLayer(container);
  layer.replaceChildren();

  const textareaRect = textarea.getBoundingClientRect();
  const containerRect = container.getBoundingClientRect();
  const offsetLeft = textareaRect.left - containerRect.left;
  const offsetTop = textareaRect.top - containerRect.top;
  const marks: HTMLElement[] = [];

  for (const rect of contentRects) {
    const el = document.createElement("div");
    el.className = reduced
      ? "shell-editor-pulse-mark is-static"
      : "shell-editor-pulse-mark";
    el.style.left = `${offsetLeft + rect.left - textarea.scrollLeft}px`;
    el.style.top = `${offsetTop + rect.top - textarea.scrollTop}px`;
    el.style.width = `${rect.width}px`;
    el.style.height = `${rect.height}px`;
    layer.appendChild(el);
    marks.push(el);
  }

  return { marks, layer };
}

/**
 * Scroll to [start, end) with bezier easing, then pulse-highlight twice
 * (or once statically when reduced motion is preferred).
 * Does not change textarea selection/focus.
 */
export function pulseTextareaRange(options: PulseOptions): HighlightHandle {
  const { container, textarea, start, end } = options;
  const safeEnd = Math.max(start, Math.min(end, textarea.value.length));
  const safeStart = Math.max(0, Math.min(start, safeEnd));

  const contentRects = measureRangeInContent(textarea, safeStart, safeEnd);
  if (contentRects.length === 0) {
    return { cancel: () => undefined };
  }

  const targetTop = targetScrollTopForRange(textarea, contentRects);
  const reduced = prefersReducedMotion();
  let reducedTimer: number | null = null;
  let cancelScroll: (() => void) | null = null;
  let cancelled = false;
  let layer: HTMLElement | null = null;

  const cleanup = () => {
    if (cancelled) return;
    cancelled = true;
    cancelScroll?.();
    cancelScroll = null;
    if (reducedTimer !== null) window.clearTimeout(reducedTimer);
    layer?.replaceChildren();
  };

  const startPulse = () => {
    if (cancelled) return;
    const placed = placePulseMarks(container, textarea, contentRects, reduced);
    layer = placed.layer;
    const { marks } = placed;
    if (marks.length === 0) {
      cleanup();
      return;
    }

    if (reduced) {
      reducedTimer = window.setTimeout(cleanup, 1000);
      return;
    }

    let ended = 0;
    const onEnd = (event: AnimationEvent) => {
      if (event.animationName !== "shell-source-pulse") return;
      ended += 1;
      if (ended >= marks.length) cleanup();
    };
    for (const el of marks) {
      el.addEventListener("animationend", onEnd);
    }
  };

  if (reduced) {
    textarea.scrollTop = targetTop;
    startPulse();
  } else {
    cancelScroll = animateScrollTop(
      textarea,
      targetTop,
      scrollDurationMs(targetTop - textarea.scrollTop),
      startPulse,
    );
  }

  return { cancel: cleanup };
}
