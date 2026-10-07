import type { FileStatus as Status } from "../types/file";

const STATUS_LABELS: Record<Status, string> = {
  UPLOADED: "Uploaded",
  PROCESSING: "Processing…",
  COMPLETED: "Completed",
  FAILED: "Failed",
};

const STATUS_CLASS: Record<Status, string> = {
  UPLOADED: "status-uploaded",
  PROCESSING: "status-processing",
  COMPLETED: "status-completed",
  FAILED: "status-failed",
};

interface Props {
  status: Status;
}

export default function FileStatus({ status }: Props) {
  return (
    <span className={`status-badge ${STATUS_CLASS[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  );
}
