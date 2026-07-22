import { FileTextIcon } from "lucide-react";
import { useEffect, useState } from "react";

type DocTitleInputProps = {
  title: string;
  disabled?: boolean;
  onCommit: (title: string) => void;
};

export function DocTitleInput({ title, disabled, onCommit }: DocTitleInputProps) {
  const [draft, setDraft] = useState(title);

  useEffect(() => {
    setDraft(title);
  }, [title]);

  const commit = () => {
    const next = draft.trim() || "未命名文稿";
    setDraft(next);
    if (next !== title) onCommit(next);
  };

  return (
    <div className="shell-doc-name">
      <FileTextIcon className="shell-doc-name-icon size-4" />
      <input
        className="shell-doc-name-input"
        value={draft}
        disabled={disabled}
        aria-label="文稿标题"
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => commit()}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            (e.target as HTMLInputElement).blur();
          }
        }}
      />
    </div>
  );
}
