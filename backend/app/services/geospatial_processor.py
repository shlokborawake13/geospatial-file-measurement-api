"""
Geospatial Processor
====================

Orchestrates the common processing pipeline after a file has been parsed
into a GeoDataFrame by either KMLProcessor or ShapefileProcessor.

Pipeline:
    GeoDataFrame
        → detect CRS
        → select measurement CRS
        → for each feature:
            → validate/repair geometry
            → reproject to measurement CRS
            → calculate measurement
            → build Feature + Measurement domain objects
"""
import logging
import uuid
from typing import List, Tuple

import geopandas as gpd
from pyproj import CRS

from app.models.feature import Feature
from app.models.measurement import Measurement
from app.services.crs_service import CRSService
from app.services.geometry_service import GeometryService
from app.services.measurement_service import MeasurementService

logger = logging.getLogger(__name__)


class GeospatialProcessor:
    def __init__(self):
        self._crs_service = CRSService()
        self._geometry_service = GeometryService()
        self._measurement_service = MeasurementService()

    def process(
        self, gdf: gpd.GeoDataFrame, file_id: str
    ) -> Tuple[List[Feature], List[Measurement], str, str]:
        """
        Process a GeoDataFrame into Feature and Measurement domain objects.

        Returns
        -------
        (features, measurements, original_crs_str, measurement_crs_str)
        """
        source_crs: CRS = gdf.crs
        original_crs_str = self._crs_service.normalize_crs_string(source_crs)
        logger.info("Processing file_id=%s original_crs=%s features=%d",
                    file_id, original_crs_str, len(gdf))

        measurement_crs, measurement_crs_str = self._crs_service.select_measurement_crs(gdf)

        features: List[Feature] = []
        measurements: List[Measurement] = []

        for idx, row in gdf.iterrows():
            feature_index = int(idx)
            raw_geom = row.geometry
            geom_type = raw_geom.geom_type if raw_geom is not None else "Unknown"

            # Validate / repair geometry
            valid_geom, geom_error = self._geometry_service.validate_and_repair(
                raw_geom, feature_index
            )

            # Convert geometry to GeoJSON (use original CRS geometry for storage)
            geojson = (
                self._geometry_service.to_geojson(raw_geom)
                if raw_geom is not None
                else None
            )

            # Build properties dict (exclude geometry column)
            props = {
                k: v
                for k, v in row.items()
                if k != "geometry" and v is not None
            }
            # Ensure JSON-serialisable values
            props = {k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                     for k, v in props.items()}

            feature_id = str(uuid.uuid4())
            feature = Feature(
                id=feature_id,
                file_id=file_id,
                feature_index=feature_index,
                geometry_type=geom_type,
                geometry=geojson,
                properties=props,
                original_crs=original_crs_str,
            )
            features.append(feature)

            # Measurement
            classification = self._geometry_service.classify(geom_type)

            if valid_geom is not None and classification in ("area", "length"):
                # Reproject to measurement CRS
                projected_geom = self._crs_service.reproject_geometry(
                    valid_geom, source_crs, measurement_crs
                )
            else:
                projected_geom = valid_geom

            if geom_error and classification in ("area", "length"):
                from app.models.measurement import MeasurementStatus
                from app.services.measurement_service import MeasurementResult
                result = MeasurementResult(
                    status=MeasurementStatus.FAILED,
                    error_message=geom_error,
                )
            else:
                result = self._measurement_service.calculate(
                    projected_geom, geom_type, measurement_crs_str, classification
                )

            measurement = Measurement(
                id=str(uuid.uuid4()),
                feature_id=feature_id,
                status=result.status,
                measurement_type=result.measurement_type,
                value=result.value,
                unit=result.unit,
                measurement_crs=result.measurement_crs,
                error_message=result.error_message,
            )
            measurements.append(measurement)

        logger.info(
            "Processed file_id=%s: %d features, measurement_crs=%s",
            file_id, len(features), measurement_crs_str,
        )
        return features, measurements, original_crs_str, measurement_crs_str
