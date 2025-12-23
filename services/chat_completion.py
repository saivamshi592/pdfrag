import logging
import os
from config.settings import settings

# Attempt to import Groq; handle if missing to verify "strictly required" cleanliness, 
# although we added it to requirements.
try:
    from groq import Groq
except ImportError:
    Groq = None

from openai import AzureOpenAI

def get_chat_completion(messages: list) -> str:
    """
    Abstracts the chat completion provider (Azure OpenAI vs Groq).
    """
    provider = settings.LLM_PROVIDER

    if provider == "groq":
        if Groq is None:
            raise RuntimeError("LLM_PROVIDER is set to 'groq', but 'groq' python package is not installed.")
        
        if not settings.GROQ_API_KEY:
            raise ValueError("LLM_PROVIDER is 'groq' but GROQ_API_KEY is not set.")

        logging.info(f"Calling Groq Chat Completion with model: {settings.GROQ_MODEL}")
        
        client = Groq(api_key=settings.GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            messages=messages,
            model=settings.GROQ_MODEL,
            temperature=0.7,
            max_tokens=800
        )
        return completion.choices[0].message.content

    else:
        # Default / Fallback to Azure OpenAI
        if not settings.AZURE_OPENAI_API_KEY or not settings.AZURE_OPENAI_ENDPOINT:
             raise ValueError("Azure OpenAI configuration missing or incomplete.")
            
        logging.info(f"Calling Azure OpenAI Chat Completion with model: {settings.AZURE_OPENAI_CHAT_DEPLOYMENT}")
        
        client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_version=settings.AZURE_OPENAI_API_VERSION
        )

        completion = client.chat.completions.create(
            model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        return completion.choices[0].message.content
