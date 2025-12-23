import logging
import azure.functions as func
import json
import os
import re
from datetime import datetime, timedelta

# Import services - internal logic is now lazy
from services.embeddings import generate_embeddings
from services.vector_search import search_vectors
from services.chat_completion import get_chat_completion
from services.mongo_store import mongo_store

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

class CustomJSONEncoder(json.JSONEncoder):
    """Safely serialize Mongo / ObjectId / numpy types if present."""
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

def get_blob_url(cat, fname):
    """Generate a SAS URL for the blob."""
    try:
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
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
        if not pdf_name:
            # Regex: Word chars, hyphens, dots, finishing with .pdf (case insensitive)
            match = re.search(r'\b([\w\-.]+\.pdf)\b', question, re.IGNORECASE)
            if match:
                pdf_name = match.group(1)
                logging.info(f"Auto-detected filename filter from query: {pdf_name}")


        # 1. Generate Embedding
        # If Mongo is down or embedding fails, we should handle gracefully
        # generate_embeddings now returns [] on failure
        embeddings = generate_embeddings([question])
        
        if not embeddings:
            logging.error("Embedding generation returned empty. Possibly OpenAI down.")
            # We can't search without embeddings.
            # Return a polite error or fallback?
            # User requirement: "Chat ... must continue to work with empty context."
            # If embedding fails, we have NO context.
            return func.HttpResponse(
                json.dumps({
                    "answer": "I'm sorry, I'm currently unable to access the knowledge base (Embedding Error).",
                    "sources": [],
                    "results": [],
                    "context_used": []
                }), 
                status_code=200, # Return 200 so UI doesn't break
                mimetype="application/json"
            )

        query_vec = embeddings[0]

        # 2. Vector Search
        search_category = category if category and category.lower() != "all" else None
        
        # search_vectors handles lazy Mongo connection. Returns [] if Mongo down.
        top_chunks = search_vectors(
            query_embedding=query_vec,
            top_k=5, 
            category=search_category,
            pdf_name=pdf_name
        )

        # If no documents found (either empty DB, Mongo down, or no match)
        if not top_chunks:
            logging.info("No relevant chunks found.")
            return func.HttpResponse(
                json.dumps({
                    "answer": "No relevant documents found.",
                    "sources": [],
                    "results": [],
                    "context_used": []
                }), 
                status_code=200, 
                mimetype="application/json"
            )

        # FIX: Rank at CHUNK LEVEL (Pick Top 1 Single Best Chunk)
        # This ensures page_number is exact and context is focused.
        # Sort by score DESC
        top_chunks.sort(key=lambda x: x.get('score', 0), reverse=True)
        # Pick ONLY the top 1
        top_chunks = top_chunks[:1]
        c = top_chunks[0]

        # ENSURE PAGE NUMBER
        # lazy Mongo access here too
        if "page_number" not in c or c["page_number"] is None or c["page_number"] == "N/A":
            try:
                # Accessing mongo_store.collection invokes lazy connection
                col = mongo_store.collection
                if col is not None:
                    query = {
                        "pdf_name": c.get("pdf_name"),
                        "category": c.get("category"),
                        "chunk_index": c.get("chunk_index")
                    }
                    if c.get("chunk_index") is None:
                         query = {
                            "pdf_name": c.get("pdf_name"),
                            "category": c.get("category"),
                            "text": c.get("text")
                        }
                    doc = col.find_one(query, {"page_number": 1})
                    if doc and doc.get("page_number"):
                        c["page_number"] = doc.get("page_number")
            except Exception as e:
                logging.warning(f"Could not fetch page_number: {e}")

        logging.info(f"Selected Top Chunk: {c.get('pdf_name')} (Page {c.get('page_number')}, Score {c.get('score')})")

        # 3. Construct Prompt
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

        # 4. Chat Completion
        try:
            answer = get_chat_completion(messages)
        except Exception as e:
             logging.error(f"Chat completion failed: {e}")
             answer = "I'm sorry, I encountered an error generating the response."

        # 5. Return Response
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
            "sources": [c.get('pdf_name') for c in top_chunks],
            "results": rich_results,
            "context_used": top_chunks 
        }

        return func.HttpResponse(
            json.dumps(response_payload, cls=CustomJSONEncoder),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Chat API Critical Error")
        # Ensure we return valid JSON even on 500
        return func.HttpResponse(
            json.dumps({"error": "Internal server error", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
