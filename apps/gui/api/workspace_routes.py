"""HTTP routes for workspace persistence (ADR-010)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from sentrealm_core.store.errors import ConflictError, NotFoundError, WorkspaceStoreError
from sentrealm_core.store.workspace_store import WorkspaceStore
from sentrealm_core.workspace_models import (
    CreateDocumentRequest,
    CreateProjectRequest,
    Document,
    DocumentDetail,
    DocumentResult,
    DocumentSummary,
    ExportDocumentRequest,
    ExportDocumentResponse,
    Project,
    ProjectSummary,
    RenameProjectRequest,
    SetActiveRequest,
    UpdateDocumentRequest,
    WorkspaceResponse,
)

from apps.gui.api.dependencies import WorkspaceDep

workspace_router = APIRouter(prefix="/api/v1")


def _handle_store_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc


@workspace_router.get("/workspace", response_model=WorkspaceResponse)
def get_workspace(store: WorkspaceDep) -> WorkspaceResponse:
    return store.ensure_initialized()


@workspace_router.put("/workspace/active", response_model=WorkspaceResponse)
def put_workspace_active(body: SetActiveRequest, store: WorkspaceDep) -> WorkspaceResponse:
    try:
        return store.set_active(body.project_id, body.document_id)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.get("/projects", response_model=list[ProjectSummary])
def list_projects(store: WorkspaceDep) -> list[ProjectSummary]:
    store.ensure_initialized()
    return store.list_projects()


@workspace_router.post("/projects", response_model=Project)
def create_project(body: CreateProjectRequest, store: WorkspaceDep) -> Project:
    store.ensure_initialized()
    return store.create_project(body.name)


@workspace_router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str, store: WorkspaceDep) -> Project:
    try:
        store.ensure_initialized()
        return store.get_project(project_id)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.patch("/projects/{project_id}", response_model=Project)
def rename_project(
    project_id: str,
    body: RenameProjectRequest,
    store: WorkspaceDep,
) -> Project:
    try:
        store.ensure_initialized()
        return store.rename_project(project_id, body.name)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str, store: WorkspaceDep) -> Response:
    try:
        store.ensure_initialized()
        store.delete_project(project_id)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc
    return Response(status_code=204)


@workspace_router.get(
    "/projects/{project_id}/documents",
    response_model=list[DocumentSummary],
)
def list_documents(project_id: str, store: WorkspaceDep) -> list[DocumentSummary]:
    try:
        store.ensure_initialized()
        return store.list_documents(project_id)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.post("/projects/{project_id}/documents", response_model=Document)
def create_document(
    project_id: str,
    body: CreateDocumentRequest,
    store: WorkspaceDep,
) -> Document:
    try:
        store.ensure_initialized()
        return store.create_document(project_id, title=body.title)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.get(
    "/projects/{project_id}/documents/{document_id}",
    response_model=DocumentDetail,
)
def get_document(
    project_id: str,
    document_id: str,
    store: WorkspaceDep,
) -> DocumentDetail:
    try:
        store.ensure_initialized()
        return store.get_document_detail(project_id, document_id)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.patch(
    "/projects/{project_id}/documents/{document_id}",
    response_model=DocumentDetail,
)
def update_document(
    project_id: str,
    document_id: str,
    body: UpdateDocumentRequest,
    store: WorkspaceDep,
) -> DocumentDetail:
    try:
        store.ensure_initialized()
        return store.update_document(
            project_id,
            document_id,
            title=body.title,
            source_text=body.source_text,
        )
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.delete(
    "/projects/{project_id}/documents/{document_id}",
    status_code=204,
)
def delete_document(
    project_id: str,
    document_id: str,
    store: WorkspaceDep,
) -> Response:
    try:
        store.ensure_initialized()
        store.delete_document(project_id, document_id)
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc
    return Response(status_code=204)


@workspace_router.put(
    "/projects/{project_id}/documents/{document_id}/result",
    response_model=DocumentResult,
)
def put_document_result(
    project_id: str,
    document_id: str,
    body: DocumentResult,
    store: WorkspaceDep,
) -> DocumentResult:
    try:
        store.ensure_initialized()
        return store.save_document_result(
            project_id,
            document_id,
            processed=body.processed,
            line_count=body.line_count,
            flagged_lines=body.flagged_lines,
        )
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc


@workspace_router.post(
    "/projects/{project_id}/documents/{document_id}/export",
    response_model=ExportDocumentResponse,
)
def export_document(
    project_id: str,
    document_id: str,
    body: ExportDocumentRequest,
    store: WorkspaceDep,
) -> ExportDocumentResponse:
    try:
        store.ensure_initialized()
        return store.export_document_txt(
            project_id,
            document_id,
            processed=body.processed,
        )
    except WorkspaceStoreError as exc:
        raise _handle_store_error(exc) from exc
