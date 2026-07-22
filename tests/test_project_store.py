"""Tests for project CRUD in workspace store."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentrealm_core.store.errors import ConflictError, NotFoundError
from sentrealm_core.store.workspace_store import WorkspaceStore


@pytest.fixture
def store(tmp_path: Path) -> WorkspaceStore:
    ws = WorkspaceStore(root=tmp_path / "workspace")
    ws.ensure_initialized()
    return ws


def test_create_and_get_project(store: WorkspaceStore) -> None:
    project = store.create_project("口播项目")

    loaded = store.get_project(project.id)
    assert loaded.name == "口播项目"
    assert loaded.schema_version == 1


def test_rename_project(store: WorkspaceStore) -> None:
    project = store.create_project("旧名称")
    renamed = store.rename_project(project.id, "新名称")

    assert renamed.name == "新名称"
    assert store.get_project(project.id).name == "新名称"


def test_delete_non_active_project(store: WorkspaceStore) -> None:
    extra = store.create_project("可删项目")
    store.delete_project(extra.id)
    with pytest.raises(NotFoundError):
        store.get_project(extra.id)


def test_cannot_delete_last_project(store: WorkspaceStore) -> None:
    projects = store.list_projects()
    only_id = projects[0].id
    with pytest.raises(ConflictError):
        store.delete_project(only_id)


def test_cannot_delete_active_project(store: WorkspaceStore) -> None:
    store.create_project("第二个项目")
    workspace = store.get_workspace()
    with pytest.raises(ConflictError):
        store.delete_project(workspace.active_project_id)
