import pytest
from terralab3d.domain.search.calculations import DefaultSearchNormalizationCalculator
from terralab3d.domain.search.indexer import AstronomicalSearchIndex
from terralab3d.domain.geometry import EquatorialCoordinate
from terralab3d.domain.search.models import SearchQuery, SearchTargetKind

def test_normalization_calculator():
    calc = DefaultSearchNormalizationCalculator()
    
    # Test unidecode
    assert calc.normalize_query("Júpiter") == "jupiter"
    assert calc.normalize_query("Urà") == "ura"
    assert calc.normalize_query("Saturno") == "saturno"
    assert calc.normalize_query("Lluna") == "lluna"
    
    # Test spaces
    assert calc.normalize_query("NGC 1976") == "ngc1976"
    assert calc.normalize_query("M 42") == "m42"

def test_coordinate_calculator():
    calc = DefaultSearchNormalizationCalculator()
    
    # Text coordinates
    coord1 = calc.coordinate_query("ra=83.8 dec=-5.3")
    assert coord1 is not None
    assert coord1.right_ascension_deg == 83.8
    assert coord1.declination_deg == -5.3
    
    # Hours format
    coord2 = calc.coordinate_query("05h35m17.3s -05d23m28s")
    assert coord2 is not None
    assert 83.8 <= coord2.right_ascension_deg <= 83.9
    assert -5.4 <= coord2.declination_deg <= -5.3

def test_astronomical_search_index():
    calc = DefaultSearchNormalizationCalculator()
    index = AstronomicalSearchIndex(calc)
    
    # Dummy data
    planets = [
        {
            "body_id": "jupiter",
            "canon_name": "Júpiter",
            "aliases": ["Júpiter", "Jupiter"],
            "coordinate_snapshot": EquatorialCoordinate(right_ascension_deg=100.0, declination_deg=20.0)
        }
    ]
    
    class DummyDeepSky:
        def __init__(self, name, common_name, messier_nr, ra, dec):
            self.name = name
            self.common_name = common_name
            self.messier_nr = messier_nr
            self.ra_deg = ra
            self.dec_deg = dec
            
    deep_sky = [
        DummyDeepSky("NGC 1976", "Orion Nebula", 42, 83.8, -5.3)
    ]
    
    index.build_index([], deep_sky, planets)
    
    # Exact match for planet
    query_jup = SearchQuery("Jupiter", frozenset([SearchTargetKind.BODY]), 10)
    res_jup = index.search(query_jup)
    assert len(res_jup) == 1
    assert res_jup[0].target_ref == "jupiter"
    assert res_jup[0].score == 100
    
    # Exact match for deep sky (M42 alias)
    query_m42 = SearchQuery("M42", frozenset([SearchTargetKind.DEEP_SKY]), 10)
    res_m42 = index.search(query_m42)
    assert len(res_m42) == 1
    assert res_m42[0].target_ref == "NGC 1976"
    assert res_m42[0].score == 100
    
    # Prefix match
    query_j = SearchQuery("jup", frozenset([SearchTargetKind.BODY]), 10)
    res_j = index.search(query_j)
    assert len(res_j) == 1
    assert res_j[0].score == 50
