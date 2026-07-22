import { ApiError } from "@/lib/api-error";
import type { BackendStatus } from "@/lib/types";

export type BannerKind =
  | "none"
  | "starting"
  | "unavailable"
  | "stopped"
  | "process_http"
  | "process_validation"
  | "stale_backend"
  | "network";

export type BannerContent = {
  kind: BannerKind;
  title: string;
  hint?: string;
  detail?: string;
  tone: "warn" | "err";
};

export function mapHealthToBannerKind(
  status: BackendStatus,
  wasEverReady: boolean,
): BannerKind {
  if (status === "starting") return "starting";
  if (status === "error") return wasEverReady ? "stopped" : "unavailable";
  return "none";
}

export function bannerContent(
  kind: BannerKind,
  detail?: string,
): BannerContent | null {
  switch (kind) {
    case "starting":
      return {
        kind,
        title: "正在连接后端 · 端口 17300",
        hint: "首次启动可能需要数秒，请稍候。",
        tone: "warn",
      };
    case "unavailable":
      return {
        kind,
        title: "后端不可达 · 端口 17300",
        hint: "请确认应用已完全启动，或查看端口是否被其他程序占用。",
        detail,
        tone: "err",
      };
    case "stopped":
      return {
        kind,
        title: "后端已停止",
        hint: "请关闭并重新打开应用，或点击重试连接。",
        detail,
        tone: "err",
      };
    case "process_http":
      return {
        kind,
        title: "处理失败",
        hint: "请稍后重试；若持续失败请重启应用。",
        detail,
        tone: "err",
      };
    case "process_validation":
      return {
        kind,
        title: "文稿或参数无效",
        hint: "请检查文稿内容与设置后重试。",
        detail,
        tone: "err",
      };
    case "stale_backend":
      return {
        kind,
        title: "后端版本过旧",
        hint: "请完全关闭 SentRealm 窗口后重新打开，以加载最新后端。",
        detail,
        tone: "err",
      };
    case "network":
      return {
        kind,
        title: "网络请求失败",
        hint: "请确认后端仍在运行，或点击重试。",
        detail,
        tone: "err",
      };
    default:
      return null;
  }
}

export function mapProcessError(error: unknown): BannerKind {
  if (error instanceof ApiError) {
    if (error.status === 404) return "stale_backend";
    if (error.status === 422) return "process_validation";
    if (error.status >= 500) return "process_http";
    if (error.status >= 400) return "process_validation";
  }
  return "network";
}
