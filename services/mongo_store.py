import logging
import os
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config.settings import settings

# Global cache for the client/collection
_mongo_client = None
_mongo_collection = None

def get_mongo_collection():
    """
    Lazy initialization of MongoDB client and collection.
    Returns None if connection fails or MONGO_URI is missing.
    """
    global _mongo_client, _mongo_collection

    if _mongo_collection:
        return _mongo_collection

    if not settings.MONGO_URI:
        logging.warning("MONGO_URI not set. Running without MongoDB.")
        return None

    try:
        # Patch DNS for local if needed, inside the function to avoid module-level side effects
        # (Only really needed for some local setups with SRV)
        try:
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
            dns.resolver.default_resolver = resolver
        except ImportError:
            pass
        except Exception as e:
            logging.warning(f"DNS patch failed: {e}")

        # Initialize Client
        logging.info("Initializing MongoDB Client...")
        _mongo_client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=3000
        )
        
        # Verify connection
        _mongo_client.admin.command("ping")
        
        db = _mongo_client[settings.MONGO_DB_NAME]
        _mongo_collection = db[settings.MONGO_COLLECTION_NAME]
        
        logging.info(f"Connected to MongoDB: {settings.MONGO_DB_NAME}.{settings.MONGO_COLLECTION_NAME}")
        return _mongo_collection

    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
        # Ensure we don't crash the app, just return None
        _mongo_client = None
        _mongo_collection = None
        return None

class MongoStore:
    """
    Wrapper class that uses the lazy get_mongo_collection function.
    """
    @property
    def collection(self):
        return get_mongo_collection()

    def delete_category(self, category: str):
        col = self.collection
        if col is None:
            logging.warning("MongoDB unavailable, cannot delete category")
            return
        
        try:
            result = col.delete_many({"category": category})
            logging.info("Deleted %d records for category: %s", result.deleted_count, category)
        except Exception as e:
            logging.error(f"Error deleting category: {e}")

    def delete_pdf(self, category: str, filename: str):
        col = self.collection
        if col is None:
             logging.warning("MongoDB unavailable, cannot delete PDF")
             return
            
        try:
            result = col.delete_many({
                "category": category,
                "pdf_name": filename
            })
            logging.info("Deleted %d records for PDF: %s/%s", result.deleted_count, category, filename)
        except Exception as e:
            logging.error(f"Error deleting PDF: {e}")

    def list_pdfs(self, category: str) -> list:
        col = self.collection
        if col is None:
            return []
        
        try:
            return col.distinct("pdf_name", {"category": category})
        except Exception as e:
            logging.error(f"Error listing PDFs: {e}")
            return []

    def get_all_categories(self) -> list:
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
                
            return list(cleaned)
        except Exception as e:
            logging.error(f"Error getting categories: {e}")
            return ["uncategorized"]

    def save_chunks(self, category: str, filename: str, chunks: list, embeddings: list, metadata: dict = None):
        col = self.collection
        if col is None:
            logging.error("MongoDB unavailable, cannot save chunks")
            return # Don't raise, just log as per requirements to not crash

        if len(chunks) != len(embeddings):
            logging.error("Chunks and embeddings length mismatch")
            return

        try:
            # Remove old chunks
            col.delete_many({
                "category": category,
                "pdf_name": filename
            })

            if metadata is None:
                metadata = {}
            
            year = metadata.get("year", 2025)
            date_str = metadata.get("date", "")

            documents = []
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                documents.append({
                    "category": category,
                    "pdf_name": filename,
                    "chunk_index": idx,
                    "text": chunk,
                    "embedding": embedding,
                    "year": year,
                    "date": date_str
                })

            if documents:
                col.insert_many(documents)
                logging.info(
                    "Inserted %d chunks for %s (Year: %s)",
                    len(documents),
                    filename,
                    year
                )
        except Exception as e:
            logging.error(f"Error saving chunks: {e}")

# Singleton instance (safe to create because __init__ is now empty/implicit or lazy)
# Note: MongoStore() class content changed, so no __init__ running connection logic.
mongo_store = MongoStore()
