import time
import logging
from typing import List
from openai import AzureOpenAI, RateLimitError
from config.settings import settings

BATCH_SIZE = 25          # safe for S0 tier
SLEEP_SECONDS = 1.5      # throttle


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    if not (
        settings.AZURE_OPENAI_API_KEY
        and settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
    ):
        logging.error("Azure OpenAI embedding config missing")
        return []

    client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]

        try:
            response = client.embeddings.create(
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                input=batch,
            )
            all_embeddings.extend([r.embedding for r in response.data])

            time.sleep(SLEEP_SECONDS)

        except RateLimitError as e:
            logging.warning("Rate limit hit, sleeping and retrying")
            time.sleep(60)
            # FIX: Combine previous results with the result of the retry to preserve total count
            return all_embeddings + generate_embeddings(texts[i:])

        except Exception:
            logging.exception("Embedding generation failed")
            return []

    return all_embeddings


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for a single string.
    Wrapper around generate_embeddings to satisfy chat_api import.
    Used by chat_api (single query).
    """
    results = generate_embeddings([text])
    return results[0] if results else []
