import logging
import azure.functions as func
import json
import os
from services.embeddings import generate_embeddings
from services.vector_search import search_vectors
from services.chat_completion import get_chat_completion
from services.mongo_store import mongo_store
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

class CustomJSONEncoder(json.JSONEncoder):
    """Safely serialize Mongo / ObjectId / numpy types if present."""
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Chat API triggered")

    try:
        # Parse Input
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}), 
                status_code=400, 
                mimetype="application/json"
            )

        question = req_body.get("question")
        category = req_body.get("category")
        pdf_name = req_body.get("pdf_name") # Optional filter
        
        if not question:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'question' field"}), 
                status_code=400, 
                mimetype="application/json"
            )

        # 1a. Smart Filter: Auto-detect filename in question if not explicit
        # Look for patterns like "foo.pdf" or "report_2024.pdf"
        if not pdf_name:
            import re
            # Regex: Word chars, hyphens, dots, finishing with .pdf (case insensitive)
            match = re.search(r'\b([\w\-.]+\.pdf)\b', question, re.IGNORECASE)
            if match:
                pdf_name = match.group(1)
                logging.info(f"Auto-detected filename filter from query: {pdf_name}")


        # 1. Generate Embedding (using services.embeddings)
        # generate_embeddings returns List[List[float]]
        embeddings = generate_embeddings([question])
        if not embeddings:
            return func.HttpResponse(
                json.dumps({"error": "Embedding generation failed"}), 
                status_code=500, 
                mimetype="application/json"
            )
        query_vec = embeddings[0]

        # 2. Vector Search (In-memory cosine similarity)
        # Handle "All" case for search_vectors (assuming it treats None or Global logic correctly)
        search_category = category if category and category != "All" else None

        top_chunks = search_vectors(
            query_embedding=query_vec,
            top_k=5, 
            category=search_category,
            pdf_name=pdf_name
        )

        # STRICT FILTERING: If category is specific, ensure we got results
        if search_category and not top_chunks:
            # Check if it was because of empty results
            return func.HttpResponse(
                json.dumps({
                    "answer": "No relevant documents found in the selected category.",
                    "sources": [],
                    "results": [],
                    "context_used": []
                }), 
                status_code=200, 
                mimetype="application/json"
            )

        # FIX: Rank at CHUNK LEVEL (Pick Top 1 Single Best Chunk)
        # This ensures page_number is exact and context is focused.
        if top_chunks:
            # Sort by score DESC just to be safe
            top_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
            # Pick ONLY the top 1
            top_chunks = top_chunks[:1]
            c = top_chunks[0]

            # ENSURE PAGE NUMBER: Fetch from Mongo if missing in vector projection
            # Primary check: vector_search now returns page_number, so this is just a safety net
            if "page_number" not in c or c["page_number"] is None or c["page_number"] == "N/A":
                try:
                    if mongo_store.collection is not None:
                        # Match by chunk_index for stability (instead of text)
                        query = {
                            "pdf_name": c.get("pdf_name"),
                            "category": c.get("category"),
                            "chunk_index": c.get("chunk_index")
                        }
                        # Fallback to text if chunk_index is missing (unlikely)
                        if c.get("chunk_index") is None:
                             query = {
                                "pdf_name": c.get("pdf_name"),
                                "category": c.get("category"),
                                "text": c.get("text")
                            }

                        doc = mongo_store.collection.find_one(query, {"page_number": 1})
                        if doc and doc.get("page_number"):
                            c["page_number"] = doc.get("page_number")
                except Exception as e:
                    logging.warning(f"Could not fetch page_number: {e}")

            logging.info(f"Selected Top Chunk: {c.get('pdf_name')} (Page {c.get('page_number')}, Score {c.get('score')})")

        # 3. Construct Prompt
        # Format chunks into a context string
        context_parts = []
        for chunk in top_chunks:
            source = chunk.get('pdf_name', 'Unknown')
            text = chunk.get('text', '').strip()
            context_parts.append(f"Source: {source}\nContent: {text}")
        
        context_text = "\n\n".join(context_parts)
        
        system_message = "You are a helpful AI assistant. Use the provided Context to answer the user's Question. If the answer is not found in the Context, state that you do not have enough information."
        user_message = f"Context:\n{context_text}\n\nQuestion: {question}"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

        # 4. Chat Completion (Azure or Groq via abstraction)
        answer = get_chat_completion(messages)

        # 5. Return Response
        
        # Helper to construct download URL
        # For POC, we assume standard Azure Blob URL format or Azurite
        # Ideally, we'd use generate_blob_sas if private, but we'll stick to public URL pattern for simplicity.
        def get_blob_url(cat, fname):
            try:
                conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
                if not conn_str:
                    return "#"
                
                blob_service_client = BlobServiceClient.from_connection_string(conn_str)
                blob_name = f"{cat}/{fname}"
                blob_client = blob_service_client.get_blob_client(container="pdfs", blob=blob_name)
                
                sas_token = generate_blob_sas(
                    account_name=blob_service_client.account_name,
                    container_name="pdfs",
                    blob_name=blob_name,
                    account_key=blob_service_client.credential.account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=datetime.utcnow() + timedelta(hours=1)
                )
                
                return f"{blob_client.url}?{sas_token}"
            except Exception as e:
                logging.error(f"Error generating SAS for {fname}: {e}")
                return "#"

        rich_results = []
        for c in top_chunks:
            cat = c.get('category', 'uncategorized')
            fname = c.get('pdf_name', 'unknown')
            rich_results.append({
                "pdf_name": fname,
                "category": cat,
                "year": c.get('year', 'N/A'),
                "page": c.get('page_number', 'N/A'),
                "download_url": get_blob_url(cat, fname)
            })

        response_payload = {
            "answer": answer,
            "sources": [c.get('pdf_name') for c in top_chunks], # Keep for backward compat
            "results": rich_results, # New rich metadata
            "context_used": top_chunks 
        }

        return func.HttpResponse(
            json.dumps(response_payload, cls=CustomJSONEncoder),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Chat API Error")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
