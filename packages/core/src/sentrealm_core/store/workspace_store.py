"""Filesystem-backed workspace, project, and document stores (ADR-010)."""

from __future__ import annotations

import shutil
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sentrealm_core.store.errors import ConflictError, NotFoundError
from sentrealm_core.store.fs_utils import atomic_write_json, atomic_write_text, read_json
from sentrealm_core.workspace_models import (
    Document,
    DocumentDetail,
    DocumentMeta,
    DocumentResult,
    DocumentSummary,
    ExportDocumentResponse,
    Project,
    ProjectSummary,
    RecentDocumentItem,
    WorkspaceMeta,
    WorkspaceResponse,
)

SCHEMA_VERSION = 1
DEFAULT_PROJECT_NAME = "默认项目"
DEFAULT_DOCUMENT_TITLE = "未命名文稿"
_RESERVED_EXPORT_NAMES = frozenset({"source.txt", "result.json", "document.json"})
_INVALID_FILENAME_CHARS = set('<>:"/\\|?*')


def export_filename_from_title(title: str) -> str:
    """Build a safe .txt filename from a document title."""
    cleaned = "".join(
        "_" if ch in _INVALID_FILENAME_CHARS else ch for ch in title.strip()
    )
    cleaned = cleaned.strip(" .")
    if not cleaned:
        cleaned = "processed"
    filename = f"{cleaned}.txt"
    if filename.lower() in _RESERVED_EXPORT_NAMES:
        filename = f"{cleaned}-processed.txt"
    return filename


def default_workspace_path() -> Path:
    """Return gui workspace root; Windows uses Documents/SentRealm."""
    if sys.platform == "win32":
        path = Path.home() / "Documents" / "SentRealm"
    elif sys.platform == "darwin":
        path = Path.home() / "Documents" / "SentRealm"
    else:
        path = Path.home() / "Documents" / "SentRealm"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkspaceStore:
    """Manage workspace metadata plus project/document CRUD on disk."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_workspace_path()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def workspace_json(self) -> Path:
        return self.root / "workspace.json"

    @property
    def projects_dir(self) -> Path:
        return self.root / "projects"

    def ensure_initialized(self) -> WorkspaceResponse:
        if not self.workspace_json.is_file() or not any(self._iter_project_dirs()):
            self._create_default_structure()
        self.repair_meta()
        return self.get_workspace()

    def repair_meta(self) -> WorkspaceMeta:
        meta = self._load_meta()
        changed = False

        project_ids = {path.name for path in self._iter_project_dirs()}
        if meta.active_project_id not in project_ids:
            meta.active_project_id = self._pick_latest_project_id() or self._create_default_structure()[0]
            changed = True

        document_ids = {path.name for path in self._iter_document_dirs(meta.active_project_id)}
        if meta.active_document_id not in document_ids:
            meta.active_document_id = (
                self._pick_latest_document_id(meta.active_project_id)
                or self._create_blank_document(meta.active_project_id).meta.id
            )
            changed = True

        if changed:
            self._save_meta(meta)
        return meta

    def get_workspace(self) -> WorkspaceResponse:
        meta = self._load_meta()
        return WorkspaceResponse(
            root_path=str(self.root),
            schema_version=SCHEMA_VERSION,
            active_project_id=meta.active_project_id,
            active_document_id=meta.active_document_id,
            recent_projects=self.list_projects(),
            recent_documents=self._list_recent_documents(),
        )

    def set_active(self, project_id: str, document_id: str) -> WorkspaceResponse:
        if not self._project_json(project_id).is_file():
            raise NotFoundError(f"project not found: {project_id}")
        if not self._document_json(project_id, document_id).is_file():
            raise NotFoundError(f"document not found: {document_id}")
        self._save_meta(
            WorkspaceMeta(
                active_project_id=project_id,
                active_document_id=document_id,
            )
        )
        return self.get_workspace()

    def list_projects(self) -> list[ProjectSummary]:
        summaries: list[ProjectSummary] = []
        for project_dir in self._iter_project_dirs():
            project = self._load_project(project_dir.name)
            summaries.append(
                ProjectSummary(
                    id=project.id,
                    name=project.name,
                    updated_at=project.updated_at,
                    document_count=len(list(self._iter_document_dirs(project.id))),
                )
            )
        summaries.sort(key=lambda item: item.updated_at, reverse=True)
        return summaries

    def create_project(self, name: str) -> Project:
        now = _utc_now()
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            created_at=now,
            updated_at=now,
        )
        project_dir = self._project_dir(project.id)
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "documents").mkdir(exist_ok=True)
        atomic_write_json(self._project_json(project.id), project.model_dump(mode="json"))
        return project

    def get_project(self, project_id: str) -> Project:
        if not self._project_json(project_id).is_file():
            raise NotFoundError(f"project not found: {project_id}")
        return self._load_project(project_id)

    def rename_project(self, project_id: str, name: str) -> Project:
        project = self.get_project(project_id)
        project.name = name
        project.updated_at = _utc_now()
        atomic_write_json(self._project_json(project_id), project.model_dump(mode="json"))
        return project

    def delete_project(self, project_id: str) -> None:
        if not self._project_json(project_id).is_file():
            raise NotFoundError(f"project not found: {project_id}")
        if len(list(self._iter_project_dirs())) <= 1:
            raise ConflictError("不能删除最后一个项目")
        meta = self._load_meta()
        if meta.active_project_id == project_id:
            raise ConflictError("不能删除当前活动项目")
        shutil.rmtree(self._project_dir(project_id))

    def list_documents(self, project_id: str) -> list[DocumentSummary]:
        self.get_project(project_id)
        summaries: list[DocumentSummary] = []
        for document_dir in self._iter_document_dirs(project_id):
            meta = self._load_document_meta(project_id, document_dir.name)
            source = self._read_source(project_id, meta.id)
            summaries.append(
                DocumentSummary(
                    id=meta.id,
                    title=meta.title,
                    updated_at=meta.updated_at,
                    char_count=len(source),
                )
            )
        summaries.sort(key=lambda item: item.updated_at, reverse=True)
        return summaries

    def create_document(self, project_id: str, title: str = DEFAULT_DOCUMENT_TITLE) -> Document:
        self.get_project(project_id)
        return self._create_blank_document(project_id, title=title)

    def get_document_detail(self, project_id: str, document_id: str) -> DocumentDetail:
        meta = self._load_document_meta(project_id, document_id)
        return DocumentDetail(
            id=meta.id,
            project_id=meta.project_id,
            title=meta.title,
            source_text=self._read_source(project_id, document_id),
            created_at=meta.created_at,
            updated_at=meta.updated_at,
            result=self._read_result(project_id, document_id),
        )

    def update_document(
        self,
        project_id: str,
        document_id: str,
        *,
        title: str | None = None,
        source_text: str | None = None,
    ) -> DocumentDetail:
        meta = self._load_document_meta(project_id, document_id)
        if title is not None:
            meta.title = title
        if source_text is not None:
            atomic_write_text(self._source_txt(project_id, document_id), source_text)
        meta.updated_at = _utc_now()
        atomic_write_json(
            self._document_json(project_id, document_id),
            meta.model_dump(mode="json"),
        )
        self._touch_project(project_id)
        return self.get_document_detail(project_id, document_id)

    def delete_document(self, project_id: str, document_id: str) -> None:
        if not self._document_json(project_id, document_id).is_file():
            raise NotFoundError(f"document not found: {document_id}")
        meta = self._load_meta()
        if (
            meta.active_project_id == project_id
            and meta.active_document_id == document_id
        ):
            raise ConflictError(
                "不能删除当前正在编辑的文稿，请先切换到其他文稿或新建一篇"
            )
        shutil.rmtree(self._document_dir(project_id, document_id))
        self._touch_project(project_id)

    def save_document_result(
        self,
        project_id: str,
        document_id: str,
        *,
        processed: str,
        line_count: int,
        flagged_lines: list[int],
    ) -> DocumentResult:
        self._load_document_meta(project_id, document_id)
        result = DocumentResult(
            processed_at=_utc_now(),
            line_count=line_count,
            flagged_lines=flagged_lines,
            processed=processed,
        )
        atomic_write_json(
            self._result_json(project_id, document_id),
            result.model_dump(mode="json"),
        )
        return result

    def export_document_txt(
        self,
        project_id: str,
        document_id: str,
        *,
        processed: str,
    ) -> ExportDocumentResponse:
        meta = self._load_document_meta(project_id, document_id)
        filename = export_filename_from_title(meta.title)
        path = self._document_dir(project_id, document_id) / filename
        atomic_write_text(path, processed)
        return ExportDocumentResponse(path=str(path.resolve()), filename=filename)

    def _create_default_structure(self) -> tuple[str, str]:
        project = self.create_project(DEFAULT_PROJECT_NAME)
        document = self._create_blank_document(project.id)
        meta = WorkspaceMeta(
            active_project_id=project.id,
            active_document_id=document.meta.id,
        )
        self._save_meta(meta)
        return project.id, document.meta.id

    def _create_blank_document(
        self,
        project_id: str,
        *,
        title: str = DEFAULT_DOCUMENT_TITLE,
    ) -> Document:
        now = _utc_now()
        meta = DocumentMeta(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        document_dir = self._document_dir(project_id, meta.id)
        document_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._document_json(project_id, meta.id), meta.model_dump(mode="json"))
        atomic_write_text(self._source_txt(project_id, meta.id), "")
        self._touch_project(project_id)
        return Document(meta=meta, source_text="")

    def _list_recent_documents(self, limit: int = 20) -> list[RecentDocumentItem]:
        items: list[RecentDocumentItem] = []
        for project_dir in self._iter_project_dirs():
            project_id = project_dir.name
            for document_dir in self._iter_document_dirs(project_id):
                meta = self._load_document_meta(project_id, document_dir.name)
                items.append(
                    RecentDocumentItem(
                        project_id=project_id,
                        document_id=meta.id,
                        title=meta.title,
                        updated_at=meta.updated_at,
                    )
                )
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items[:limit]

    def _pick_latest_project_id(self) -> str | None:
        projects = self.list_projects()
        return projects[0].id if projects else None

    def _pick_latest_document_id(self, project_id: str) -> str | None:
        documents = self.list_documents(project_id)
        return documents[0].id if documents else None

    def _load_meta(self) -> WorkspaceMeta:
        if not self.workspace_json.is_file():
            if self._iter_project_dirs():
                project_id = self._pick_latest_project_id()
                assert project_id is not None
                document_id = self._pick_latest_document_id(project_id)
                if document_id is None:
                    document_id = self._create_blank_document(project_id).meta.id
                meta = WorkspaceMeta(
                    active_project_id=project_id,
                    active_document_id=document_id,
                )
                self._save_meta(meta)
                return meta
            project_id, document_id = self._create_default_structure()
            return WorkspaceMeta(
                active_project_id=project_id,
                active_document_id=document_id,
            )
        data = read_json(self.workspace_json)
        return WorkspaceMeta.model_validate(data)

    def _save_meta(self, meta: WorkspaceMeta) -> None:
        atomic_write_json(self.workspace_json, meta.model_dump(mode="json"))

    def _load_project(self, project_id: str) -> Project:
        return Project.model_validate(read_json(self._project_json(project_id)))

    def _load_document_meta(self, project_id: str, document_id: str) -> DocumentMeta:
        if not self._document_json(project_id, document_id).is_file():
            raise NotFoundError(f"document not found: {document_id}")
        return DocumentMeta.model_validate(read_json(self._document_json(project_id, document_id)))

    def _read_source(self, project_id: str, document_id: str) -> str:
        path = self._source_txt(project_id, document_id)
        if not path.is_file():
            return ""
        return path.read_text(encoding="utf-8")

    def _read_result(self, project_id: str, document_id: str) -> DocumentResult | None:
        path = self._result_json(project_id, document_id)
        if not path.is_file():
            return None
        return DocumentResult.model_validate(read_json(path))

    def _touch_project(self, project_id: str) -> None:
        project = self.get_project(project_id)
        project.updated_at = _utc_now()
        atomic_write_json(self._project_json(project_id), project.model_dump(mode="json"))

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def _project_json(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def _documents_dir(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "documents"

    def _document_dir(self, project_id: str, document_id: str) -> Path:
        return self._documents_dir(project_id) / document_id

    def _document_json(self, project_id: str, document_id: str) -> Path:
        return self._document_dir(project_id, document_id) / "document.json"

    def _source_txt(self, project_id: str, document_id: str) -> Path:
        return self._document_dir(project_id, document_id) / "source.txt"

    def _result_json(self, project_id: str, document_id: str) -> Path:
        return self._document_dir(project_id, document_id) / "result.json"

    def _iter_project_dirs(self) -> list[Path]:
        if not self.projects_dir.is_dir():
            return []
        return sorted(path for path in self.projects_dir.iterdir() if path.is_dir())

    def _iter_document_dirs(self, project_id: str) -> list[Path]:
        documents_dir = self._documents_dir(project_id)
        if not documents_dir.is_dir():
            return []
        return sorted(path for path in documents_dir.iterdir() if path.is_dir())
