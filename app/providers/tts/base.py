from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.models.timeline import WordTimestamp

class TTSProvider(ABC):
    """Lớp trừu tượng cho công cụ tổng hợp giọng đọc tiếng Việt."""

    @abstractmethod
    async def synthesize_to_file(
        self,
        text: str,
        output_wav_path: str,
        voice: str = "vi-VN-HoaiMyNeural",
        speed: float = 1.0
    ) -> float:
        """Sinh file WAV tiếng Việt và trả về thời lượng thực tế tính bằng giây."""
        pass
