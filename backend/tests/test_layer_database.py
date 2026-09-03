from __future__ import annotations

import json
from pathlib import Path

import pytest

from terralab3d.domain.identifiers import ResourceId
from terralab3d.infrastructure.resources.layer_database import LayerDatabase


def _descriptor() -> dict[str, object]:
    return {
        "id": "sky.test",
        "name": "Test layer",
        "description": "Fixture",
        "domain": "sky",
        "category": "deep_sky",
        "provider": "TerraLab3D",
        "acquisitionKind": "STATIC_FILE",
        "citation": "Fixture",
        "license": "Test",
        "variants": [{"id": "default", "title": "Default"}],
    }


def _write_catalog(appdata: Path, catalog: object) -> Path:
    path = appdata / "TerraLab3D" / "layers.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path


def test_loads_versioned_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _write_catalog(tmp_path, {"schemaVersion": 2, "layers": [_descriptor()]})

    database = LayerDatabase()

    assert database.get_descriptor(ResourceId("sky.test")) is not None


def test_loads_legacy_list_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _write_catalog(tmp_path, [_descriptor()])

    database = LayerDatabase()

    assert database.get_descriptor(ResourceId("sky.test")) is not None


def test_save_writes_versioned_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    path = _write_catalog(tmp_path, [_descriptor()])
    database = LayerDatabase()

    database.save()

    catalog = json.loads(path.read_text(encoding="utf-8"))
    assert catalog["schemaVersion"] == 2
    assert [item["id"] for item in catalog["layers"]] == ["sky.test"]


def test_public_snapshot_omits_backend_only_parametric_plan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    descriptor = _descriptor()
    descriptor["acquisitionKind"] = "PARAMETRIC_DOWNLOAD"
    descriptor["variants"] = [{
        "id": "default",
        "title": "Default",
        "sourceUrls": ["https://example.test/internal-part-1"],
        "metadata": {"parametricPlan": "x" * 10_000, "publicFlag": True},
    }]
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _write_catalog(tmp_path, {"schemaVersion": 2, "layers": [descriptor]})

    database = LayerDatabase()

    internal_metadata = database.get_all_descriptors()[0].to_dict()["variants"][0]["metadata"]
    public_metadata = database.public_snapshot()[0]["variants"][0]["metadata"]
    assert internal_metadata["parametricPlan"] == "x" * 10_000
    assert public_metadata == {"publicFlag": True}
    assert database.public_snapshot()[0]["variants"][0]["sourceUrls"] == []


@pytest.mark.parametrize("catalog", [{"schemaVersion": 2}, ["not-an-object"]])
def test_rejects_malformed_catalog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    catalog: object,
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    _write_catalog(tmp_path, catalog)

    with pytest.raises(ValueError, match="catàleg de capes"):
        LayerDatabase()
