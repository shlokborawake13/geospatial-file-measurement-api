import type { MeasurementResponse } from "../types/measurement";

interface Props {
  measurements: MeasurementResponse[];
}

function formatValue(m: MeasurementResponse): string {
  if (m.value == null) return "—";
  return m.value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function MeasurementTable({ measurements }: Props) {
  if (measurements.length === 0) {
    return <p className="empty-state">No measurements to display.</p>;
  }

  return (
    <div className="table-wrapper">
      <table className="measurement-table">
        <thead>
          <tr>
            <th>Feature #</th>
            <th>Geometry Type</th>
            <th>Measurement</th>
            <th>Value</th>
            <th>Unit</th>
            <th>Measurement CRS</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {measurements.map((m) => (
            <tr key={m.feature_id} className={m.status === "FAILED" ? "row-failed" : ""}>
              <td>{m.feature_index}</td>
              <td>{m.geometry_type}</td>
              <td>{m.measurement_type ?? "—"}</td>
              <td className="value-cell">{formatValue(m)}</td>
              <td>{m.unit ?? "—"}</td>
              <td>{m.measurement_crs ?? "—"}</td>
              <td>
                <span className={`status-badge status-${m.status.toLowerCase()}`}>
                  {m.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
