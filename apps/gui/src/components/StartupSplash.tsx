import { useCallback, useEffect, useState } from "react";

const EXIT_DURATION_MS = 180;
const PLAYBACK_FALLBACK_MS = 5_000;

function shouldShowStartupSplash(): boolean {
  return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function StartupSplash() {
  const [visible, setVisible] = useState(shouldShowStartupSplash);
  const [leaving, setLeaving] = useState(false);

  const dismiss = useCallback(() => {
    setLeaving(true);
  }, []);

  useEffect(() => {
    if (!visible) return;

    const fallbackTimer = window.setTimeout(dismiss, PLAYBACK_FALLBACK_MS);
    return () => window.clearTimeout(fallbackTimer);
  }, [dismiss, visible]);

  useEffect(() => {
    if (!leaving) return;

    const exitTimer = window.setTimeout(
      () => setVisible(false),
      EXIT_DURATION_MS,
    );
    return () => window.clearTimeout(exitTimer);
  }, [leaving]);

  if (!visible) return null;

  return (
    <div
      className={`shell-startup-splash ${leaving ? "is-leaving" : ""}`}
      aria-hidden="true"
    >
      <video
        className="shell-startup-video"
        src="/startup.mp4"
        autoPlay
        muted
        playsInline
        preload="auto"
        onCanPlay={(event) => {
          void event.currentTarget.play().catch(dismiss);
        }}
        onEnded={dismiss}
        onError={dismiss}
      />
    </div>
  );
}
