"""Universal raster I/O adapters."""

from terralab3d.domain.raster import RasterDatasetError, RasterSelectionRequired, TextRasterOptions
from .reader import RasterioRasterReader
from .text import TextRasterError, TextRasterMaterializer
from .categorical import RasterioCategoricalRasterAdapter

__all__ = [
    "RasterDatasetError",
    "RasterioCategoricalRasterAdapter",
    "RasterSelectionRequired",
    "RasterioRasterReader",
    "TextRasterError",
    "TextRasterMaterializer",
    "TextRasterOptions",
]
