import json
import logging
import azure.functions as func

from services.embeddings import get_embedding
from services.vector_search import search_vectors
from services.chat_completion import get_chat_completion


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Chat API triggered")

    try:
        body = req.get_json()
        question = body.get("question", "").strip()
        category_raw = body.get("category")
        category = (category_raw if category_raw else "all").lower()

        if not question:
            return func.HttpResponse(
                json.dumps({"error": "Question is required"}),
                status_code=400,
                mimetype="application/json",
            )

        # 1️⃣ Embed the query
        query_embedding = get_embedding(question)

        # 2️⃣ Vector search WITH category enforcement
        chunks = search_vectors(
            query_embedding=query_embedding,
            category=category,
            top_k=3,
        )

        #  NO chunks → NO answer
        if not chunks:
            return func.HttpResponse(
                json.dumps({
                    "answer": "The answer is not available in the uploaded documents.",
                    "sources": [],
                    "results": []
                }),
                mimetype="application/json",
            )

        # 3️⃣ Build STRICT RAG prompt
        context_text = "\n\n".join(
            f"[File: {c.get('pdf_name', 'unknown')} | Page: {c.get('page_number', 'N/A')}] {c.get('text', '')}"
            for c in chunks
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a STRICT document-based assistant.\n"
                    "Answer ONLY using the provided context.\n"
                    "If the answer is not in the context, say:\n"
                    "'The answer is not available in the uploaded documents.'\n"
                    "DO NOT use general knowledge."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion:\n{question}",
            },
        ]

        answer = get_chat_completion(messages)

        # 4️⃣ Build sources (Must be strings for UI compatibility)
        sources = [c.get("pdf_name", "unknown") for c in chunks]

        # Rich metadata (optional, ensuring no data loss)
        results = [
            {
                "pdf_name": c.get("pdf_name", "unknown"),
                "category": c.get("category", "unknown"),
                "page": c.get("page_number", "N/A"),
                "year": c.get("year", "N/A"),
                "download_url": c.get("download_url", "#") 
            }
            for c in chunks
        ]

        return func.HttpResponse(
            json.dumps({
                "answer": answer,
                "sources": sources,
                "results": results,
            }),
            mimetype="application/json",
        )

    except Exception as e:
        logging.exception("Chat API failed")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json",
        )
