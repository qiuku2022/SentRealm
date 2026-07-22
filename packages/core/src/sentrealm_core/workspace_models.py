"""Workspace domain models aligned with docs/api/openapi.yaml."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

DEFAULT_DOCUMENT_TITLE = "未命名文稿"


class ProjectSummary(BaseModel):
    id: str
    name: str
    updated_at: datetime
    document_count: int = Field(ge=0)


class Project(BaseModel):
    schema_version: int = 1
    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class DocumentMeta(BaseModel):
    schema_version: int = 1
    id: str
    project_id: str
    title: str
    created_at: datetime
    updated_at: datetime


class Document(BaseModel):
    meta: DocumentMeta
    source_text: str = ""


class DocumentSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime
    char_count: int | None = Field(default=None, ge=0)


class DocumentResult(BaseModel):
    schema_version: int = 1
    processed_at: datetime
    line_count: int = Field(ge=0)
    flagged_lines: list[int] = Field(default_factory=list)
    processed: str


class DocumentDetail(BaseModel):
    id: str
    project_id: str
    title: str
    source_text: str
    created_at: datetime
    updated_at: datetime
    result: DocumentResult | None = None


class RecentDocumentItem(BaseModel):
    project_id: str
    document_id: str
    title: str
    updated_at: datetime


class WorkspaceResponse(BaseModel):
    root_path: str
    schema_version: int = 1
    active_project_id: str
    active_document_id: str
    recent_projects: list[ProjectSummary]
    recent_documents: list[RecentDocumentItem]


class WorkspaceMeta(BaseModel):
    schema_version: int = 1
    active_project_id: str
    active_document_id: str


class SetActiveRequest(BaseModel):
    project_id: str
    document_id: str


class CreateProjectRequest(BaseModel):
    name: str


class RenameProjectRequest(BaseModel):
    name: str


class CreateDocumentRequest(BaseModel):
    title: str = DEFAULT_DOCUMENT_TITLE


class UpdateDocumentRequest(BaseModel):
    title: str | None = None
    source_text: str | None = None


class ExportDocumentRequest(BaseModel):
    processed: str


class ExportDocumentResponse(BaseModel):
    path: str
    filename: str
