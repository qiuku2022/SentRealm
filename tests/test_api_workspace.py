"""HTTP integration tests for workspace API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.gui.api.main import create_app
from sentrealm_core import SqliteSettingsStore
from sentrealm_core.store import WorkspaceStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    store = SqliteSettingsStore(db_path=tmp_path / "settings.db")
    workspace = WorkspaceStore(root=tmp_path / "workspace")
    return TestClient(create_app(store=store, workspace_store=workspace))


def test_get_workspace_initializes_defaults(client: TestClient) -> None:
    response = client.get("/api/v1/workspace")

    assert response.status_code == 200
    data = response.json()
    assert data["schema_version"] == 1
    assert data["active_project_id"]
    assert len(data["recent_projects"]) >= 1


def test_document_crud_via_http(client: TestClient) -> None:
    workspace = client.get("/api/v1/workspace").json()
    project_id = workspace["active_project_id"]

    create = client.post(
        f"/api/v1/projects/{project_id}/documents",
        json={"title": "HTTP 文稿"},
    )
    assert create.status_code == 200
    document_id = create.json()["meta"]["id"]

    patch = client.patch(
        f"/api/v1/projects/{project_id}/documents/{document_id}",
        json={"source_text": "测试正文"},
    )
    assert patch.status_code == 200
    assert patch.json()["source_text"] == "测试正文"


def test_put_document_result_via_http(client: TestClient) -> None:
    workspace = client.get("/api/v1/workspace").json()
    project_id = workspace["active_project_id"]
    document_id = workspace["active_document_id"]

    response = client.put(
        f"/api/v1/projects/{project_id}/documents/{document_id}/result",
        json={
            "schema_version": 1,
            "processed_at": "2026-07-18T00:00:00+00:00",
            "line_count": 2,
            "flagged_lines": [],
            "processed": "第一行\n第二行",
        },
    )

    assert response.status_code == 200
    assert response.json()["processed"] == "第一行\n第二行"


def test_export_document_via_http(client: TestClient, tmp_path: Path) -> None:
    workspace = client.get("/api/v1/workspace").json()
    project_id = workspace["active_project_id"]
    document_id = workspace["active_document_id"]

    client.patch(
        f"/api/v1/projects/{project_id}/documents/{document_id}",
        json={"title": "HTTP 导出"},
    )

    response = client.post(
        f"/api/v1/projects/{project_id}/documents/{document_id}/export",
        json={"processed": "导出内容\n第二行"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "HTTP 导出.txt"
    path = Path(data["path"])
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == "导出内容\n第二行"
    assert path.parent == (
        tmp_path / "workspace" / "projects" / project_id / "documents" / document_id
    )


def test_preprocess_does_not_write_result_json(client: TestClient, tmp_path: Path) -> None:
    workspace = client.get("/api/v1/workspace").json()
    project_id = workspace["active_project_id"]
    document_id = workspace["active_document_id"]
    result_path = (
        tmp_path
        / "workspace"
        / "projects"
        / project_id
        / "documents"
        / document_id
        / "result.json"
    )

    response = client.post(
        "/api/v1/preprocess",
        json={"text": "大家好，欢迎来到今天的节目。"},
    )
    assert response.status_code == 200
    assert not result_path.is_file()


def test_delete_active_document_returns_409(client: TestClient) -> None:
    workspace = client.get("/api/v1/workspace").json()
    project_id = workspace["active_project_id"]
    document_id = workspace["active_document_id"]

    response = client.delete(
        f"/api/v1/projects/{project_id}/documents/{document_id}",
    )
    assert response.status_code == 409
