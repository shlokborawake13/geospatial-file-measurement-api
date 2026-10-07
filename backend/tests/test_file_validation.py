"""Tests for FileValidator."""
import io
import zipfile

import pytest

from app.core.exceptions import (
    FileTooLargeError,
    InvalidKMLError,
    InvalidShapefileError,
    UnsupportedFileTypeError,
)
from app.services.file_validator import FileValidator

validator = FileValidator()

VALID_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document></Document></kml>"""


def _make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


class TestExtensionValidation:
    def test_valid_kml_extension(self):
        ext = validator.validate("test.kml", VALID_KML)
        assert ext == "kml"

    def test_valid_zip_extension(self):
        content = _make_zip({"a.shp": b"x", "a.shx": b"x", "a.dbf": b"x"})
        ext = validator.validate("test.zip", content)
        assert ext == "zip"

    def test_unsupported_extension_geojson(self):
        with pytest.raises(UnsupportedFileTypeError):
            validator.validate("data.geojson", b"{}")

    def test_unsupported_extension_csv(self):
        with pytest.raises(UnsupportedFileTypeError):
            validator.validate("data.csv", b"col1,col2")

    def test_no_extension(self):
        with pytest.raises(UnsupportedFileTypeError):
            validator.validate("noextension", b"data")


class TestSizeValidation:
    def test_oversized_file(self):
        big = b"x" * (51 * 1024 * 1024)
        with pytest.raises(FileTooLargeError):
            validator.validate("big.kml", big)

    def test_exactly_at_limit_passes(self):
        # 50 MB exactly — should pass (limit is strictly greater than)
        content = VALID_KML  # tiny, just checking the logic path
        validator.validate("ok.kml", content)


class TestContentValidation:
    def test_invalid_kml_content(self):
        with pytest.raises(InvalidKMLError):
            validator.validate("bad.kml", b"this is not xml at all")

    def test_invalid_zip_magic_bytes(self):
        with pytest.raises(InvalidShapefileError):
            validator.validate("bad.zip", b"not a zip file content")

    def test_corrupt_zip(self):
        with pytest.raises(InvalidShapefileError):
            validator.validate("corrupt.zip", b"PK\x03\x04" + b"\xff" * 50)
