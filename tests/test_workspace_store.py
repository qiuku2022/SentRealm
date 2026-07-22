"""Tests for workspace store initialization and repair."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentrealm_core.store.errors import NotFoundError
from sentrealm_core.store.fs_utils import read_json
from sentrealm_core.store.workspace_store import WorkspaceStore, export_filename_from_title


@pytest.fixture
def store(tmp_path: Path) -> WorkspaceStore:
    return WorkspaceStore(root=tmp_path / "workspace")


def test_ensure_initialized_creates_default_structure(store: WorkspaceStore) -> None:
    response = store.ensure_initialized()

    assert response.schema_version == 1
    assert response.active_project_id
    assert response.active_document_id
    assert len(response.recent_projects) == 1
    assert store.workspace_json.is_file()
    assert (store.root / "projects").is_dir()


def test_repair_meta_fixes_missing_active_document(store: WorkspaceStore) -> None:
    response = store.ensure_initialized()
    project_id = response.active_project_id

    meta = store._load_meta()
    meta.active_document_id = "00000000-0000-0000-0000-000000000099"
    store._save_meta(meta)

    repaired = store.repair_meta()
    assert store._document_json(project_id, repaired.active_document_id).is_file()


def test_atomic_json_round_trip(store: WorkspaceStore) -> None:
    store.ensure_initialized()
    payload = read_json(store.workspace_json)
    assert payload["schema_version"] == 1
    assert "active_project_id" in payload


def test_set_active_unknown_project_raises(store: WorkspaceStore) -> None:
    store.ensure_initialized()
    with pytest.raises(NotFoundError):
        store.set_active(
            "00000000-0000-0000-0000-000000000099",
            "00000000-0000-0000-0000-000000000001",
        )


def test_export_filename_from_title_sanitizes_and_avoids_reserved() -> None:
    assert export_filename_from_title("我的文稿") == "我的文稿.txt"
    assert export_filename_from_title("  a/b:c*d  ") == "a_b_c_d.txt"
    assert export_filename_from_title("   ") == "processed.txt"
    assert export_filename_from_title("source") == "source-processed.txt"
    assert export_filename_from_title("Source") == "Source-processed.txt"


def test_export_document_txt_writes_beside_source(store: WorkspaceStore) -> None:
    response = store.ensure_initialized()
    project_id = response.active_project_id
    document_id = response.active_document_id
    store.update_document(project_id, document_id, title="导出示例")

    exported = store.export_document_txt(
        project_id,
        document_id,
        processed="第一行\n第二行",
    )

    assert exported.filename == "导出示例.txt"
    path = Path(exported.path)
    assert path.is_file()
    assert path.parent == store._document_dir(project_id, document_id)
    assert path.read_text(encoding="utf-8") == "第一行\n第二行"
    assert store._source_txt(project_id, document_id).is_file()


def test_export_document_txt_unknown_document_raises(store: WorkspaceStore) -> None:
    response = store.ensure_initialized()
    with pytest.raises(NotFoundError):
        store.export_document_txt(
            response.active_project_id,
            "00000000-0000-0000-0000-000000000099",
            processed="x",
        )
