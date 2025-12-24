import os
import logging
from typing import Optional, List
from pymongo import MongoClient
from pymongo.collection import Collection

# Environment variables
MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "PDFRag")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "ghmdocuments")

_client: Optional[MongoClient] = None
_collection: Optional[Collection] = None


def get_mongo_collection() -> Optional[Collection]:
    """
    Lazily initialize MongoDB collection.
    IMPORTANT: Never use truthy checks on Collection.
    """
    global _client, _collection

    #  FIX: explicit None check
    if _collection is not None:
        return _collection

    if not MONGO_URI:
        logging.error("MONGO_URI not set")
        return None

    try:
        logging.info("Initializing MongoDB client")
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

        # Force connection check
        _client.admin.command("ping")

        db = _client[MONGO_DB_NAME]
        _collection = db[MONGO_COLLECTION_NAME]

        logging.info(
            "MongoDB connected: %s.%s",
            MONGO_DB_NAME,
            MONGO_COLLECTION_NAME
        )
        return _collection

    except Exception:
        logging.exception("MongoDB connection failed")
        _collection = None
        return None


class MongoStore:
    """
    Safe wrapper around MongoDB operations.
    """

    @property
    def collection(self) -> Optional[Collection]:
        return get_mongo_collection()

    def delete_pdf(self, category: str, filename: str) -> None:
        col = self.collection
        if col is None:
            return
        col.delete_many({
            "category": category,
            "pdf_name": filename
        })

    #  FIX: this method was missing (list_api crash)
    def get_all_categories(self) -> List[str]:
        col = self.collection
        if col is None:
            return ["uncategorized"]

        try:
            cats = col.distinct("category")
            cleaned = set()

            for c in cats:
                if c:
                    cleaned.add(c)
                else:
                    cleaned.add("uncategorized")

            if "uncategorized" not in cleaned:
                cleaned.add("uncategorized")

            return sorted(cleaned)

        except Exception:
            logging.exception("Failed to fetch categories")
            return ["uncategorized"]


# Singleton instance
mongo_store = MongoStore()
