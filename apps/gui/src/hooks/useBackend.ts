import { useCallback, useEffect, useState } from "react";

import {
  fetchHealth,
  getApiBaseUrl,
  getBackendStartupError,
  waitForHealth,
} from "@/lib/api";
import type { BackendStatus } from "@/lib/types";

export function useBackend() {
  const [status, setStatus] = useState<BackendStatus>("starting");
  const [baseUrl, setBaseUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wasEverReady, setWasEverReady] = useState(false);

  const refresh = useCallback(async () => {
    setStatus("starting");
    setError(null);

    try {
      const url = await getApiBaseUrl();
      setBaseUrl(url);

      const startupErr = await getBackendStartupError();
      if (startupErr) {
        setError(startupErr);
        setStatus("error");
        return;
      }

      const ok = (await fetchHealth(url)) || (await waitForHealth(url));
      if (!ok) {
        const err =
          (await getBackendStartupError()) ??
          "后端 health 检查超时（30s）。请确认应用已完全启动，或端口 17300 未被占用。";
        setError(err);
        setStatus("error");
        return;
      }

      setStatus("ready");
      setWasEverReady(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { status, baseUrl, error, wasEverReady, refresh };
}
