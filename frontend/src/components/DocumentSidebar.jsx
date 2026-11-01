function describe(doc) {
  if (doc.status === "pending" || doc.status === "processing") return "Indexing…";
  if (doc.status === "failed") return "Could not be processed";
  return `${doc.total_pages} pages`;
}

export default function DocumentSidebar({
  documents,
  selectedId,
  uploading,
  error,
  onSelect,
  onUpload,
  onDelete,
}) {
  const handleChange = (event) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow choosing the same file again later
    if (file) onUpload(file);
  };

  return (
    <aside className="sidebar">
      <div className="brand">AI Knowledge Assistant</div>

      <label className={`button primary${uploading ? " disabled" : ""}`}>
        {uploading ? "Uploading…" : "Upload a PDF"}
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleChange}
          disabled={uploading}
          hidden
        />
      </label>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <h2 className="sidebar-title">Your documents</h2>
      {documents.length === 0 && <p className="muted">Nothing uploaded yet.</p>}

      <ul className="doc-list">
        {documents.map((doc) => (
          <li key={doc.id} className={doc.id === selectedId ? "doc selected" : "doc"}>
            <button type="button" className="doc-main" onClick={() => onSelect(doc.id)}>
              <span className="doc-name">{doc.filename}</span>
              <span className={`doc-status ${doc.status}`}>{describe(doc)}</span>
            </button>
            <button
              type="button"
              className="link-button"
              onClick={() => onDelete(doc)}
              aria-label={`Remove ${doc.filename}`}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
