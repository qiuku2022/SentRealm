"""Tests for document CRUD and result persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentrealm_core.store.errors import ConflictError, NotFoundError
from sentrealm_core.store.fs_utils import read_json
from sentrealm_core.store.workspace_store import WorkspaceStore


@pytest.fixture
def store(tmp_path: Path) -> tuple[WorkspaceStore, str]:
    ws = WorkspaceStore(root=tmp_path / "workspace")
    workspace = ws.ensure_initialized()
    return ws, workspace.active_project_id


def test_create_and_update_document(store: tuple[WorkspaceStore, str]) -> None:
    ws, project_id = store
    document = ws.create_document(project_id, title="第一篇")

    detail = ws.update_document(
        project_id,
        document.meta.id,
        title="改标题",
        source_text="大家好",
    )

    assert detail.title == "改标题"
    assert detail.source_text == "大家好"
    assert (ws.root / "projects" / project_id / "documents" / document.meta.id / "source.txt").is_file()


def test_save_document_result_without_original(store: tuple[WorkspaceStore, str]) -> None:
    ws, project_id = store
    document = ws.create_document(project_id)
    result = ws.save_document_result(
        project_id,
        document.meta.id,
        processed="第一行\n第二行",
        line_count=2,
        flagged_lines=[1],
    )

    assert result.line_count == 2
    payload = read_json(ws._result_json(project_id, document.meta.id))
    assert "original" not in payload
    assert payload["processed"] == "第一行\n第二行"


def test_get_document_detail_includes_null_result(store: tuple[WorkspaceStore, str]) -> None:
    ws, project_id = store
    document = ws.create_document(project_id)
    detail = ws.get_document_detail(project_id, document.meta.id)

    assert detail.result is None


def test_cannot_delete_active_document(store: tuple[WorkspaceStore, str]) -> None:
    ws, project_id = store
    workspace = ws.get_workspace()
    with pytest.raises(ConflictError):
        ws.delete_document(project_id, workspace.active_document_id)


def test_delete_non_active_document(store: tuple[WorkspaceStore, str]) -> None:
    ws, project_id = store
    extra = ws.create_document(project_id, title="临时稿")
    ws.delete_document(project_id, extra.meta.id)
    with pytest.raises(NotFoundError):
        ws.get_document_detail(project_id, extra.meta.id)
