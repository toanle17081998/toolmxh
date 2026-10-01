import json
import re
from typing import Type, TypeVar, Any
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

class RobustJSONParser:
    """Bộ giải mã JSON chống lỗi, tự động lọc markdown fences và cứu lỗi cú pháp phổ biến."""

    @staticmethod
    def extract_json_str(text: str) -> str:
        text = text.strip()
        
        # 1. Tìm block ```json ... ```
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
            
        # 2. Tìm khối giữa { và } ngoài cùng
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return text[first_brace:last_brace + 1].strip()
            
        return text

    @classmethod
    def parse_to_model(cls, text: str, model_cls: Type[T]) -> T:
        raw_json = cls.extract_json_str(text)
        try:
            return model_cls.model_validate_json(raw_json)
        except (ValidationError, json.JSONDecodeError):
            # Cố gắng sanitize: loại bỏ trailing commas trước } hoặc ]
            sanitized = re.sub(r",\s*([\]}])", r"\1", raw_json)
            try:
                data = json.loads(sanitized)
                return model_cls.model_validate(data)
            except Exception as e:
                raise ValueError(f"Không thể phân tích JSON thành {model_cls.__name__}: {e}\nNội dung gốc:\n{raw_json[:500]}...")
