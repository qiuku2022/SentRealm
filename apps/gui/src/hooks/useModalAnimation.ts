import { useEffect, useState, type TransitionEvent } from "react";

export function useModalAnimation(open: boolean) {
  const [present, setPresent] = useState(open);
  const [active, setActive] = useState(false);

  useEffect(() => {
    if (open) {
      setPresent(true);
      const frame = requestAnimationFrame(() => {
        requestAnimationFrame(() => setActive(true));
      });
      return () => cancelAnimationFrame(frame);
    }
    setActive(false);
  }, [open]);

  const handleScrimTransitionEnd = (event: TransitionEvent<HTMLDivElement>) => {
    if (event.target !== event.currentTarget) return;
    if (!active && event.propertyName === "opacity") {
      setPresent(false);
    }
  };

  return { present, active, handleScrimTransitionEnd };
}
