"""
KML Processor
=============

Reads a KML file into a normalised GeoPandas GeoDataFrame.

KML always uses EPSG:4326 (WGS84 geographic coordinates).
GeoPandas/Fiona handles multi-layer KML; we merge all layers.
"""
import io
import logging
import tempfile
import os
from pathlib import Path

import geopandas as gpd
import fiona

from app.core.exceptions import InvalidKMLError

logger = logging.getLogger(__name__)

# Enable KML driver in Fiona (disabled by default for security)
fiona.drvsupport.supported_drivers["KML"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"


class KMLProcessor:
    def process(self, content: bytes) -> gpd.GeoDataFrame:
        """
        Parse KML bytes into a GeoDataFrame.

        Returns a GeoDataFrame with CRS set to EPSG:4326.
        Raises InvalidKMLError on parse failure.
        """
        # Write to a named temp file — Fiona/GDAL requires a file path for KML.
        # Use delete=False and clean up manually after Fiona has closed the file.
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".kml")
        try:
            os.write(tmp_fd, content)
            os.close(tmp_fd)  # close fd before Fiona opens the file
            return self._read_kml(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Windows: file may still be locked; temp dir will clean it up

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _read_kml(path: str) -> gpd.GeoDataFrame:
        try:
            layers = fiona.listlayers(path)
        except Exception as exc:
            raise InvalidKMLError(f"KML file could not be opened: {exc}") from exc
        if not layers:
            raise InvalidKMLError("KML file contains no readable layers.")

        frames = []
        for layer in layers:
            try:
                gdf = gpd.read_file(path, driver="KML", layer=layer)
                if not gdf.empty:
                    frames.append(gdf)
            except Exception as exc:
                logger.warning("Skipping KML layer '%s': %s", layer, exc)

        if not frames:
            # Fallback: try reading without specifying a layer (lets GDAL pick)
            try:
                gdf = gpd.read_file(path, driver="KML")
                if not gdf.empty:
                    frames.append(gdf)
            except Exception as exc:
                raise InvalidKMLError(f"KML file contains no readable features: {exc}") from exc

        if not frames:
            raise InvalidKMLError("KML file contains no readable features.")

        combined = gpd.GeoDataFrame(
            gpd.pd.concat(frames, ignore_index=True), crs="EPSG:4326"
        )
        combined = combined[combined.geometry.notna()].reset_index(drop=True)

        if combined.empty:
            raise InvalidKMLError("KML file contains no valid geometries.")

        logger.info("KML parsed: %d features across %d layer(s)", len(combined), len(layers))
        return combined
