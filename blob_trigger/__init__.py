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
        # myblob.name format:
        # pdfs/{category}/{filename}
        path_parts = myblob.name.split("/")

        if len(path_parts) >= 3:
            category = path_parts[-2]
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

        # 2. Get Metadata (Year, Date) - Reusing existing service logic
        # We treat 'text' here as temporary just for metadata extraction
        _, metadata = extract_text_and_metadata(pdf_bytes)

        # 3. Page-by-Page Extraction & Chunking
        all_chunks = []
        all_page_nums = []

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if not page_text or not page_text.strip():
                    continue
                
                # Chunk this page's text
                page_sub_chunks = chunk_text(page_text)
                if page_sub_chunks:
                    all_chunks.extend(page_sub_chunks)
                    # 1-based page number
                    all_page_nums.extend([i + 1] * len(page_sub_chunks))
        
        except Exception as pdf_err:
            logging.error(f"Page extraction error: {pdf_err}")
            return

        if not all_chunks:
            logging.warning("No chunks generated from PDF.")
            return

        logging.info("Generated %d chunks across pages", len(all_chunks))

        # 4. Generate embeddings
        embeddings = generate_embeddings(all_chunks)

        if len(embeddings) != len(all_chunks):
            raise ValueError(
                f"Embedding count mismatch: chunks={len(all_chunks)} embeddings={len(embeddings)}"
            )

        # 5. Store in MongoDB (Custom insert to include page_num)
        if mongo_store.collection is None:
             logging.error("MongoDB collection not available.")
             return

        # Clean old records for this PDF
        mongo_store.delete_pdf(category, filename)

        # Build documents with page_num
        documents = []
        year = metadata.get("year", 2025)
        date_str = metadata.get("date", "")

        for idx, (txt, emb, p_num) in enumerate(zip(all_chunks, embeddings, all_page_nums)):
            documents.append({
                "category": category,
                "pdf_name": filename,
                "chunk_index": idx,
                "text": txt,
                "embedding": emb,
                "year": year,
                "date": date_str,
                "page_number": p_num
            })

        if documents:
            mongo_store.collection.insert_many(documents)
            logging.info("Successfully processed and stored PDF: %s with %d chunks (Page Level)", filename, len(documents))

    except Exception as exc:
        logging.exception("Blob trigger failed: %s", exc)
        raise
