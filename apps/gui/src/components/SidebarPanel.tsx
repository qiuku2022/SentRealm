import {
  FileTextIcon,
  MoreHorizontalIcon,
  PanelLeftCloseIcon,
  PanelLeftOpenIcon,
  PlusIcon,
  SearchIcon,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
  type TransitionEvent,
} from "react";

import { SettingsButton } from "@/components/SettingsDrawer";
import { formatRelativeTime } from "@/lib/text-utils";
import type { RecentDocumentItem } from "@/lib/types";

type SidebarPanelProps = {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  searchInputRef: RefObject<HTMLInputElement | null>;
  documents: RecentDocumentItem[];
  activeDocumentId: string | null;
  healthClass: string;
  healthLabel: string;
  healthMeta?: string;
  onCreateDocument: () => void;
  onSelectDocument: (item: RecentDocumentItem) => void;
  onRenameDocument: (item: RecentDocumentItem, title: string) => void;
  onDeleteDocument: (item: RecentDocumentItem) => void;
  onOpenSettings: () => void;
};

type DisplayDoc = {
  item: RecentDocumentItem;
  exiting: boolean;
};

function docKey(item: RecentDocumentItem) {
  return `${item.project_id}:${item.document_id}`;
}

export function SidebarPanel({
  collapsed,
  onToggleCollapsed,
  searchQuery,
  onSearchQueryChange,
  searchInputRef,
  documents,
  activeDocumentId,
  healthClass,
  healthLabel,
  healthMeta,
  onCreateDocument,
  onSelectDocument,
  onRenameDocument,
  onDeleteDocument,
  onOpenSettings,
}: SidebarPanelProps) {
  const [menuDocId, setMenuDocId] = useState<string | null>(null);
  const [menuPresentId, setMenuPresentId] = useState<string | null>(null);
  const [menuActive, setMenuActive] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [exitingDocs, setExitingDocs] = useState<
    Map<string, RecentDocumentItem>
  >(() => new Map());
  const [listOrder, setListOrder] = useState<string[]>(() =>
    documents.map((doc) => doc.document_id),
  );
  const [rowOpenIds, setRowOpenIds] = useState<Set<string>>(
    () => new Set(documents.map((doc) => doc.document_id)),
  );
  const menuRef = useRef<HTMLDivElement>(null);
  const prevDocumentsRef = useRef(documents);
  const skipEnterRef = useRef(true);

  const docById = useMemo(() => {
    const map = new Map<string, RecentDocumentItem>();
    for (const doc of documents) map.set(doc.document_id, doc);
    for (const [id, doc] of exitingDocs) map.set(id, doc);
    return map;
  }, [documents, exitingDocs]);

  const displayDocuments = useMemo<DisplayDoc[]>(() => {
    return listOrder
      .map((id) => {
        const item = docById.get(id);
        if (!item) return null;
        return {
          item,
          exiting:
            exitingDocs.has(id) &&
            !documents.some((doc) => doc.document_id === id),
        };
      })
      .filter((entry): entry is DisplayDoc => entry != null);
  }, [docById, documents, exitingDocs, listOrder]);

  const filteredDocuments = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return displayDocuments;
    return displayDocuments.filter(
      ({ item, exiting }) =>
        exiting || item.title.toLowerCase().includes(q),
    );
  }, [displayDocuments, searchQuery]);

  const finalizeExit = useCallback((documentId: string) => {
    setExitingDocs((current) => {
      if (!current.has(documentId)) return current;
      const next = new Map(current);
      next.delete(documentId);
      return next;
    });
    setListOrder((order) => order.filter((id) => id !== documentId));
  }, []);

  useEffect(() => {
    const prev = prevDocumentsRef.current;
    const prevIds = new Set(prev.map((doc) => doc.document_id));
    const currIds = documents.map((doc) => doc.document_id);
    const currSet = new Set(currIds);

    if (skipEnterRef.current) {
      skipEnterRef.current = false;
      prevDocumentsRef.current = documents;
      setListOrder(currIds);
      setRowOpenIds(new Set(currIds));
      return;
    }

    const added = documents.filter((doc) => !prevIds.has(doc.document_id));
    const removed = prev.filter((doc) => !currSet.has(doc.document_id));

    if (removed.length > 0) {
      setExitingDocs((current) => {
        const next = new Map(current);
        for (const doc of removed) next.set(doc.document_id, doc);
        return next;
      });
      setRowOpenIds((current) => {
        const next = new Set(current);
        for (const doc of removed) next.delete(doc.document_id);
        return next;
      });
    }

    if (added.length > 0 || removed.length > 0) {
      setListOrder((order) => {
        const exitingIds = order.filter((id) => !currSet.has(id));
        const next = [...currIds];
        for (const id of exitingIds) {
          if (next.includes(id)) continue;
          const oldPos = order.indexOf(id);
          next.splice(Math.min(oldPos, next.length), 0, id);
        }
        return next;
      });
    }

    if (added.length > 0) {
      const frame = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setRowOpenIds((current) => {
            const next = new Set(current);
            for (const doc of added) next.add(doc.document_id);
            return next;
          });
        });
      });
      prevDocumentsRef.current = documents;
      return () => cancelAnimationFrame(frame);
    }

    prevDocumentsRef.current = documents;
  }, [documents]);

  useEffect(() => {
    if (menuDocId) {
      setMenuPresentId(menuDocId);
      const frame = requestAnimationFrame(() => {
        requestAnimationFrame(() => setMenuActive(true));
      });
      return () => cancelAnimationFrame(frame);
    }
    setMenuActive(false);
  }, [menuDocId]);

  useEffect(() => {
    if (!menuDocId) return;
    const onDocClick = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuDocId(null);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [menuDocId]);

  const startRename = (item: RecentDocumentItem) => {
    setMenuDocId(null);
    setRenamingId(item.document_id);
    setRenameDraft(item.title);
  };

  const commitRename = (item: RecentDocumentItem) => {
    const next = renameDraft.trim() || "未命名文稿";
    setRenamingId(null);
    if (next !== item.title) onRenameDocument(item, next);
  };

  const renderDocRow = ({ item, exiting }: DisplayDoc) => {
    const isActive = item.document_id === activeDocumentId;
    const isRenaming = renamingId === item.document_id;
    const menuOpen = menuDocId === item.document_id;
    const menuVisible = menuPresentId === item.document_id;
    const rowOpen = rowOpenIds.has(item.document_id);

    const handleRowTransitionEnd = (event: TransitionEvent<HTMLDivElement>) => {
      if (event.target !== event.currentTarget) return;
      if (!exiting || rowOpen) return;
      if (event.propertyName === "opacity") {
        finalizeExit(item.document_id);
      }
    };

    if (collapsed) {
      return (
        <div
          key={docKey(item)}
          className={`shell-doc-row-wrap ${rowOpen ? "is-open" : ""}`}
          onTransitionEnd={handleRowTransitionEnd}
        >
          <div className="shell-doc-row-wrap-inner">
            <button
              type="button"
              title={item.title}
              className={`shell-doc-item is-compact ${
                isActive ? "is-active" : ""
              }`}
              onClick={() => onSelectDocument(item)}
            >
              <FileTextIcon className="size-4" />
            </button>
          </div>
        </div>
      );
    }

    return (
      <div
        key={docKey(item)}
        className={`shell-doc-row-wrap ${rowOpen ? "is-open" : ""} ${
          menuOpen || menuVisible ? "is-menu-open" : ""
        }`}
        onTransitionEnd={handleRowTransitionEnd}
      >
        <div className="shell-doc-row-wrap-inner">
          <div className={`shell-doc-row ${isActive ? "is-active" : ""}`}>
            {isRenaming ? (
              <input
                className="shell-doc-rename-input"
                value={renameDraft}
                autoFocus
                onChange={(e) => setRenameDraft(e.target.value)}
                onBlur={() => commitRename(item)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    commitRename(item);
                  }
                  if (e.key === "Escape") setRenamingId(null);
                }}
              />
            ) : (
              <button
                type="button"
                className="shell-doc-item shell-doc-item-main"
                onClick={() => onSelectDocument(item)}
              >
                <div className="shell-doc-title">{item.title}</div>
                <div className="shell-doc-meta">
                  {formatRelativeTime(item.updated_at)}
                </div>
              </button>
            )}

            {!isRenaming && (
              <div
                className="shell-doc-menu-wrap"
                ref={menuDocId === item.document_id ? menuRef : undefined}
              >
                <button
                  type="button"
                  className={`shell-doc-menu-btn ${menuOpen ? "is-open" : ""}`}
                  aria-label="文稿操作"
                  aria-expanded={menuOpen}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (menuOpen) {
                      setMenuDocId(null);
                      return;
                    }
                    setMenuDocId(item.document_id);
                    setMenuPresentId(item.document_id);
                  }}
                >
                  <MoreHorizontalIcon className="size-4" />
                </button>
                {menuVisible && (
                  <div
                    className={`shell-doc-menu ${menuActive ? "is-open" : ""}`}
                    role="menu"
                    onTransitionEnd={(event) => {
                      if (event.target !== event.currentTarget) return;
                      if (!menuActive && event.propertyName === "opacity") {
                        setMenuPresentId(null);
                      }
                    }}
                  >
                    <button
                      type="button"
                      role="menuitem"
                      onClick={() => startRename(item)}
                    >
                      重命名
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="is-danger"
                      onClick={() => {
                        setMenuDocId(null);
                        onDeleteDocument(item);
                      }}
                    >
                      删除
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const showEmptyState =
    documents.length === 0 && exitingDocs.size === 0 && !collapsed;

  return (
    <aside className={`shell-side ${collapsed ? "is-collapsed" : ""}`}>
      <div className="shell-side-head">
        <div className="shell-brand">
          <span className="shell-brand-mark">S</span>
          {!collapsed && <span className="shell-brand-name">SentRealm</span>}
          <button
            type="button"
            className="shell-side-toggle"
            aria-label={collapsed ? "展开侧栏" : "折叠侧栏"}
            onClick={onToggleCollapsed}
          >
            {collapsed ? (
              <PanelLeftOpenIcon />
            ) : (
              <PanelLeftCloseIcon />
            )}
          </button>
        </div>
        {!collapsed && (
          <p className="shell-side-note">
            文稿保存在本机 Documents/SentRealm，可在项目间切换与恢复。
          </p>
        )}
      </div>

      {!collapsed && (
        <div className="shell-side-search">
          <div className="shell-side-search-box">
            <SearchIcon className="shell-side-search-icon size-4" />
            <input
              ref={searchInputRef}
              type="search"
              className="shell-side-search-input"
              placeholder="搜索文稿…"
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
            />
            <span className="shell-kbd-hint">/</span>
          </div>
        </div>
      )}

      <div className="shell-side-body">
        <button
          type="button"
          className={`shell-btn-go shell-btn-new ${collapsed ? "is-icon" : ""}`}
          title="新建文稿"
          onClick={onCreateDocument}
        >
          <PlusIcon className="size-4 inline" />
          {!collapsed && " 新建文稿"}
        </button>

        {!collapsed && (
          <div className="shell-side-group">
            最近文稿 <span className="shell-side-count">{documents.length}</span>
          </div>
        )}

        {showEmptyState && (
          <div className="shell-side-empty">
            <FileTextIcon className="shell-side-empty-icon size-8" />
            <p>还没有文稿</p>
            <p className="shell-side-empty-hint">点击上方按钮新建，或粘贴口播稿开始。</p>
          </div>
        )}

        {!collapsed && documents.length > 0 && filteredDocuments.length === 0 && (
          <div className="shell-side-empty">
            <p>无匹配文稿</p>
            <p className="shell-side-empty-hint">试试其他关键词，或清空搜索。</p>
          </div>
        )}

        {filteredDocuments.map(renderDocRow)}
      </div>

      <div className="shell-side-foot">
        <div
          className={`shell-health ${healthClass}`}
          title={healthMeta ? `${healthLabel} · ${healthMeta}` : healthLabel}
        >
          <span className="dot" />
          {!collapsed && (
            <>
              <span className="shell-health-ttl">{healthLabel}</span>
              {healthMeta && (
                <span className="shell-health-meta">{healthMeta}</span>
              )}
            </>
          )}
        </div>
        <SettingsButton onClick={onOpenSettings} collapsed={collapsed} />
      </div>
    </aside>
  );
}
