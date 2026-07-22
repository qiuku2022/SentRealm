import { AlertCircleIcon, LoaderCircleIcon, XIcon } from "lucide-react";

import { bannerContent, type BannerKind } from "@/lib/banner";

type BackendBannerProps = {
  kind: BannerKind;
  detail?: string;
  onClose: () => void;
  onRetry?: () => void;
};

export function BackendBanner({
  kind,
  detail,
  onClose,
  onRetry,
}: BackendBannerProps) {
  const content = bannerContent(kind, detail);
  if (!content) return null;

  return (
    <div
      className={`shell-banner ${content.tone === "warn" ? "is-warn" : "is-err"}`}
      role="alert"
    >
      <div className="shell-banner-main">
        {kind === "starting" ? (
          <LoaderCircleIcon className="shell-banner-icon animate-spin" />
        ) : (
          <AlertCircleIcon className="shell-banner-icon" />
        )}
        <div className="shell-banner-text">
          <strong>{content.title}</strong>
          {content.hint && <p className="shell-banner-hint">{content.hint}</p>}
          {content.detail && (
            <p className="shell-banner-detail">{content.detail}</p>
          )}
        </div>
      </div>
      <div className="shell-banner-actions">
        {onRetry && (
          <button type="button" className="shell-banner-btn" onClick={onRetry}>
            重试
          </button>
        )}
        <button
          type="button"
          className="shell-banner-btn shell-banner-close"
          aria-label="关闭提示"
          onClick={onClose}
        >
          <XIcon className="size-4" />
        </button>
      </div>
    </div>
  );
}
