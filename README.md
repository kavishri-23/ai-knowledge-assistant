# AI Knowledge Assistant

A PDF question-answering system built with Retrieval-Augmented Generation (RAG). Ask a question about a PDF and get an answer with the source text and page numbers, so every response can be verified.

![Python](https://img.shields.io/badge/Python-3.x-blue) ![ChromaDB](https://img.shields.io/badge/Vector%20DB-ChromaDB-green) ![Ollama](https://img.shields.io/badge/LLM-Ollama-black)

## Features
- Upload a PDF and ask questions about its content
- Vector search retrieves the most relevant passages from the document
- Answers are generated from the retrieved text, not from guesswork
- Every answer shows its source text and page number for verification
- Runs locally with Ollama, so no external API key is needed

## How It Works
1. **Load:** Read the PDF and extract text page by page.
2. **Chunk:** Split the text into smaller passages and keep the page number for each.
3. **Embed and store:** Convert each passage into a vector and store it in ChromaDB.
4. **Retrieve:** For a question, search ChromaDB for the most similar passages.
5. **Generate:** Send the question and the retrieved passages to the Ollama model to write the answer.
6. **Cite:** Return the answer along with the source text and page numbers.

## Tech Stack
| Area | Tools |
|------|-------|
| Language | Python |
| Vector database | ChromaDB |
| LLM runtime | Ollama |
| PDF parsing | PyPDF / pypdf |
| Interface | Command line |

## Project Structure
```
ai-knowledge-assistant/
│
├── backend/
│   ├── main.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md

## Getting Started

### Prerequisites
- Python 3.8 or higher
- [Ollama](https://ollama.com) installed and running

### Installation
```bash
git clone https://github.com/kavishri-23/ai-knowledge-assistant.git
cd ai-knowledge-assistant
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Download the model
```bash
ollama pull llama3
```
Use the same model name that your code uses.

### Run
```bash
python3 main.py
```

## Usage
1. Run the program and give the path to your PDF.
2. Wait while the document is processed and stored in ChromaDB.
3. Type a question about the document.
4. Read the answer and check the source text and page numbers shown below it.

## Example
```
Question: What is the main conclusion of the document?

Answer: <generated answer>

Sources:
- Page 5: "<relevant passage>"
- Page 8: "<relevant passage>"
```

## What I Learned
- Building a RAG pipeline with vector search
- Storing and querying embeddings with ChromaDB
- Running a local LLM with Ollama
- Showing sources in answers to make AI output verifiable

## Future Improvements
- Support multiple PDFs at once
- Add a web interface (FastAPI and React)
- Add chat history for follow-up questions

## Author
**Kavishri Senguttuvan**
[GitHub](https://github.com/kavishri-23) · [LinkedIn](https://www.linkedin.com/in/kavishrisenguttuvan)
