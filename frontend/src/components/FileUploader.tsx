import { useRef, useState, DragEvent, ChangeEvent } from "react";

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED = [".kml", ".zip"];
const MAX_MB = 50;

export default function FileUploader({ onFile, disabled }: Props) {
  const [dragging, setDragging] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  function validate(file: File): string | null {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !ACCEPTED.includes(`.${ext}`)) {
      return `Unsupported file type ".${ext}". Accepted: .kml, .zip`;
    }
    if (file.size > MAX_MB * 1024 * 1024) {
      return `File exceeds ${MAX_MB} MB limit.`;
    }
    return null;
  }

  function handleFile(file: File) {
    const err = validate(file);
    if (err) {
      setValidationError(err);
      return;
    }
    setValidationError(null);
    onFile(file);
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }

  return (
    <div className="uploader">
      <div
        className={`drop-zone ${dragging ? "dragging" : ""} ${disabled ? "disabled" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="Upload area"
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
      >
        <p className="drop-icon">📂</p>
        <p>Drag &amp; drop a file here, or <span className="link">browse</span></p>
        <p className="hint">Supported: KML / ZIP &nbsp;·&nbsp; Maximum size: {MAX_MB} MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".kml,.zip"
          onChange={onChange}
          style={{ display: "none" }}
          disabled={disabled}
        />
      </div>
      {validationError && (
        <p className="validation-error" role="alert">{validationError}</p>
      )}
    </div>
  );
}
