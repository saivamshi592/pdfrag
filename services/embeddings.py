import logging
from typing import List
from openai import AzureOpenAI
from config.settings import settings

_client = None

# Initialize Azure OpenAI client
if (
    settings.AZURE_OPENAI_API_KEY
    and settings.AZURE_OPENAI_ENDPOINT
    and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
):
    _client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )

def generate_embeddings(text_chunks: List[str]) -> List[List[float]]:
    if not text_chunks:
        return []

    if not _client:
        raise RuntimeError(
            "Azure OpenAI config missing. Check AZURE_OPENAI_* settings."
        )

    try:
        response = _client.embeddings.create(
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            input=text_chunks,
        )
        return [item.embedding for item in response.data]

    except Exception:
        logging.exception("Azure embedding generation failed")
        raise
