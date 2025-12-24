import logging
from typing import List
from openai import AzureOpenAI
from config.settings import settings


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of strings using Azure OpenAI.
    Lazy initialization: Client is created only when this function is called.
    Used by blob_trigger (batch processing).
    """
    if not texts:
        return []

    if not (
        settings.AZURE_OPENAI_API_KEY
        and settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    ):
        logging.error("Azure OpenAI embedding config missing")
        return []

    try:
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )

        response = client.embeddings.create(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=texts,
        )

        return [r.embedding for r in response.data]

    except Exception:
        logging.exception("Embedding generation failed")
        return []


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for a single string.
    Wrapper around generate_embeddings to satisfy chat_api import.
    Used by chat_api (single query).
    """
    results = generate_embeddings([text])
    return results[0] if results else []
