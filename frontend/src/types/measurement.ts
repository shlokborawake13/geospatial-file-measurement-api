export type MeasurementType = "AREA" | "LENGTH";
export type MeasurementStatus = "SUCCESS" | "NOT_REQUIRED" | "UNSUPPORTED" | "FAILED";

export interface MeasurementResponse {
  feature_id: string;
  feature_index: number;
  geometry_type: string;
  measurement_type: MeasurementType | null;
  value: number | null;
  unit: string | null;
  measurement_crs: string | null;
  status: MeasurementStatus;
}

export interface MeasurementsResponse {
  file_id: string;
  page: number;
  page_size: number;
  total: number;
  measurements: MeasurementResponse[];
}
