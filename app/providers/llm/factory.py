import os
from typing import Optional
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini import GeminiLLMProvider
from app.providers.llm.openai import OpenAILLMProvider
from app.providers.llm.offline import OfflineBrainProvider
from app.config import settings

def get_llm_provider(preference: Optional[str] = None, model: Optional[str] = None) -> LLMProvider:
    """Tự động lựa chọn LLM Provider phù hợp theo model yêu cầu và API key hiện có."""
    m = (model or "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY

    # 1. Nếu người dùng chọn Offline Brain
    if m.lower() in ["offline", "offline-brain", "local"]:
        return OfflineBrainProvider()

    # 2. Nếu người dùng chọn mô hình GPT (gpt-5.6, gpt-5.5, gpt-4o...)
    if m.lower().startswith("gpt") or preference == "openai":
        if openai_key:
            return OpenAILLMProvider(api_key=openai_key, model=m or "gpt-4o")
        elif gemini_key:
            return GeminiLLMProvider(api_key=gemini_key, model="gemini-3.8-flash")
        else:
            return OfflineBrainProvider()

    # 3. Nếu người dùng chọn mô hình Gemini (gemini-3.8-flash, gemini-3.5-flash-lite, gemini-3.1-pro-preview...)
    if m.lower().startswith("gemini") or preference == "gemini":
        if gemini_key:
            return GeminiLLMProvider(api_key=gemini_key, model=m or "gemini-3.8-flash")
        elif openai_key:
            return OpenAILLMProvider(api_key=openai_key, model="gpt-4o")
        else:
            return OfflineBrainProvider()

    # 4. Tự động lựa chọn theo key
    if gemini_key:
        return GeminiLLMProvider(api_key=gemini_key, model="gemini-3.8-flash")
    elif openai_key:
        return OpenAILLMProvider(api_key=openai_key, model="gpt-4o")
    else:
        return OfflineBrainProvider()
