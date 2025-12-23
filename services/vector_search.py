import logging
import numpy as np
from typing import List, Optional, Dict, Any

from services.mongo_store import mongo_store


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors
    """
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search_vectors(
    query_embedding: List[float],
    top_k: int = 5,
    category: Optional[str] = None,
    pdf_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform in-memory vector search using cosine similarity.
    Fetches embeddings from MongoDB and ranks them in Python.
    """

    # ✅ FIX: Correct MongoDB collection check
    if mongo_store.collection is None:
        logging.error("MongoDB collection not initialized")
        return []

    # Build MongoDB filter
    query_filter: Dict[str, Any] = {}
    
    # Global search if category is None or "All"
    if category and category.lower() != "all":
        query_filter["category"] = category
        
    if pdf_name:
        query_filter["pdf_name"] = pdf_name

    # Fetch candidate documents
    cursor = mongo_store.collection.find(
        query_filter,
        {
            "_id": 0,
            "text": 1,
            "embedding": 1,
            "category": 1,
            "pdf_name": 1,
            "year": 1,
            "chunk_index": 1,
            "page_number": 1
        }
    )

    query_vec = np.array(query_embedding, dtype=np.float32)
    scored_results: List[Dict[str, Any]] = []

    for doc in cursor:
        embedding = doc.get("embedding")
        if not embedding:
            continue

        doc_vec = np.array(embedding, dtype=np.float32)
        score = _cosine_similarity(query_vec, doc_vec)
        
        # Light Orchestration: Newer year preferred
        # Simple linear boost: 0.0005 per year since 2000
        # e.g. 2025 (+0.0125), 2000 (+0)
        year = doc.get("year", 2000)
        year_boost = 0.0
        if isinstance(year, int):
            year_boost = max(0, (year - 2000)) * 0.0005
            
        final_score = score + year_boost

        scored_results.append({
            "text": doc.get("text"),
            "category": doc.get("category"),
            "pdf_name": doc.get("pdf_name"),
            "year": year,
            "chunk_index": doc.get("chunk_index"),
            "page_number": doc.get("page_number"),
            "score": final_score
        })

    # Sort by similarity score (descending)
    scored_results.sort(key=lambda x: x["score"], reverse=True)

    return scored_results[:top_k]
