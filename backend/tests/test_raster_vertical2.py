from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.shutil import copy as copy_raster
from affine import Affine

from terralab3d.domain.raster.models import (
    RasterDatasetSelection,
    RasterMetadataOverride,
    RasterWindowRequest,
)
from terralab3d.infrastructure.adapters.raster import (
    RasterDatasetError,
    RasterSelectionRequired,
    RasterioRasterReader,
    TextRasterError,
    TextRasterMaterializer,
    TextRasterOptions,
)


def _write_raster(
    path: Path,
    values: np.ndarray,
    *,
    driver: str = "GTiff",
    nodata: float | int | None = -9999,
) -> None:
    arrays = values[np.newaxis, ...] if values.ndim == 2 else values
    with rasterio.open(
        path,
        "w",
        driver=driver,
        width=arrays.shape[2],
        height=arrays.shape[1],
        count=arrays.shape[0],
        dtype=arrays.dtype,
        crs="EPSG:25831",
        transform=Affine(10, 0, 400000, 0, -10, 4600000),
        nodata=nodata,
    ) as dataset:
        dataset.write(arrays)
        for band in range(1, arrays.shape[0] + 1):
            dataset.set_band_description(band, f"Band {band}")
            dataset.scales = tuple(2.0 for _ in range(arrays.shape[0]))
            dataset.offsets = tuple(3.0 for _ in range(arrays.shape[0]))


def test_rasterio_descriptor_and_window_preserve_source_values(tmp_path: Path) -> None:
    path = tmp_path / "elevation.data"
    values = np.asarray([[1, 2, 3], [4, -9999, 6]], dtype=np.int16)
    _write_raster(path, values)
    reader = RasterioRasterReader(max_open_datasets=1)

    descriptor = reader.inspect(str(path))
    assert descriptor.driver == "GTiff"
    assert descriptor.source_dtype == "int16"
    assert descriptor.crs == "EPSG:25831"
    assert descriptor.bands[0].scale == 2.0
    assert descriptor.bands[0].offset == 3.0
    assert descriptor.bands[0].nodata == -9999
    assert "GTiff" in reader.drivers()

    result = reader.read_window(
        RasterWindowRequest(RasterDatasetSelection(str(path)), 0, 0, 3, 2)
    )
    assert result.values.dtype == np.int16
    assert result.values.tolist() == values.tolist()
    assert result.valid_mask.tolist() == [[True, True, True], [True, False, True]]
    reader.close()
    with pytest.raises(RasterDatasetError, match="closed"):
        reader.read_window(
            RasterWindowRequest(RasterDatasetSelection(str(path)), 0, 0, 1, 1)
        )


def test_multiband_requires_explicit_selection_and_overrides_are_virtual(tmp_path: Path) -> None:
    path = tmp_path / "multi.tif"
    values = np.stack(
        [np.full((2, 2), 10, dtype=np.float32), np.full((2, 2), 20, dtype=np.float32)]
    )
    _write_raster(path, values, nodata=None)
    reader = RasterioRasterReader()

    with pytest.raises(RasterSelectionRequired, match="bands"):
        reader.validate_selection(RasterDatasetSelection(str(path)))
    selection = RasterDatasetSelection(
        str(path),
        band_index=2,
        overrides=RasterMetadataOverride(
            crs="EPSG:4326",
            transform=(0.1, 0.0, 2.0, 0.0, -0.1, 42.0),
            nodata=20.0,
            nodata_is_set=True,
            provenance="import-confirmation",
        ),
    )
    descriptor = reader.validate_selection(selection)
    assert descriptor.crs == "EPSG:4326"
    assert descriptor.original_metadata["overrides"]["provenance"] == "import-confirmation"
    result = reader.read_window(RasterWindowRequest(selection, 0, 0, 2, 2))
    assert not result.valid_mask.any()
    with rasterio.open(path) as original:
        assert str(original.crs) == "EPSG:25831"
        assert original.nodata is None


def test_nodata_override_replaces_metadata_nodata_without_losing_physical_masks(tmp_path: Path) -> None:
    path = tmp_path / "nodata-override.tif"
    _write_raster(path, np.asarray([[-9999, 20]], dtype=np.int16), nodata=-9999)
    reader = RasterioRasterReader()
    selection = RasterDatasetSelection(
        str(path),
        overrides=RasterMetadataOverride(nodata=20, nodata_is_set=True),
    )
    result = reader.read_window(RasterWindowRequest(selection, 0, 0, 2, 1))
    assert result.valid_mask.tolist() == [[True, False]]


def test_bounds_override_builds_a_virtual_transform(tmp_path: Path) -> None:
    path = tmp_path / "bounds.tif"
    _write_raster(path, np.ones((2, 4), dtype=np.float32), nodata=None)
    reader = RasterioRasterReader()
    descriptor = reader.validate_selection(RasterDatasetSelection(
        str(path),
        overrides=RasterMetadataOverride(bounds=(0, 10, 40, 30), provenance="user-bounds"),
    ))
    assert descriptor.bounds == pytest.approx((0, 10, 40, 30))
    assert descriptor.resolution == pytest.approx((10, 10))
    assert descriptor.original_metadata["overrides"]["bounds"] == (0, 10, 40, 30)


@pytest.mark.parametrize("driver,suffix", [("GTiff", ".tif"), ("AAIGrid", ".asc")])
def test_installed_core_drivers(driver: str, suffix: str, tmp_path: Path) -> None:
    reader = RasterioRasterReader()
    if driver not in reader.drivers():
        pytest.skip(f"{driver} driver is not installed")
    path = tmp_path / f"fixture{suffix}"
    try:
        _write_raster(path, np.arange(9, dtype=np.float32).reshape(3, 3), driver=driver)
    except rasterio.errors.RasterioError:
        pytest.skip(f"Installed {driver} driver cannot create this fixture")
    assert reader.inspect(str(path)).driver == driver


@pytest.mark.parametrize(
    "driver,suffix",
    [("ENVI", ".dat"), ("HFA", ".img"), ("JP2OpenJPEG", ".jp2")],
)
def test_other_installed_drivers_are_exercised_or_explicitly_skipped(
    driver: str,
    suffix: str,
    tmp_path: Path,
) -> None:
    reader = RasterioRasterReader()
    if driver not in reader.drivers():
        pytest.skip(f"{driver} read capability is not installed")
    path = tmp_path / f"optional{suffix}"
    try:
        _write_raster(
            path,
            np.arange(16, dtype=np.uint16).reshape(4, 4),
            driver=driver,
            nodata=None,
        )
    except (rasterio.errors.RasterioError, TypeError, ValueError) as exc:
        pytest.skip(f"{driver} is readable but cannot create this fixture: {exc}")
    assert reader.inspect(str(path)).driver == driver


def test_vrt_is_opened_by_gdal_without_extension_routing(tmp_path: Path) -> None:
    source = tmp_path / "source.tif"
    _write_raster(source, np.arange(4, dtype=np.int16).reshape(2, 2))
    vrt = tmp_path / "renamed.container"
    with rasterio.open(source) as dataset:
        copy_raster(dataset, vrt, driver="VRT")
    reader = RasterioRasterReader()
    assert reader.inspect(str(vrt)).driver == "VRT"


def test_text_matrix_csv_and_regular_xyz_materialize_to_common_reader(tmp_path: Path) -> None:
    materializer = TextRasterMaterializer()
    cache = tmp_path / "cache"
    matrix = tmp_path / "matrix.csv"
    matrix.write_text("1,2,3\n4,-9999,6\n", encoding="utf-8")
    matrix_raster = materializer.materialize(
        matrix,
        cache,
        TextRasterOptions(
            layout="matrix",
            delimiter=",",
            has_header=False,
            crs="EPSG:25831",
            transform=(5, 0, 100, 0, -5, 200),
            nodata=-9999,
        ),
    )
    reader = RasterioRasterReader()
    descriptor = reader.inspect(str(matrix_raster))
    assert descriptor.source_dtype == "int64"
    assert descriptor.width == 3 and descriptor.height == 2

    xyz = tmp_path / "points.xyz"
    xyz.write_text("0 0 1\n1 0 2\n0 1 3\n1 1 4\n", encoding="utf-8")
    xyz_raster = materializer.materialize(
        xyz,
        cache,
        TextRasterOptions(layout="xyz", delimiter=" ", has_header=False, crs="EPSG:25831"),
    )
    window = reader.read_window(
        RasterWindowRequest(RasterDatasetSelection(str(xyz_raster)), 0, 0, 2, 2)
    )
    assert window.values.tolist() == [[3.0, 4.0], [1.0, 2.0]]


def test_text_layout_header_and_irregular_xyz_are_rejected(tmp_path: Path) -> None:
    materializer = TextRasterMaterializer()
    ambiguous = tmp_path / "ambiguous.csv"
    ambiguous.write_text("x,y,z\n0,0,1\n1,0,2\n", encoding="utf-8")
    with pytest.raises(TextRasterError, match="header presence"):
        materializer.materialize(
            ambiguous,
            tmp_path / "cache",
            TextRasterOptions(layout="xyz", delimiter=","),
        )

    irregular = tmp_path / "irregular.xyz"
    irregular.write_text("0 0 1\n1 0 2\n0 2 3\n1 3 4\n", encoding="utf-8")
    with pytest.raises(TextRasterError, match="point cloud|fill a regular grid"):
        materializer.materialize(
            irregular,
            tmp_path / "cache",
            TextRasterOptions(layout="xyz", delimiter=" ", has_header=False, crs="EPSG:25831"),
        )
