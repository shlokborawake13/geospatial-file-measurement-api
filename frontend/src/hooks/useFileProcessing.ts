import { useState } from "react";
import { uploadFile } from "../services/api";
import type { FileUploadResponse } from "../types/file";

interface State {
  loading: boolean;
  result: FileUploadResponse | null;
  error: string | null;
}

export function useFileProcessing() {
  const [state, setState] = useState<State>({
    loading: false,
    result: null,
    error: null,
  });

  async function upload(file: File) {
    setState({ loading: true, result: null, error: null });
    try {
      const result = await uploadFile(file);
      setState({ loading: false, result, error: null });
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed.";
      setState({ loading: false, result: null, error: message });
      return null;
    }
  }

  function reset() {
    setState({ loading: false, result: null, error: null });
  }

  return { ...state, upload, reset };
}
