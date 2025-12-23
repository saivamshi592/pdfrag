import logging
from typing import List, Optional
from openai import AzureOpenAI
from config.settings import settings

_embedding_client = None

def get_embedding_client() -> Optional[AzureOpenAI]:
    global _embedding_client
    if _embedding_client:
        return _embedding_client

    if (
        settings.AZURE_OPENAI_API_KEY
        and settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    ):
        try:
            logging.info("Initializing Azure OpenAI Embedding Client...")
            _embedding_client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
            return _embedding_client
        except Exception as e:
            logging.error(f"Failed to initialize Azure OpenAI client: {e}")
            return None
    else:
        logging.warning("Azure OpenAI Embedding configuration missing.")
        return None

def generate_embeddings(text_chunks: List[str]) -> List[List[float]]:
    if not text_chunks:
        return []

    client = get_embedding_client()
    if not client:
        logging.error("Embedding client not available. Returning empty embeddings.")
        return []

    try:
        response = client.embeddings.create(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=text_chunks,
        )
        return [item.embedding for item in response.data]

    except Exception as e:
        logging.exception(f"Azure embedding generation failed: {e}")
        # Return empty list instead of raising, or maybe specific behavior? 
        # User said "If embedding generation ... fails, log error and still return success for upload".
        # But this function is raw. Let's return empty list or raise?
        # User said "Chat and upload APIs must continue to work...".
        # If I return [], the caller handles it.
        return []
