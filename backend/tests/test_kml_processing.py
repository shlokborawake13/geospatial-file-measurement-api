"""Tests for KMLProcessor."""
import pytest
from app.services.kml_processor import KMLProcessor
from app.core.exceptions import InvalidKMLError

processor = KMLProcessor()

POLYGON_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Polygon</name>
      <Polygon>
        <outerBoundaryIs><LinearRing>
          <coordinates>0,0,0 1,0,0 1,1,0 0,1,0 0,0,0</coordinates>
        </LinearRing></outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""

LINESTRING_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Line</name>
      <LineString>
        <coordinates>0,0,0 0.01,0,0</coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

POINT_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Point</name>
      <Point><coordinates>0,0,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>"""

MIXED_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon><outerBoundaryIs><LinearRing>
        <coordinates>0,0 1,0 1,1 0,1 0,0</coordinates>
      </LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
    <Placemark>
      <LineString><coordinates>0,0 0.01,0</coordinates></LineString>
    </Placemark>
    <Placemark>
      <Point><coordinates>0,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>"""


def test_polygon_kml_returns_one_feature():
    gdf = processor.process(POLYGON_KML)
    assert len(gdf) == 1
    assert gdf.iloc[0].geometry.geom_type == "Polygon"


def test_polygon_kml_crs_is_4326():
    gdf = processor.process(POLYGON_KML)
    assert gdf.crs.to_epsg() == 4326


def test_linestring_kml():
    gdf = processor.process(LINESTRING_KML)
    assert len(gdf) == 1
    assert gdf.iloc[0].geometry.geom_type == "LineString"


def test_point_kml():
    gdf = processor.process(POINT_KML)
    assert len(gdf) == 1
    assert gdf.iloc[0].geometry.geom_type == "Point"


def test_mixed_kml_returns_three_features():
    gdf = processor.process(MIXED_KML)
    assert len(gdf) == 3
    types = set(gdf.geometry.geom_type)
    assert "Polygon" in types
    assert "LineString" in types
    assert "Point" in types


def test_invalid_kml_raises():
    with pytest.raises(InvalidKMLError):
        processor.process(b"this is not kml")


def test_empty_kml_raises():
    empty = b"""<?xml version="1.0"?>
    <kml xmlns="http://www.opengis.net/kml/2.2"><Document></Document></kml>"""
    with pytest.raises(InvalidKMLError):
        processor.process(empty)
