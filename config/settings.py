import os


def _require_env(name: str, default=None):
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Settings:
    # MongoDB / Cosmos
    MONGO_URI = _require_env("MONGO_URI")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "PDFRag")
    MONGO_COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME", "ghmdocuments")

    # Azure Storage
    # Prefer explicit connection string if available, else fall back to Functions runtime string
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING") or os.environ.get("AzureWebJobsStorage")

    # Azure OpenAI
    AZURE_OPENAI_API_KEY = _require_env("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_ENDPOINT = _require_env("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = _require_env("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT = _require_env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    # Optional tuning
    EMBEDDING_BATCH_SIZE = int(os.environ.get("EMBEDDING_BATCH_SIZE", "16"))
    MAX_TOP_K = int(os.environ.get("MAX_TOP_K", "20"))
    
    AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

    # LLM Provider Config
    LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "azure").lower()
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


settings = Settings()
