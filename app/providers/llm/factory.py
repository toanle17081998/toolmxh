import os
from typing import Optional
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini import GeminiLLMProvider
from app.providers.llm.openai import OpenAILLMProvider
from app.providers.llm.offline import OfflineBrainProvider
from app.config import settings

def get_llm_provider(preference: Optional[str] = None) -> LLMProvider:
    """Tự động lựa chọn provider phù hợp theo API key hiện có."""
    pref = (preference or settings.DEFAULT_LLM_PROVIDER).lower()
    
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY

    if pref == "gemini" and gemini_key:
        return GeminiLLMProvider(api_key=gemini_key)
    elif pref == "openai" and openai_key:
        return OpenAILLMProvider(api_key=openai_key)
    elif gemini_key:
        return GeminiLLMProvider(api_key=gemini_key)
    elif openai_key:
        return OpenAILLMProvider(api_key=openai_key)
    else:
        # Tự động dùng Offline Content Brain nếu chưa cấu hình API key
        return OfflineBrainProvider()
