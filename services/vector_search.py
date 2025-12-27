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
    
    # Global Search Logic:
    # If category is "all" (Global Search), we intentionally DO NOT filter by category.
    # This ensures we retrieve candidates from ALL categories (Science, Maths, Manuals, etc.)
    # and let the semantic similarity score decide the winner.
    
    # 1. Apply Filename Scope (Most Specific) -- Still respected if provided
    if pdf_name:
        mongo_filter["pdf_name"] = pdf_name

    # 2. Apply Category Scope -- ONLY if specific (not "all")
    elif category and category.lower() != "all":
         # FIX: Use case-insensitive regex to match 'Maths', 'maths', 'MATHS'
        mongo_filter["category"] = {"$regex": f"^{category.strip()}$", "$options": "i"}

    logging.info(f"Vector search filter: {mongo_filter}")

    docs = list(collection.find(mongo_filter))

    scored = []
    for doc in docs:
        emb = np.array(doc.get("embedding", []), dtype=np.float32)
        score = cosine_similarity(query_vec, emb)
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Progressive Deep Search Ranking
    # 1. Return Top 1 (Best Match) with lenient threshold to ensure an answer 
    # 2. Return Top 2-3 with moderate threshold for context
    # 3. Return Top 4+ only if high relevance (strict)
    
    results = []
    for i, (score, doc) in enumerate(scored):
        if len(results) >= top_k:
            break

        # Tier 1: Single Best Match (Top 1)
        # prioritization: explicit > semantic > keyword
        if i == 0:
            if score >= 0.25: # Lenient for the "best" candidate
                results.append(doc)
            continue

        # Tier 2: Core Context (Top 2-3)
        if i < 3:
            if score >= 0.28: # Moderate relevance
                results.append(doc)
            continue

        # Tier 3: Extended Context (Top 4+)
        if score >= 0.30: # Strict relevance (original threshold)
            results.append(doc)

    return results
