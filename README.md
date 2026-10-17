\# AI Knowledge Assistant



An AI-powered application that allows users to upload a PDF document and ask questions about its contents. It retrieves relevant text passages and generates answers based on the uploaded document.



\## Features



\- Upload and process PDF documents

\- Ask questions in natural language

\- Retrieve relevant information using RAG (Retrieval-Augmented Generation)

\- Generate answers using a locally running LLM

\- Display source text and page numbers to help verify answers

\- Store and search document embeddings using ChromaDB



\## Technologies Used



\- \*\*Frontend:\*\* React, Vite, CSS

\- \*\*Backend:\*\* Python, FastAPI

\- \*\*LLM:\*\* Ollama (Llama 3.2)

\- \*\*Embeddings:\*\* Sentence Transformers (`all-MiniLM-L6-v2`)

\- \*\*Vector Database:\*\* ChromaDB

\- \*\*PDF Processing:\*\* PyMuPDF



\## How It Works



1\. Upload a PDF document.

2\. Extract and split the document text into smaller chunks.

3\. Convert the chunks into embeddings.

4\. Retrieve relevant chunks when a question is asked.

5\. Generate an answer using the retrieved context.

6\. Display the answer with supporting source text and page numbers.



\## Run Locally



\### 1. Clone the repository



```bash

git clone https://github.com/kavishri-23/ai-knowledge-assistant.git

cd ai-knowledge-assistant

```



\### 2. Set up the backend



```bash

cd backend

python -m venv venv

```



Activate the environment on Windows:



```powershell

.\\venv\\Scripts\\Activate.ps1

```



Install dependencies:



```bash

pip install -r requirements.txt

```



Start the backend:



```bash

uvicorn main:app --reload

```



Backend API documentation: http://127.0.0.1:8000/docs



\### 3. Set up Ollama



Install Ollama, then download the model:



```bash

ollama pull llama3.2:1b

```



Ensure Ollama is running before asking questions.



\### 4. Run the frontend



Open a second terminal:



```bash

cd frontend

npm install

npm run dev

```



Open the local URL shown in your terminal.



\## Future Improvements



\- Support multiple PDF documents

\- Add user authentication

\- Improve answer evaluation and error handling

\- Deploy the application online



\## Author



\*\*Kavishri Senguttuvan\*\*



GitHub: \[kavishri-23](https://github.com/kavishri-23)



