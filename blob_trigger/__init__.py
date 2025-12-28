import logging
import azure.functions as func
import os
import io
from pypdf import PdfReader

from services.pdf_processor import extract_text_and_metadata
from services.chunker import chunk_text
from services.embeddings import generate_embeddings
from services.mongo_store import mongo_store


def main(myblob: func.InputStream):
    logging.info(
        "Blob trigger fired | Name=%s | Size=%s bytes",
        myblob.name,
        myblob.length
    )

    try:
        # myblob.name format: pdfs/{category}/{filename}
        path_parts = myblob.name.split("/")

        if len(path_parts) >= 3:
            category = path_parts[-2].lower()
            filename = path_parts[-1]
        else:
            category = "uncategorized"
            filename = os.path.basename(myblob.name)

        logging.info("Parsed category=%s, filename=%s", category, filename)

        # 1. Read blob bytes
        pdf_bytes = myblob.read()
        if not pdf_bytes:
            logging.warning("Blob is empty. Skipping processing.")
            return

        # 2. Extract metadata (year/date)
        _, metadata = extract_text_and_metadata(pdf_bytes)

        # 3. Page-wise extraction & chunking
        MAX_TOTAL_CHUNKS = 1200
        all_chunks = []
        all_page_nums = []

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for i, page in enumerate(reader.pages):
                if len(all_chunks) >= MAX_TOTAL_CHUNKS:
                    logging.info("MAX_TOTAL_CHUNKS reached, stopping extraction.")
                    break

                page_text = page.extract_text()
                if not page_text or not page_text.strip():
                    continue

                page_chunks = chunk_text(page_text)
                if page_chunks:
                    remaining = MAX_TOTAL_CHUNKS - len(all_chunks)
                    actual_chunks = page_chunks[:remaining]
                    
                    all_chunks.extend(actual_chunks)
                    all_page_nums.extend([i + 1] * len(actual_chunks))

        except Exception as pdf_err:
            logging.exception("PDF page extraction failed")
            return

        if not all_chunks:
            logging.warning("No chunks generated from PDF.")
            return

        logging.info("Generated %d chunks across pages", len(all_chunks))

        # 4. Generate embeddings
        embeddings = generate_embeddings(all_chunks)

        if len(embeddings) != len(all_chunks):
            logging.error(
                "Embedding mismatch: chunks=%d embeddings=%d",
                len(all_chunks),
                len(embeddings)
            )
            return

        # 5. MongoDB operations (SAFE)
        collection = mongo_store.collection
        if collection is None:
            logging.error("MongoDB collection not available. Skipping insert.")
            return

        # Remove existing chunks for same PDF
        mongo_store.delete_pdf(category, filename)

        documents = []
        year = metadata.get("year", 2025)
        date_str = metadata.get("date", "")

        # Prepare metadata
        from datetime import datetime, timezone
        upload_time = datetime.now(timezone.utc)
        blob_path_str = f"{category}/{filename}"

        for idx, (txt, emb, p_num) in enumerate(
            zip(all_chunks, embeddings, all_page_nums)
        ):
            documents.append({
                "category": category,
                "pdf_name": filename,
                "blob_path": blob_path_str,
                "chunk_index": idx,
                "text": txt,
                "embedding": emb,
                "year": year,
                "date": date_str,
                "page_number": p_num,
                "uploaded_at": upload_time
            })

        if documents:
            collection.insert_many(documents)
            logging.info(
                "Stored PDF %s with %d chunks (page-level)",
                filename,
                len(documents)
            )

    except Exception as exc:
        logging.exception("Blob trigger failed")
        # Re-raise so Azure logs it clearly (but logic bugs are now fixed)
        raise
