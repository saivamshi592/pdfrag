import io
import logging
import re
from datetime import datetime
from pypdf import PdfReader

def extract_text_and_metadata(pdf_bytes: bytes) -> tuple[str, dict]:
    """
    Extract text and metadata (year, date) from PDF bytes.
    Returns: (text, {"year": int, "date": str})
    """
    if not pdf_bytes:
        return "", {"year": 2025, "date": ""}

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        extracted_text = []

        for page_index, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text:
                    extracted_text.append(text)
            except Exception as page_err:
                logging.warning(f"Failed to extract page {page_index}: {page_err}")

        final_text = "\n".join(extracted_text)
        
        # Metadata Extraction
        metadata = {"year": 2025, "date": ""}
        
        # 1. Try PDF Metadata
        if reader.metadata:
            creation_date = reader.metadata.get('/CreationDate')
            if creation_date:
                # Format: D:YYYYMMDDHHmmSS...
                # Simple parse: remove D: and take first 4 chars
                try:
                    clean_date = creation_date.replace("D:", "")
                    year_str = clean_date[:4]
                    if year_str.isdigit() and 2000 <= int(year_str) <= 2030:
                        metadata["year"] = int(year_str)
                        metadata["date"] = clean_date[:8] # YYYYMMDD
                except Exception:
                    pass

        # 2. Key fallback to text regex if year is still default
        if metadata["year"] == 2025:
            # Look for years 2000-2030 in text
            years = re.findall(r'\b(20[0-3]\d)\b', final_text)
            if years:
                # Pick the most recent year found
                metadata["year"] = int(max(years))

        logging.info("Extracted %d chars. Metadata: %s", len(final_text), metadata)
        return final_text, metadata

    except Exception as e:
        logging.error(f"PDF extraction failed: {e}")
        raise

# Legacy wrapper if needed, but better to update caller
def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text, _ = extract_text_and_metadata(pdf_bytes)
    return text
