from datetime import datetime, timezone

from terralab3d.domain.identifiers import ResourceId
from terralab3d.domain.star_trails.models import (
    StarTrailGeometry,
    StarTrailPlaybackConfig,
    StarTrailRequest,
    clamped_exposure_seconds,
)


def test_star_trail_models():
    start = datetime(2026, 8, 14, 22, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 15, 4, 0, tzinfo=timezone.utc)
    req = StarTrailRequest(start_utc=start, end_utc=end, sample_count=128, magnitude_limit=6.0)
    assert req.sample_count == 128
    assert req.magnitude_limit == 6.0

    geom = StarTrailGeometry(resource_id=ResourceId("star_trails_1"), version=1, segment_count=128)
    assert geom.segment_count == 128
    assert geom.resource_id == ResourceId("star_trails_1")


def test_star_trail_playback_controls_are_normalized() -> None:
    config = StarTrailPlaybackConfig.normalized(
        duration_seconds=-10.0,
        sample_interval_seconds=0.0,
        magnitude_limit=6.5,
        playback_rate=0.0,
    )

    assert config.duration_seconds == 1.0
    assert config.sample_interval_seconds == 1.0
    assert config.magnitude_limit == 6.5
    assert config.playback_rate == 0.01


def test_star_trail_exposure_is_clamped_to_session_interval() -> None:
    start = datetime(2026, 8, 14, 22, 0, tzinfo=timezone.utc)

    assert clamped_exposure_seconds(
        start, datetime(2026, 8, 14, 21, 0, tzinfo=timezone.utc), 3_600.0
    ) == 0.0
    assert clamped_exposure_seconds(
        start, datetime(2026, 8, 14, 22, 30, tzinfo=timezone.utc), 3_600.0
    ) == 1_800.0
    assert clamped_exposure_seconds(
        start, datetime(2026, 8, 15, 0, 0, tzinfo=timezone.utc), 3_600.0
    ) == 3_600.0
