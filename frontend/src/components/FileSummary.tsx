import type { FileDetailResponse } from "../types/file";
import FileStatus from "./FileStatus";

interface Props {
  file: FileDetailResponse;
}

export default function FileSummary({ file }: Props) {
  return (
    <div className="file-summary">
      <h2>{file.filename}</h2>
      <table className="summary-table">
        <tbody>
          <tr><td>File ID</td><td><code>{file.id}</code></td></tr>
          <tr><td>Type</td><td>{file.file_type}</td></tr>
          <tr><td>Status</td><td><FileStatus status={file.status} /></td></tr>
          <tr><td>Features</td><td>{file.feature_count ?? "—"}</td></tr>
          <tr><td>Original CRS</td><td>{file.crs ?? "—"}</td></tr>
          <tr>
            <td>Processing time</td>
            <td>{file.processing_duration_ms != null ? `${file.processing_duration_ms} ms` : "—"}</td>
          </tr>
          {file.error_message && (
            <tr>
              <td>Error</td>
              <td className="error-text">{file.error_message}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
