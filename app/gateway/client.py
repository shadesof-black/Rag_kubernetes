import logfire
from portkey_ai import Portkey, createHeaders, PORTKEY_GATEWAY_URL
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.config import settings


# Production gateway client:
# Defaults to ChatGroq using active model (openai/gpt-oss-20b)
portkey_client = None
if settings.PORTKEY_API_KEY:
    try:
        portkey_client = Portkey(
            api_key=settings.PORTKEY_API_KEY,
            config=settings.PORTKEY_CONFIG,
        )
    except Exception as e:
        logfire.warning(f"Portkey initialization warning: {e}")
        portkey_client = None


def get_langchain_llm(feature: str = "rag") -> ChatGroq:
    api_key = settings.GROQ_API_KEY or settings.GROQ_FALLBACK_API_KEY
    return ChatGroq(
        api_key=api_key,
        model=settings.GROQ_MODEL,
        temperature=0
    )

def extract_cache_status(response) -> str:
    """
    Pull x-portkey-cache-status from response headers defensively.
    """
    for attr in ("_raw_response", "_response", "_http_response"):
        raw = getattr(response, attr, None)
        if raw is not None:
            headers = getattr(raw, "headers", {})
            if hasattr(headers, "get"):
                status = headers.get("x-portkey-cache-status", "")
                if status:
                    return status.upper()
    return "MISS"