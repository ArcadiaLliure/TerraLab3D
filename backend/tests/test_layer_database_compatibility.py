import json

import pytest

from terralab3d.domain.identifiers import ResourceId
from terralab3d.infrastructure.resources.layer_database import LayerDatabase


def _layer_record() -> dict:
    return {
        "id": "test.layer",
        "name": "Test layer",
        "description": "",
        "domain": "earth",
        "category": "land_cover",
        "provider": "Test provider",
        "acquisitionKind": "STATIC_FILE",
        "citation": "",
        "license": "",
        "originalSourceUrl": None,
        "directUrl": None,
        "variants": [],
        "credits": [],
        "dependencies": [],
        "metadata": {},
    }


def test_layer_database_loads_versioned_document_and_preserves_schema(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    state_dir = tmp_path / "TerraLab3D"
    state_dir.mkdir()
    path = state_dir / "layers.json"
    path.write_text(
        json.dumps({"schemaVersion": 2, "layers": [_layer_record()]}),
        encoding="utf-8",
    )

    database = LayerDatabase()

    assert database.get_descriptor(ResourceId("test.layer")) is not None
    database.save()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schemaVersion"] == 2
    assert saved["layers"][0]["id"] == "test.layer"


def test_layer_database_migrates_legacy_array_on_next_save(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    state_dir = tmp_path / "TerraLab3D"
    state_dir.mkdir()
    path = state_dir / "layers.json"
    path.write_text(json.dumps([_layer_record()]), encoding="utf-8")

    database = LayerDatabase()
    assert database.get_descriptor(ResourceId("test.layer")) is not None

    database.save()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["schemaVersion"] == 2
    assert saved["layers"][0]["id"] == "test.layer"


@pytest.mark.parametrize(
    "payload",
    [
        {"schemaVersion": 2},
        {"schemaVersion": 2, "layers": ["not-a-layer"]},
        "not-a-document",
    ],
)
def test_layer_database_rejects_invalid_document_shape(tmp_path, monkeypatch, payload) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    state_dir = tmp_path / "TerraLab3D"
    state_dir.mkdir()
    (state_dir / "layers.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid layer catalog"):
        LayerDatabase()
