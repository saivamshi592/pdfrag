import logging
import os
from typing import List, Dict, Any
from openai import AzureOpenAI
from config.settings import settings

# Global lazy client
_chat_client = None

def get_chat_client():
    global _chat_client
    if _chat_client:
        return _chat_client

    if not (
        settings.AZURE_OPENAI_API_KEY
        and settings.AZURE_OPENAI_ENDPOINT
        and settings.AZURE_OPENAI_CHAT_DEPLOYMENT
    ):
        raise RuntimeError("Azure OpenAI Chat configuration missing")

    _chat_client = AzureOpenAI(
        api_key=settings.AZURE_OPENAI_API_KEY,
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )
    return _chat_client


def get_chat_completion(messages: List[Dict[str, str]]) -> str:
    """
    Executes a chat completion validation/request against Azure OpenAI.
    Lazy initialization validation included.
    """
    client = get_chat_client()
    
    try:
        completion = client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
            max_tokens=1500
        )
        return completion.choices[0].message.content
    except Exception as e:
        logging.exception("Chat completion failed")
        raise e

# Legacy function support (if needed by other modules, redirected to new logic)
def generate_answer(question: str, chunks: List[Dict[str, Any]]) -> str:
    """
    Legacy wrapper if needed. Reconstructs messages and calls get_chat_completion.
    """
    context = "\n\n".join([f"- {c.get('text', '')}" for c in chunks])
    
    system_msg = "You are a helpful AI assistant. Answer using the context provided."
    user_msg = f"Context:\n{context}\n\nQuestion:\n{question}"
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    return get_chat_completion(messages)
