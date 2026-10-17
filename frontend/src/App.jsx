
import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [file, setFile] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const uploadPDF = async () => {
    if (!file) {
      setMessage("Please select a PDF first.");
      return;
    }

    setLoading(true);
    setMessage("Uploading and processing your PDF...");
    setAnswer("");
    setSources([]);
    setUploadedFilename("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_URL}/store-pdf`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed.");
      }

      setUploadedFilename(data.filename);
      setMessage(
        `Upload successful! ${data.total_pages} pages processed and ${data.total_chunks_stored} text chunks stored.`
      );
    } catch (error) {
      setMessage(error.message || "Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  };

  const askQuestion = async () => {
    if (!question.trim()) {
      setAnswer("Please enter a question.");
      setSources([]);
      return;
    }

    if (!uploadedFilename) {
      setAnswer("Please upload a PDF first.");
      setSources([]);
      return;
    }

    setLoading(true);
    setAnswer("");
    setSources([]);

    try {
      const params = new URLSearchParams({
        question: question.trim(),
        filename: uploadedFilename,
      });

      const response = await fetch(`${API_URL}/ask?${params.toString()}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Question failed.");
      }

      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (error) {
      setAnswer(error.message || "Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app">
      <header>
        <h1>AI Knowledge Assistant</h1>
        <p>Upload a PDF, ask questions, and verify answers from source text.</p>
      </header>

      <section className="panel">
        <h2>1. Upload your PDF</h2>

        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(event) => {
            setFile(event.target.files?.[0] || null);
            setUploadedFilename("");
            setAnswer("");
            setSources([]);
            setMessage("");
          }}
        />

        {file && <p>Selected file: {file.name}</p>}

        <button onClick={uploadPDF} disabled={loading}>
          Upload and Process
        </button>

        {message && <p className="message">{message}</p>}

        {uploadedFilename && (
          <p>
            <strong>Active document:</strong> {uploadedFilename}
          </p>
        )}
      </section>

      <section className="panel">
        <h2>2. Ask a question</h2>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            askQuestion();
          }}
        >
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. What is the company name?"
            disabled={loading}
          />

          <button type="submit" disabled={loading || !uploadedFilename}>
            Ask AI
          </button>
        </form>

        {loading && <p>Working on your request...</p>}

        {answer && (
          <div className="answer">
            <h3>Answer</h3>
            <p>{answer}</p>
          </div>
        )}

        {sources.length > 0 && (
          <div className="sources">
            <h3>Source text</h3>
            <p>
              These are the retrieved passages used as context for the answer.
            </p>

            {sources.map((source, index) => (
              <article
                className="source-item"
                key={`${source.page ?? "unknown"}-${index}`}
              >
                <h4>
                  Source {index + 1}
                  {source.page != null
                    ? ` — Page ${source.page}`
                    : " — Page not recorded"}
                </h4>
                <p>{source.text}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;
