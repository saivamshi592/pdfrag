import logging

# ===== DNS PATCH (CRITICAL – FIXES LOCAL SRV DNS ISSUE) =====
try:
    import dns.resolver
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
    dns.resolver.default_resolver = resolver
    logging.info("Mongo DNS patched to Google DNS (8.8.8.8)")
except Exception as e:
    logging.warning(f"Mongo DNS patch failed: {e}")

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from config.settings import settings


class MongoStore:
    def __init__(self):
        self.client = None
        self.collection = None

        try:
            # IMPORTANT: DNS patch runs BEFORE this line
            self.client = MongoClient(
                settings.MONGO_URI,
                serverSelectionTimeoutMS=10000
            )

            # Force connection test
            self.client.admin.command("ping")

            db = self.client[settings.MONGO_DB_NAME]
            self.collection = db[settings.MONGO_COLLECTION_NAME]

            logging.info(
                "Connected to MongoDB %s.%s",
                settings.MONGO_DB_NAME,
                settings.MONGO_COLLECTION_NAME
            )

        except PyMongoError as e:
            logging.exception("MongoDB connection failed due to DNS / network issue")
            self.collection = None
            raise

    def delete_category(self, category: str):
        if self.collection is None:
            logging.warning("MongoDB collection not initialized, cannot delete category")
            return
        
        result = self.collection.delete_many({"category": category})
        logging.info("Deleted %d records for category: %s", result.deleted_count, category)

    def delete_pdf(self, category: str, filename: str):
        if self.collection is None:
             logging.warning("MongoDB collection not initialized")
             return
            
        result = self.collection.delete_many({
            "category": category,
            "pdf_name": filename
        })
        logging.info("Deleted %d records for PDF: %s/%s", result.deleted_count, category, filename)

    def list_pdfs(self, category: str) -> list:
        if self.collection is None:
            return []
        
        # Get distinct pdf_name for the category
        return self.collection.distinct("pdf_name", {"category": category})

    def get_all_categories(self) -> list:
        if self.collection is None:
            return ["uncategorized"]
        
        cats = self.collection.distinct("category")
        # Ensure uncategorized is present if not found, or at least normalized
        # But distinctive query returns what is there. 
        # We can enforce "uncategorized" to always be available if desired, 
        # or just return what is in DB. Requirements say "include Uncategorized".
        # Let's clean up None to "uncategorized" and deduplicate in caller or here.
        cleaned = set()
        for c in cats:
            if c:
                cleaned.add(c)
            else:
                cleaned.add("uncategorized")
        
        if "uncategorized" not in cleaned:
            cleaned.add("uncategorized")
            
        return list(cleaned)

    def save_chunks(self, category: str, filename: str, chunks: list, embeddings: list, metadata: dict = None):
        if self.collection is None:
            raise RuntimeError("MongoDB collection not initialized")

        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings length mismatch")

        # Remove old chunks for same PDF (redundant if category wiped, but safe)
        self.collection.delete_many({
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
            self.collection.insert_many(documents)
            logging.info(
                "Inserted %d chunks for %s (Year: %s)",
                len(documents),
                filename,
                year
            )


# Singleton instance (used by blob_trigger)
mongo_store = MongoStore()
