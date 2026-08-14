import pytest
from datetime import datetime, timezone
from terralab3d.domain.star_trails.models import StarTrailRequest, StarTrailGeometry
from terralab3d.domain.identifiers import ResourceId

def test_star_trail_models():
    start = datetime(2026, 8, 14, 22, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)
    req = StarTrailRequest(start_utc=start, end_utc=end, sample_count=128, magnitude_limit=6.0)
    assert req.sample_count == 128
    assert req.magnitude_limit == 6.0

    geom = StarTrailGeometry(resource_id=ResourceId("star_trails_1"), version=1, segment_count=128)
    assert geom.segment_count == 128
    assert geom.resource_id == ResourceId("star_trails_1")
