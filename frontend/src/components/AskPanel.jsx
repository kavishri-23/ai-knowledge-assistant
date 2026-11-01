import { useEffect, useRef, useState } from "react";
import { askStream } from "../api";

function pageLabel(source) {
  return source.page_start === source.page_end
    ? `Page ${source.page_start}`
    : `Pages ${source.page_start}–${source.page_end}`;
}

/** Turns "[1]" markers in the answer into buttons that jump to the matching passage. */
function AnswerText({ text, onCite }) {
  return text.split(/(\[\d+\])/g).map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) return <span key={index}>{part}</span>;
    const number = Number(match[1]);
    return (
      <button
        key={index}
        type="button"
        className="cite"
        onClick={() => onCite(number)}
        aria-label={`Show source ${number}`}
      >
        {number}
      </button>
    );
  });
}

export default function AskPanel({ doc }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [cited, setCited] = useState([]);
  const [notFound, setNotFound] = useState(false);
  const [asking, setAsking] = useState(false);
  const [asked, setAsked] = useState(false);
  const [error, setError] = useState("");
  const [activeSource, setActiveSource] = useState(null);
  const controllerRef = useRef(null);

  useEffect(() => () => controllerRef.current?.abort(), []);

  const ask = async (event) => {
    event.preventDefault();
    const text = question.trim();
    if (!text || asking) return;

    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setAsking(true);
    setAsked(true);
    setError("");
    setAnswer("");
    setSources([]);
    setCited([]);
    setNotFound(false);
    setActiveSource(null);

    try {
      await askStream({
        documentId: doc.id,
        question: text,
        signal: controller.signal,
        onEvent: (item) => {
          if (item.type === "sources") setSources(item.sources);
          else if (item.type === "token") setAnswer((previous) => previous + item.text);
          else if (item.type === "done") {
            setCited(item.cited);
            setNotFound(item.not_found);
          } else if (item.type === "error") setError(item.message);
        },
      });
    } catch (failure) {
      if (failure.name !== "AbortError") setError(failure.message);
    } finally {
      if (controllerRef.current === controller) setAsking(false);
    }
  };

  const showSource = (number) => {
    setActiveSource(number);
    document.getElementById(`source-${number}`)?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  };

  const showSources = sources.length > 0 && !notFound;

  return (
    <section className="ask">
      <header className="ask-header">
        <h1>{doc.filename}</h1>
        <p className="muted">
          {doc.total_pages} pages, {doc.total_chunks} passages indexed
        </p>
      </header>

      <form className="ask-form" onSubmit={ask}>
        <label htmlFor="question" className="visually-hidden">
          Your question
        </label>
        <input
          id="question"
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask something this document can answer"
          maxLength={1000}
          autoComplete="off"
        />
        <button type="submit" className="button primary" disabled={asking || !question.trim()}>
          {asking ? "Answering…" : "Ask"}
        </button>
      </form>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      {asked && (
        <div className="answer" aria-live="polite">
          {answer ? (
            <p className={notFound ? "answer-text muted" : "answer-text"}>
              <AnswerText text={answer} onCite={showSource} />
            </p>
          ) : (
            !error && <p className="muted">Searching the document…</p>
          )}
        </div>
      )}

      {showSources && (
        <div className="sources">
          <h2>Passages from the document</h2>
          <p className="muted">
            Highlighted passages are the ones the answer cites. Match is how closely a passage
            fits your question (1.00 is identical).
          </p>
          <ol>
            {sources.map((source) => {
              const isCited = cited.includes(source.number);
              const classes = ["source"];
              if (isCited) classes.push("cited");
              if (activeSource === source.number) classes.push("active");
              return (
                <li key={source.number} id={`source-${source.number}`} className={classes.join(" ")}>
                  <div className="source-head">
                    <strong>
                      [{source.number}] {pageLabel(source)}
                    </strong>
                    <span className="muted">match {source.similarity.toFixed(2)}</span>
                  </div>
                  <p>{source.text}</p>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </section>
  );
}
