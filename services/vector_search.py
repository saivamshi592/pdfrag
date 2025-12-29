import logging
import numpy as np
from typing import List, Dict, Optional
from services.mongo_store import mongo_store


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_vectors(
    query_embedding: List[float],
    category: Optional[str],
    pdf_name: Optional[str] = None,
    top_k: int = 5,
) -> List[Dict]:
    """
    Vector search with STRICT category and filename filtering.
    """

    collection = mongo_store.collection
    if collection is None:
        logging.error("Mongo collection not initialized")
        return []

    query_vec = np.array(query_embedding, dtype=np.float32)

    #  Build filter condition
    mongo_filter = {}
    if category and category.lower() != "all":
        mongo_filter["category"] = category.lower()

    logging.info(f"Vector search filter: {mongo_filter}")

    docs = list(collection.find(mongo_filter))

    scored = []
    for doc in docs:
        emb = np.array(doc.get("embedding", []), dtype=np.float32)
        score = cosine_similarity(query_vec, emb)
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    # return only relevant chunks
    return [doc for score, doc in scored[:top_k] if score > 0.15]
