import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import FileSummary from "../components/FileSummary";
import MeasurementTable from "../components/MeasurementTable";
import Pagination from "../components/Pagination";
import ErrorMessage from "../components/ErrorMessage";
import { getFile, getMeasurements } from "../services/api";
import type { FileDetailResponse } from "../types/file";
import type { MeasurementResponse, MeasurementsResponse } from "../types/measurement";

const PAGE_SIZE = 100;

export default function ResultsPage() {
  const { fileId } = useParams<{ fileId: string }>();
  const navigate = useNavigate();

  const [file, setFile] = useState<FileDetailResponse | null>(null);
  const [measurementsData, setMeasurementsData] = useState<MeasurementsResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loadingFile, setLoadingFile] = useState(true);
  const [loadingMeasurements, setLoadingMeasurements] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!fileId) return;
    setLoadingFile(true);
    getFile(fileId)
      .then(setFile)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingFile(false));
  }, [fileId]);

  useEffect(() => {
    if (!fileId || !file || file.status !== "COMPLETED") return;
    setLoadingMeasurements(true);
    getMeasurements(fileId, page, PAGE_SIZE)
      .then(setMeasurementsData)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingMeasurements(false));
  }, [fileId, file, page]);

  if (loadingFile) {
    return (
      <main className="page">
        <div className="loading-state" aria-live="polite">
          <span className="spinner" aria-hidden="true" /> Loading file…
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page">
        <ErrorMessage message={error} />
        <button className="btn-secondary" onClick={() => navigate("/")}>← Upload another file</button>
      </main>
    );
  }

  if (!file) return null;

  return (
    <main className="page results-page">
      <button className="btn-secondary back-btn" onClick={() => navigate("/")}>
        ← Upload another file
      </button>

      <FileSummary file={file} />

      {file.status === "COMPLETED" && (
        <section className="measurements-section">
          <h2>Measurements</h2>
          {loadingMeasurements ? (
            <div className="loading-state" aria-live="polite">
              <span className="spinner" aria-hidden="true" /> Loading measurements…
            </div>
          ) : (
            <>
              <MeasurementTable
                measurements={measurementsData?.measurements ?? []}
              />
              {measurementsData && (
                <Pagination
                  page={page}
                  pageSize={PAGE_SIZE}
                  total={measurementsData.total}
                  onPageChange={setPage}
                />
              )}
            </>
          )}
        </section>
      )}

      {file.status === "FAILED" && (
        <div className="error-banner">
          <strong>Processing failed:</strong> {file.error_message ?? "Unknown error."}
        </div>
      )}
    </main>
  );
}
