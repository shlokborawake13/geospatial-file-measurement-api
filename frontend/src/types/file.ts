export type FileStatus = "UPLOADED" | "PROCESSING" | "COMPLETED" | "FAILED";
export type FileType = "KML" | "SHP_ZIP";

export interface FileUploadResponse {
  id: string;
  filename: string;
  file_type: FileType;
  feature_count: number | null;
  crs: string | null;
  status: FileStatus;
}

export interface FileDetailResponse {
  id: string;
  filename: string;
  file_type: FileType;
  feature_count: number | null;
  crs: string | null;
  status: FileStatus;
  error_message: string | null;
  processing_duration_ms: number | null;
  created_at: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}
