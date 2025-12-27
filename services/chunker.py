from typing import List


# Constants for ingestion stability
CHUNK_SIZE = 2200
CHUNK_OVERLAP = 200
MAX_CHUNKS = 1200

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    """
    if not text:
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        # Stop if we exceed max chunks
        if len(chunks) >= MAX_CHUNKS:
            break

        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap

    return chunks
