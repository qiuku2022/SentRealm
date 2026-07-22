export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** 将 API / 网络错误转为用户可见的中文文案 */
const LEGACY_WORKSPACE_ERRORS: Record<string, string> = {
  "cannot delete the last project": "不能删除最后一个项目",
  "cannot delete the active project": "不能删除当前活动项目",
  "cannot delete the active document":
    "不能删除当前正在编辑的文稿，请先切换到其他文稿或新建一篇",
};

export function formatUserError(
  error: unknown,
  fallback = "操作失败，请稍后重试",
): string {
  if (error instanceof ApiError) {
    return LEGACY_WORKSPACE_ERRORS[error.message] ?? error.message;
  }
  if (isNetworkError(error)) {
    return "网络连接失败，请检查后端是否正在运行";
  }
  if (error instanceof Error) {
    const mapped = LEGACY_WORKSPACE_ERRORS[error.message];
    if (mapped) return mapped;
    if (/fetch|network|Failed to fetch/i.test(error.message)) {
      return "网络连接失败，请检查后端是否正在运行";
    }
    return error.message;
  }
  return fallback;
}

export function isNetworkError(error: unknown): boolean {
  if (error instanceof TypeError) return true;
  if (error instanceof Error && /fetch|network|Failed to fetch/i.test(error.message)) {
    return true;
  }
  return false;
}
