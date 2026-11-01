const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function errorMessage(response) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    return "The request was not valid.";
  } catch {
    return `Request failed (${response.status}).`;
  }
}

async function request(path, options) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error(`Cannot reach the server at ${API_URL}. Is the backend running?`);
  }
  if (!response.ok) throw new Error(await errorMessage(response));
  return response;
}

export async function listDocuments() {
  return (await request("/documents")).json();
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  return (await request("/documents", { method: "POST", body: form })).json();
}

export async function deleteDocument(id) {
  await request(`/documents/${id}`, { method: "DELETE" });
}

/**
 * Ask a question and receive the answer as it is written.
 * The server sends one JSON event per line: sources, token..., done (or error).
 */
export async function askStream({ documentId, question, signal, onEvent }) {
  const response = await request("/ask/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: documentId, question }),
    signal,
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newline;
    while ((newline = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer));
}
