import { useNavigate } from "react-router-dom";
import FileUploader from "../components/FileUploader";
import ErrorMessage from "../components/ErrorMessage";
import { useFileProcessing } from "../hooks/useFileProcessing";

export default function UploadPage() {
  const navigate = useNavigate();
  const { loading, error, upload } = useFileProcessing();

  async function handleFile(file: File) {
    const result = await upload(file);
    if (result) {
      navigate(`/results/${result.id}`);
    }
  }

  return (
    <main className="page upload-page">
      <h1>Geospatial File Measurement</h1>
      <p className="subtitle">Upload a KML or Shapefile ZIP to extract features and calculate measurements.</p>

      <FileUploader onFile={handleFile} disabled={loading} />

      {loading && (
        <div className="loading-state" aria-live="polite">
          <span className="spinner" aria-hidden="true" />
          Processing file…
        </div>
      )}

      {error && <ErrorMessage message={error} />}
    </main>
  );
}
