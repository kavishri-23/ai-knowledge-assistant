import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, uploadDocument } from "./api";
import AskPanel from "./components/AskPanel.jsx";
import DocumentSidebar from "./components/DocumentSidebar.jsx";

const BUSY = ["pending", "processing"];

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [actionError, setActionError] = useState("");
  const [connectionError, setConnectionError] = useState("");

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
      setConnectionError("");
    } catch (error) {
      setConnectionError(error.message);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // While any document is still being indexed, check on it every 1.5 seconds.
  useEffect(() => {
    if (!documents.some((doc) => BUSY.includes(doc.status))) return undefined;
    const timer = setInterval(refresh, 1500);
    return () => clearInterval(timer);
  }, [documents, refresh]);

  const handleUpload = async (file) => {
    setActionError("");
    setUploading(true);
    try {
      const doc = await uploadDocument(file);
      await refresh();
      setSelectedId(doc.id);
    } catch (error) {
      setActionError(error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (doc) => {
    if (!window.confirm(`Remove "${doc.filename}"? Its indexed text will be deleted.`)) return;
    setActionError("");
    try {
      await deleteDocument(doc.id);
      if (selectedId === doc.id) setSelectedId(null);
      await refresh();
    } catch (error) {
      setActionError(error.message);
    }
  };

  const selected = documents.find((doc) => doc.id === selectedId) ?? null;

  return (
    <div className="layout">
      <DocumentSidebar
        documents={documents}
        selectedId={selectedId}
        uploading={uploading}
        error={actionError || connectionError}
        onSelect={setSelectedId}
        onUpload={handleUpload}
        onDelete={handleDelete}
      />

      <main className="main">
        {!selected && (
          <div className="empty">
            <h1>Ask a question, check the page</h1>
            <p>
              Upload a PDF, then ask about it. Every answer points to the passages it used, so
              you can verify it yourself.
            </p>
          </div>
        )}

        {selected && BUSY.includes(selected.status) && (
          <div className="empty">
            <h1>{selected.filename}</h1>
            <p>Reading and indexing this document. Long PDFs can take a minute.</p>
          </div>
        )}

        {selected && selected.status === "failed" && (
          <div className="empty">
            <h1>{selected.filename}</h1>
            <p role="alert">{selected.error || "This document could not be processed."}</p>
            <p>Remove it from the list and upload a different file.</p>
          </div>
        )}

        {selected && selected.status === "ready" && <AskPanel key={selected.id} doc={selected} />}
      </main>
    </div>
  );
}
