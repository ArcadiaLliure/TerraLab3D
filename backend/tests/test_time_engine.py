import pytest
from datetime import datetime, timezone
from terralab3d.domain.time.engine import AstronomicalEngine

def test_julian_day():
    engine = AstronomicalEngine()
    # JD per l'any 2000-01-01 12:00 UTC (J2000.0) és 2451545.0
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    jd = engine.julian_day(dt)
    assert abs(jd - 2451545.0) < 0.001

def test_local_sidereal_time():
    engine = AstronomicalEngine()
    dt = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # LST per Greenwich at J2000.0 is roughly 280.4606 degrees
    lst = engine.local_sidereal_angle_deg(dt, 0.0)
    assert abs(lst - 280.4606) < 0.01

def test_fast_sun_altitude():
    engine = AstronomicalEngine()
    # Equinox (around March 20), noon at equator should be close to 90 degrees altitude
    dt = datetime(2023, 3, 21, 12, 0, 0, tzinfo=timezone.utc)
    alt = engine.fast_sun_altitude_for_day(dt, lat=0.0, lon=0.0, hour=12.0)
    assert 85.0 < alt <= 90.0
