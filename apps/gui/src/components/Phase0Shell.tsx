import { AlertCircleIcon, LoaderCircleIcon, RefreshCwIcon } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useBackend } from "@/hooks/useBackend";
import { fetchSettings, preprocessText } from "@/lib/api";
import type { PreprocessResult, Settings } from "@/lib/types";

const SAMPLE_TEXT =
  "短视频的前三秒决定观众是否愿意继续看下去。与其急着介绍自己，不如先抛出一个具体问题。";

export function Phase0Shell() {
  const { status, baseUrl, error, refresh } = useBackend();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [text, setText] = useState(SAMPLE_TEXT);
  const [result, setResult] = useState<PreprocessResult | null>(null);
  const [processing, setProcessing] = useState(false);

  const loadSettings = useCallback(async () => {
    if (!baseUrl || status !== "ready") return;
    setSettingsError(null);
    try {
      const data = await fetchSettings(baseUrl);
      setSettings(data);
    } catch (e) {
      setSettingsError(e instanceof Error ? e.message : String(e));
    }
  }, [baseUrl, status]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  const handlePreprocess = async () => {
    if (!baseUrl) return;
    if (!text.trim()) {
      toast.error("文稿不能为空");
      return;
    }
    setProcessing(true);
    setResult(null);
    try {
      const data = await preprocessText(baseUrl, text);
      setResult(data);
      toast.success(`处理完成 · ${data.line_count} 行`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col gap-6 p-6">
      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold tracking-tight">SentRealm</h1>
          <Badge variant="outline">Phase 0 调试壳</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Tauri spawn FastAPI → health → settings / preprocess（OD 三栏 Phase 1）
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            后端状态
            {status === "starting" && (
              <LoaderCircleIcon className="size-4 animate-spin text-muted-foreground" />
            )}
            {status === "ready" && (
              <Badge variant="success">已就绪 · 17300</Badge>
            )}
            {status === "error" && (
              <Badge variant="destructive">未就绪</Badge>
            )}
          </CardTitle>
          <CardDescription>
            base URL 来自 Tauri command，不硬编码端口。
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="text-xs text-muted-foreground">
            {baseUrl ?? "（等待 get_api_base_url）"}
          </p>
          {error && (
            <Alert variant="destructive">
              <AlertCircleIcon />
              <AlertTitle>后端未就绪</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-fit"
            onClick={() => void refresh()}
          >
            <RefreshCwIcon data-icon="inline-start" />
            重新检查 health
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
          <CardDescription>GET /api/v1/settings（health 通过后加载）</CardDescription>
        </CardHeader>
        <CardContent>
          {status !== "ready" && (
            <p className="text-sm text-muted-foreground">等待后端就绪…</p>
          )}
          {settingsError && (
            <Alert variant="destructive" className="mb-3">
              <AlertCircleIcon />
              <AlertDescription>{settingsError}</AlertDescription>
            </Alert>
          )}
          {settings && (
            <pre className="overflow-x-auto rounded-md border bg-muted/40 p-3 text-xs">
              {JSON.stringify(settings, null, 2)}
            </pre>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preprocess</CardTitle>
          <CardDescription>POST /api/v1/preprocess</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            disabled={status !== "ready" || processing}
            placeholder="粘贴口播稿…"
          />
          <Button
            type="button"
            disabled={status !== "ready" || processing}
            onClick={() => void handlePreprocess()}
          >
            {processing && (
              <LoaderCircleIcon
                data-icon="inline-start"
                className="animate-spin"
              />
            )}
            处理文稿
          </Button>
          {result && (
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">行数 {result.line_count}</Badge>
                {result.flagged_lines.length > 0 && (
                  <Badge variant="warning">
                    标记 {result.flagged_lines.length} 行
                  </Badge>
                )}
              </div>
              <pre className="max-h-64 overflow-auto rounded-md border bg-muted/40 p-3 text-xs whitespace-pre-wrap">
                {result.processed}
              </pre>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
