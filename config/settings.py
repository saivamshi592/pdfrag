
import os


class Settings:
    @property
    def MONGO_URI(self):
        return os.getenv("MONGO_URI")

    @property
    def MONGO_DB_NAME(self):
        return os.getenv("MONGO_DB_NAME", "PDFRag")

    @property
    def MONGO_COLLECTION_NAME(self):
        return os.getenv("MONGO_COLLECTION_NAME", "ghmdocuments")

    @property
    def AZURE_STORAGE_CONNECTION_STRING(self):
        return os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")

    @property
    def AZURE_OPENAI_API_KEY(self):
        return os.getenv("AZURE_OPENAI_API_KEY")

    @property
    def AZURE_OPENAI_ENDPOINT(self):
        return os.getenv("AZURE_OPENAI_ENDPOINT")

    @property
    def AZURE_OPENAI_API_VERSION(self):
        return os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

    @property
    def AZURE_OPENAI_EMBEDDING_DEPLOYMENT(self):
        return os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    @property
    def EMBEDDING_BATCH_SIZE(self):
        return int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))

    @property
    def MAX_TOP_K(self):
        return int(os.getenv("MAX_TOP_K", "20"))
    
    @property
    def AZURE_OPENAI_CHAT_DEPLOYMENT(self):
        return os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o")

    @property
    def LLM_PROVIDER(self):
        return os.getenv("LLM_PROVIDER", "azure").lower()

    @property
    def GROQ_API_KEY(self):
        return os.getenv("GROQ_API_KEY")

    @property
    def GROQ_MODEL(self):
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


settings = Settings()
