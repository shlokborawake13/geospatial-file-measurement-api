import type { FileDetailResponse, FileUploadResponse } from "../types/file";
import type { MeasurementsResponse } from "../types/measurement";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  import.meta.env.VITE_API_URL ??
  "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const message =
      body?.error?.message ?? `Request failed with status ${res.status}`;
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function uploadFile(file: File): Promise<FileUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}/api/files/`, { method: "POST", body: form });
  } catch {
    throw new Error("Cannot reach the server. Is the backend running on port 8000?");
  }
  return handleResponse<FileUploadResponse>(res);
}

export async function getFile(fileId: string): Promise<FileDetailResponse> {
  const res = await fetch(`${BASE_URL}/api/files/${fileId}/`);
  return handleResponse<FileDetailResponse>(res);
}

export async function getMeasurements(
  fileId: string,
  page: number = 1,
  pageSize: number = 100
): Promise<MeasurementsResponse> {
  const res = await fetch(
    `${BASE_URL}/api/files/${fileId}/measurements/?page=${page}&page_size=${pageSize}`
  );
  return handleResponse<MeasurementsResponse>(res);
}
