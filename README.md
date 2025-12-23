# PDF RAG Application (Azure Functions + Python)

This project allows for ingesting PDFs from Azure Blob Storage, chunking and embedding them, storing vectors in Cosmos DB (MongoDB API), and querying them via an HTTP API.

## Project Structure

```
pdfchatapp/
├── blob_trigger/       # Triggered on PDF upload
├── chat_api/           # HTTP API for RAG chat
├── services/           # Business logic (PDF processing, embeddings, DB)
├── config/             # Configuration management
├── host.json           # Azure Functions host config
├── local.settings.json # Local env vars (Git ignored usually)
└── requirements.txt    # Python dependencies
```

## Prerequisites

- Python 3.11
- Azure Functions Core Tools v4
- Azurite (for local storage emulation)
- MongoDB / Cosmos DB connection string

## Setup & Run

1. **Create Virtual Environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   - Update `local.settings.json` with your real keys if needed (MongoDB, OpenAI).
   - Ensure Azurite is running.

4. **Run Locally:**
   ```bash
   func start
   ```

## Functions

### 1. Blob Trigger (`blob_trigger`)
- **Trigger:** Blob upload to container configured in `function.json` (default: `pdfs/{category}/{name}`).
- **Action:** Extracts text, chunks it, generates embeddings, saves to MongoDB.

### 2. Chat API (`chat_api`)
- **Trigger:** HTTP POST to `/api/chat`.
- **Action:** Embeds user question, searches MongoDB, returns relevant context/answer.

## Deployment

```bash
func azure functionapp publish <APP_NAME>
## Notes

- PDFs must be uploaded using the following folder structure:
pdfs/<category>/<filename>.pdf

makefile
Copy code
Example:
pdfs/maths/algebra.pdf
pdfs/science/physics.pdf

pgsql
Copy code

- The `<category>` folder name is stored as metadata and used for filtered RAG search.
```

## New Features (v2)

### 1. Date & Year Extraction
- Automatically extracts `Year` and `Date` from PDF metadata or content.
- Defaults to `2025` if not found.
- Newer documents are preferred in Global Search.

### 2. Category Management
- **Upload Behavior**: Uploading a file into a category **WIPES** the existing category data in MongoDB and replaces it with the new file(s). This ensures a clean slate for the category.
- **Manual Delete**: Use the "Delete Category" button in the UI to manually clear all data for a specific category.

### 3. Global vs Category Search
- **Category Search**: Scopes the search strictly to the selected category (e.g., "Maths").
- **Global Search**: If "All" is selected, searches across all documents. Results are ranked by **Relevance** + **Freshness** (Year Boost).

### 4. Rich Search Results
- Search results now include detailed metadata:
  - Source File
  - Category
  - Year
  - Download Link (Direct blob storage access)

