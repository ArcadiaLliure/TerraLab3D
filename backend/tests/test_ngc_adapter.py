import tempfile
from pathlib import Path
import pytest
import struct
import numpy as np

from terralab3d.infrastructure.adapters.ngc_catalog.adapter import NgcCatalogPostProcessor, NgcFlags

def test_ngc_post_processor_basic():
    csv_content = """Name;Type;RA;Dec;Const;MajAx;MinAx;PosAng;B-Mag;V-Mag;J-Mag;H-Mag;K-Mag;SurfBr;Hubble;Cstar U-B;Cstar B-V;M;NGC;IC;Caldwell;Messier
M31;G;00:42:44.3;+41:16:09;And;190;60;35;4.36;3.44;1.939;1.196;0.867;13.6;SA(s)b;;;;224;;14;31
M42;Cl+N;05:35:17.3;-05:23:28;Ori;66;60;0;4;;;;;;;;;;1976;;;42
FakeStar;*;00:00:00.0;+00:00:00;XYZ;;;;;;;;;;;;;;;;;
EmptyData;GCl;12:00:00.0;-10:00:00;XYZ;;;;;;;;;;;;;;;;;
"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        csv_file = tmp_path / "NGC.csv"
        csv_file.write_text(csv_content, encoding="utf-8")
        
        processor = NgcCatalogPostProcessor()
        res = processor.process(csv_file, tmp_path)
        
        assert res.render_path.exists()
        
        # Read the binary data
        with open(res.render_path, "rb") as f:
            data = f.read()
            
        assert res.metadata["recordCount"] == 4
        assert res.metadata["renderableCount"] == 3  # FakeStar is * which is not eligible
        
        # Layout test
        import json
        meta_file = tmp_path / "ngc_metadata.json"
        with open(meta_file, "r") as f:
            meta = json.load(f)
            
        layout = meta["bufferLayout"]
        
        # Verify M31 (index 0)
        flags_offset = layout["flags"]["offset"]
        flags_buf = data[flags_offset:flags_offset + 4*4]
        flags = np.frombuffer(flags_buf, dtype=np.uint32)
        
        # M31: eligible (yes), major (yes), minor (yes), PA (yes), MAG (yes, V-Mag=3.44 -> MAG_IS_V), SurfBr (yes, 13.6)
        m31_flags = flags[0]
        assert bool(m31_flags & NgcFlags.RENDER_ELIGIBLE)
        assert bool(m31_flags & NgcFlags.HAS_MAJOR)
        assert bool(m31_flags & NgcFlags.HAS_MINOR)
        assert bool(m31_flags & NgcFlags.HAS_PA)
        assert bool(m31_flags & NgcFlags.HAS_MAG)
        assert bool(m31_flags & NgcFlags.MAG_IS_V)
        assert not bool(m31_flags & NgcFlags.MAG_IS_B)
        assert bool(m31_flags & NgcFlags.HAS_SURFACE_BRIGHTNESS)
        
        # M42: eligible (yes), major (yes), minor (yes), PA (yes), MAG (yes, B-Mag=4 -> MAG_IS_B)
        m42_flags = flags[1]
        assert bool(m42_flags & NgcFlags.RENDER_ELIGIBLE)
        assert bool(m42_flags & NgcFlags.HAS_MAG)
        assert bool(m42_flags & NgcFlags.MAG_IS_B)
        
        # FakeStar was skipped, so index 2 is now EmptyData
        empty_flags = flags[2]
        assert bool(empty_flags & NgcFlags.RENDER_ELIGIBLE)
        assert not bool(empty_flags & NgcFlags.HAS_MAJOR)
        assert not bool(empty_flags & NgcFlags.HAS_MAG)
