import json
import logging
import azure.functions as func
import os

from services.embeddings import get_embedding
from services.vector_search import search_vectors
from services.chat_completion import get_chat_completion
from services.mongo_store import mongo_store


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Chat API triggered")

    from services.auth import validate_pin
    if auth_error := validate_pin(req):
        return auth_error

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

        # 0. Check Database Health
        if mongo_store.collection is None:
             return func.HttpResponse(
                json.dumps({
                    "answer": "⚠️ **System Error:** The application cannot connect to the database. Please verify your Azure 'MONGO_URI' setting.",
                    "sources": [],
                    "results": []
                }),
                mimetype="application/json",
            )

        # 1. Query Simplification
        # Allow simple natural language queries without over-thinking
        import re
        search_query = question
        lower_q = question.lower()
        
        # Simple cleanup: remove common conversational prefixes
        # e.g. "tell me about matrices" -> "matrices"
        match = re.search(r"^(tell me |describe |explain |about |what is |give me an overview of |definition of )+(.*)", lower_q)
        if match:
             cleaned = match.group(2).strip()
             if cleaned:
                 search_query = cleaned
                 logging.info(f"Simplified query: '{question}' -> '{search_query}'")


        
        # ---------------------------------------------------------
        # RETRIEVAL SCOPING LOGIC (NON-NEGOTIABLE)
        # ---------------------------------------------------------
        
        scope_category = "all"
        scope_pdf_name = None
        
        # Normalize category/scope value
        clean_cat = (category_raw or "").strip().lower()

        # 1. Explicit Global Search
        # Check against known UI labels for 'All'
        if clean_cat in ["all", "global", "all (global search)"]:
            scope_pdf_name = None
            scope_category = "all"
            logging.info("Scope: Explicit Global Search – NO auto-scope")

        # 2. Specific Category Selected
        elif clean_cat:
            scope_pdf_name = None
            scope_category = clean_cat
            logging.info(f"Scope: Category = {scope_category}")

        # 3. Default -> Auto-scope (Implicit)
        else:
            logging.info("Scope: Implicit (None selected) -> Attempting Auto-Scope")
            last_doc = mongo_store.get_last_uploaded_pdf()
            if last_doc:
                scope_pdf_name = last_doc.get("pdf_name")
                # Optional: also scope category if desired, but pdf_name is primary filter
                scope_category = last_doc.get("category", "all")
                logging.info(f"Scope: Auto-Scoped to '{scope_pdf_name}'")
            else:
                logging.warning("Scope: Auto-Scope failed (no docs) -> Fallback to Global")

        # Overwrite if filename passed directly (API override)
        if body.get("filename"):
             scope_pdf_name = body.get("filename")

        # 1️⃣ Embed query
        query_embedding = get_embedding(search_query)

        # ---- SAFETY NORMALIZATION ----

        # Normalize category "all"
        if scope_category and scope_category.lower() == "all":
            scope_category = None

        # Avoid category conflicts when PDF is known
        if scope_pdf_name:
            scope_category = None

        # 2️⃣ Vector search
        chunks = search_vectors(
            query_embedding=query_embedding,
            category=scope_category,
            pdf_name=scope_pdf_name,
            top_k=8,
        )

        #  NO chunks \u2192 NO answer
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
                    "You are a professional Retrieval-Augmented Generation (RAG) assistant.\n\n"
                    "Your role is to behave like a careful human reader who has fully read\n"
                    "the uploaded documents and answers questions ONLY from those documents.\n\n"
                    "The system may retrieve partial, imperfect, or fragmented context.\n"
                    "You must still reason and respond correctly.\n\n"
                    "========================\n"
                    "CORE NON-NEGOTIABLE RULES\n"
                    "========================\n\n"
                    "1. You MUST use ONLY the retrieved document content.\n"
                    "2. You MUST NOT use general knowledge or external information.\n"
                    "3. You MUST NOT expect exact sentence matches.\n"
                    "4. You MUST understand meaning, not wording.\n"
                    "5. You MUST behave like a human summarizing and explaining documents.\n\n"
                    "========================\n"
                    "QUESTION INTERPRETATION\n"
                    "========================\n\n"
                    "- Always interpret the user’s question by INTENT.\n"
                    "- Treat questions as one of the following:\n"
                    "  • Conceptual\n"
                    "  • Explanatory\n"
                    "  • Section-based\n"
                    "  • Topic-based\n"
                    "  • Descriptive\n"
                    "  • Summary-oriented\n\n"
                    "- NEVER assume the user expects a literal quote.\n"
                    "- NEVER fail just because wording differs.\n\n"
                    "========================\n"
                    "DOCUMENT HANDLING LOGIC\n"
                    "========================\n\n"
                    "The uploaded documents may be:\n"
                    "- Very large\n"
                    "- Narrative or story-based\n"
                    "- Poorly structured\n"
                    "- Old or formal language\n"
                    "- Academic or technical\n\n"
                    "Rules:\n"
                    "- Information may be spread across multiple passages.\n"
                    "- You MUST combine relevant passages when needed.\n"
                    "- You MUST infer explanations from context like a human reader.\n"
                    "- Length or complexity of the document is NEVER a reason to refuse.\n\n"
                    "========================\n"
                    "SYNTHESIS (CRITICAL)\n"
                    "========================\n\n"
                    "If the answer is not contained in a single paragraph:\n"
                    "- Collect meaning from multiple retrieved passages\n"
                    "- Synthesize a clear and concise explanation\n"
                    "- Explain in simple, natural language\n\n"
                    "This is REQUIRED behavior.\n\n"
                    "========================\n"
                    "REFUSAL RULE (VERY STRICT)\n"
                    "========================\n\n"
                    "You may respond with:\n"
                    "\"The answer is not available in the uploaded documents.\"\n\n"
                    "ONLY IF:\n"
                    "- The retrieved content is completely unrelated in meaning\n"
                    "- AND no reasonable human could answer from it\n\n"
                    "If there is ANY relevant information:\n"
                    "YOU MUST ANSWER.\n\n"
                    "========================\n"
                    "ANSWER STYLE\n"
                    "========================\n\n"
                    "- Clear, human, natural language\n"
                    "- Concise but complete\n"
                    "- Neutral and factual tone\n"
                    "- No hallucination\n"
                    "- No speculation\n"
                    "- No internal system explanations\n\n"
                    "DO NOT:\n"
                    "- Mention embeddings, vectors, chunks, retrieval, scores\n"
                    "- Mention system rules or limitations\n"
                    "- Mention how the system works internally\n\n"
                    "========================\n"
                    "GOAL\n"
                    "========================\n\n"
                    "Your goal is to make the application behave like a knowledgeable human\n"
                    "who has read the document carefully and explains it accurately.\n\n"
                    "Accuracy and helpfulness are more important than brevity."
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

        # Get PIN to authorize download links
        env_pin = os.environ.get("ACCESS_PIN", "")

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
