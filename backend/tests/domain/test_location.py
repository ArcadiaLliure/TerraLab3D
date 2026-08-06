import pytest
from terralab3d.domain.observer.models import GeoLocation, ObserverProfile
from terralab3d.domain.identifiers import ObserverId

def test_geolocation_valid():
    loc = GeoLocation(latitude_deg=41.0, longitude_deg=1.2)
    assert loc.latitude_deg == 41.0
    assert loc.longitude_deg == pytest.approx(1.2)
    assert loc.elevation_m is None

def test_geolocation_latitude_bounds():
    with pytest.raises(ValueError, match="La latitud ha d'estar entre -90 i 90"):
        GeoLocation(latitude_deg=91.0, longitude_deg=0.0)
    
    with pytest.raises(ValueError, match="La latitud ha d'estar entre -90 i 90"):
        GeoLocation(latitude_deg=-90.1, longitude_deg=0.0)

def test_geolocation_longitude_bounds():
    with pytest.raises(ValueError, match="La longitud ha d'estar entre -180 i 180"):
        GeoLocation(latitude_deg=0.0, longitude_deg=181.0)

    with pytest.raises(ValueError, match="La longitud ha d'estar entre -180 i 180"):
        GeoLocation(latitude_deg=0.0, longitude_deg=-181.0)

def test_observer_profile_effective_height():
    loc = GeoLocation(latitude_deg=0.0, longitude_deg=0.0, elevation_m=100.0)
    profile = ObserverProfile(
        observer_id=ObserverId("test"),
        location=loc,
        height_offset_m=5.5
    )
    assert profile.effective_height_m == 105.5

    loc_no_elev = GeoLocation(latitude_deg=0.0, longitude_deg=0.0, elevation_m=None)
    profile_no_elev = ObserverProfile(
        observer_id=ObserverId("test"),
        location=loc_no_elev,
        height_offset_m=5.5
    )
    assert profile_no_elev.effective_height_m == 5.5
