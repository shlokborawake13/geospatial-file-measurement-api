"""
Shapefile Processor
===================

Safely extracts a Shapefile ZIP and reads it into a GeoDataFrame.

Security measures:
- All members are checked for path traversal (Zip Slip) before extraction.
- Extraction is limited to a generated temporary directory.
- Extraction size and file count are bounded.
- The temporary directory is always cleaned up after processing.

Required Shapefile components: .shp, .shx, .dbf
Strongly preferred: .prj (CRS definition)
"""
import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

import geopandas as gpd

from app.core.exceptions import (
    InvalidShapefileError,
    MissingShapefileComponentError,
    InvalidCRSError,
)

logger = logging.getLogger(__name__)

REQUIRED_EXTENSIONS = {".shp", ".shx", ".dbf"}
MAX_EXTRACT_SIZE_BYTES = 500 * 1024 * 1024   # 500 MB
MAX_EXTRACT_FILES = 200


class ShapefileProcessor:
    def process(self, content: bytes) -> gpd.GeoDataFrame:
        """
        Extract and read a Shapefile ZIP.

        Returns a GeoDataFrame.
        Always cleans up the temporary directory.
        """
        tmp_dir = tempfile.mkdtemp(prefix="shp_upload_")
        try:
            shp_path = self._extract(content, tmp_dir)
            return self._read_shapefile(shp_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.debug("Cleaned up temp dir: %s", tmp_dir)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract(self, content: bytes, tmp_dir: str) -> str:
        """
        Safely extract ZIP and return the path to the .shp file.
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
        except zipfile.BadZipFile:
            raise InvalidShapefileError("The uploaded file is not a valid ZIP archive.")

        members = zf.infolist()

        # Security: count and size checks
        if len(members) > MAX_EXTRACT_FILES:
            raise InvalidShapefileError(
                f"ZIP contains {len(members)} files; maximum allowed is {MAX_EXTRACT_FILES}."
            )
        total_size = sum(m.file_size for m in members)
        if total_size > MAX_EXTRACT_SIZE_BYTES:
            raise InvalidShapefileError(
                f"ZIP uncompressed size exceeds {MAX_EXTRACT_SIZE_BYTES // (1024*1024)} MB."
            )

        # Security: Zip Slip prevention
        tmp_path = Path(tmp_dir).resolve()
        for member in members:
            member_path = (tmp_path / member.filename).resolve()
            if not str(member_path).startswith(str(tmp_path)):
                raise InvalidShapefileError(
                    f"Unsafe path detected in ZIP: '{member.filename}'"
                )

        zf.extractall(tmp_dir)
        zf.close()

        return self._find_shp(tmp_dir)

    @staticmethod
    def _find_shp(tmp_dir: str) -> str:
        """Locate the .shp file and validate required components exist."""
        shp_files = list(Path(tmp_dir).rglob("*.shp"))
        if not shp_files:
            raise MissingShapefileComponentError(
                "No .shp file found in the ZIP archive."
            )
        if len(shp_files) > 1:
            logger.warning("Multiple .shp files found; using the first: %s", shp_files[0])

        shp_path = shp_files[0]
        stem = shp_path.stem
        parent = shp_path.parent

        missing = [
            ext for ext in REQUIRED_EXTENSIONS
            if not (parent / f"{stem}{ext}").exists()
        ]
        if missing:
            raise MissingShapefileComponentError(
                f"Required Shapefile components missing: {', '.join(missing)}"
            )

        if not (parent / f"{stem}.prj").exists():
            logger.warning(
                "No .prj file found for '%s'. CRS may be unavailable.", stem
            )

        return str(shp_path)

    @staticmethod
    def _read_shapefile(shp_path: str) -> gpd.GeoDataFrame:
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as exc:
            raise InvalidShapefileError(f"Could not read Shapefile: {exc}") from exc

        if gdf.empty:
            raise InvalidShapefileError("Shapefile contains no features.")

        if gdf.crs is None:
            raise InvalidCRSError(
                "Shapefile has no CRS (.prj file missing or unreadable). "
                "A valid CRS is required for metric measurement."
            )

        logger.info("Shapefile parsed: %d features, CRS=%s", len(gdf), gdf.crs)
        return gdf
