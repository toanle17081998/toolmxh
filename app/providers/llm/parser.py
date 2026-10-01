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
        # Loại bỏ trailing commas trước } hoặc ]
        sanitized = re.sub(r",\s*([\]}])", r"\1", raw_json)
        try:
            data = json.loads(sanitized)
        except Exception:
            try:
                data = json.loads(raw_json)
            except Exception as je:
                raise ValueError(f"Không thể giải mã JSON: {je}\nNội dung gốc:\n{raw_json[:500]}...")

        # Tự động chuẩn hóa dữ liệu cho Storyboard
        if isinstance(data, dict):
            if "characters" in data and isinstance(data["characters"], list):
                for idx, c in enumerate(data["characters"]):
                    if isinstance(c, dict):
                        if "character_id" not in c or not c["character_id"]:
                            c["character_id"] = f"char_{idx+1:02d}"
                        if "appearance" not in c and "description" in c:
                            c["appearance"] = c["description"]
                        elif "appearance" not in c:
                            c["appearance"] = "cinematic character"
                        if "name" not in c:
                            c["name"] = f"Character {idx+1}"
            if "scenes" in data and isinstance(data["scenes"], list):
                for s_idx, sc in enumerate(data["scenes"]):
                    if isinstance(sc, dict):
                        if "scene_id" not in sc:
                            sc["scene_id"] = s_idx + 1
                        if "image_prompt" not in sc and "visual" in sc:
                            sc["image_prompt"] = sc["visual"]
                        if "video_prompt" not in sc:
                            sc["video_prompt"] = "Cinematic camera slow push in"

        try:
            return model_cls.model_validate(data)
        except Exception as e:
            raise ValueError(f"Không thể phân tích JSON thành {model_cls.__name__}: {e}\nNội dung gốc:\n{raw_json[:500]}...")
