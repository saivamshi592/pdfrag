# 🚀 Azure PDF RAG Application (v1.3)

A serverless RAG (Retrieval-Augmented Generation) application built with **Azure Functions (Python)**. It ingests PDFs, creates embeddings using Azure OpenAI, stores them in MongoDB (Cosmos DB), and allows users to chat with their documents via a smart web interface.

---

## 📂 Project Structure

```
pdfrag1.0/
├── blob_trigger/       # ⚡ Processes PDF uploads
├── chat_api/           # 💬 Handles RAG queries
├── upload_api/         # 📤 Handles File Uploads
├── list_api/           # 📋 Lists PDFs/Categories
├── delete_api/         # 🗑️ Deletes Data
├── debug_api/          # 🏥 Diagnostics
├── services/           # 🧠 Core Logic (Mongo, OpenAI, PDF)
├── frontend/           # 🎨 UI (served via API)
├── requirements.txt    # 📦 Python Dependencies
└── host.json           # ⚙️ Host Config
```

---

##  Architecture

1.  **Blob Trigger (`blob_trigger`)**:
    -   Automatically triggers when a PDF is uploaded to the Azure Storage container `pdfs`.
    -   Extracts text -> Chunks content -> Generates Embeddings -> Saves to MongoDB.
    -   **Smart Logic**: Checks duplicates to avoid expensive reprocessing.

2.  **API Services**:
    -   **`chat_api`**: Handles user queries, retrieves relevant chunks from Mongo, and generates AI answers.
    -   **`upload_api`**: Handles file uploads from the UI directly to Blob Storage.
    -   **`list_api`**: Lists available categories and PDFs.
    -   **`delete_api`**: Manages data cleanup (deletes chunks and blobs).
    -   **`debug_api`**: Diagnostics tool to verify server health and dependency installation.

3.  **Frontend**:
    -   Hosted at `/api/ui/index.html`.
    -   Features: Chat interface, File Upload, Category Management, and "Self-Healing" capabilities.

---

## 🛠️ Prerequisites

-   **Python 3.11** (Strictly required for Azure compatibility)
-   **Azure Functions Core Tools v4**
-   **Azure Subscription** (Function App, Blob Storage, Azure OpenAI, Cosmos DB/MongoDB)
-   **VS Code** with Azure Functions Extension

---

## ⚙️ Configuration (Environment Variables)

Whether running locally (`local.settings.json`) or on Azure (Environment Variables), these keys are **REQUIRED**:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "<Common_Connection_String_For_Function_And_Blobs>",
    "AZURE_STORAGE_CONNECTION_STRING": "<Same_As_Above>",
    "MONGO_URI": "mongodb://<username>:<password>@<host>:<port>/?ssl=true&retrywrites=false&appName=@pdfragfunction002@",
    "MONGO_DB_NAME": "PDFRag",
    "MONGO_COLLECTION_NAME": "ghmdocuments",
    "AZURE_OPENAI_API_KEY": "<sk-...>",
    "AZURE_OPENAI_ENDPOINT": "https://<your-resource>.openai.azure.com/",
    "AZURE_OPENAI_CHAT_DEPLOYMENT": "gpt-4o",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
    "SCM_DO_BUILD_DURING_DEPLOYMENT": "1",
    "ENABLE_ORYX_BUILD": "true"
  }
}
```

> **🔥 Critical for Azure Deployment:**
> Ensure `SCM_DO_BUILD_DURING_DEPLOYMENT` is set to `1` in Azure Portal Config.
> Ensure `WEBSITE_RUN_FROM_PACKAGE` is **NOT** set (or deleted) to allow dependency installation.

---

## 📦 How to Deploy (Correctly)

Simple "Zip Deploy" often fails to install Python dependencies (`pymongo`, `openai`, etc.). Use the following robust command from your terminal:

```powershell
# 1. Navigate to the project root (where requirements.txt is)
cd path/to/pdfrag1.0

# 2. Force Remote Build (Installs Libraries on Server)
func azure functionapp publish <YOUR_FUNCTION_APP_NAME> --build remote
```

**Verification:**
After deployment, visit: `https://<YOUR_APP>.azurewebsites.net/api/debug_api`
It should return `{"status": "alive", "imports": { "pymongo": "Success", ... }}`.

---

## 📂 Usage Guide

### 1. Uploading Documents
-   **Via UI:** Go to `/api/ui/index.html` -> "Upload PDF".
-   **Via Storage Explorer:** Upload files into a folder structure: `pdfs/<category_name>/filename.pdf`.
    -   *Example:* `pdfs/maths/algebra_101.pdf`
    -   *Note:* The `<category>` folder name is automatically used as a metadata filter.

### 2. Chatting
-   Select a **Scope** (Specific Category or "All").
-   Ask a question. The system will retrieve relevant chunks and generate an answer with citations.

---

## 🚑 Troubleshooting

| Error | Cause | Fix |
| :--- | :--- | :--- |
| **500 Internal Server Error** | Missing Dependencies (`pymongo` not found) | Run `func azure functionapp publish ... --build remote` |
| **Mongo Connection Timeout** | Firewall Blocking Azure | whitelist `0.0.0.0/0` in MongoDB Atlas OR allow "Azure Services" in Cosmos DB Firewall. |
| **CORS Error** | Browser blocked from calling API | Azure Portal -> CORS -> Add your domain (or `*` for dev). |
| **Blob Trigger Not Firing** | Storage Mismatch | Ensure `AzureWebJobsStorage` and `AZURE_STORAGE_CONNECTION_STRING` match. |
