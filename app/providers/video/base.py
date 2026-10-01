from abc import ABC, abstractmethod

class GenerativeVideoProvider(ABC):
    """Lớp trừu tượng cho công cụ sinh video AI (T2V & I2V)."""

    @abstractmethod
    async def generate_image_to_video(
        self,
        image_path: str,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        """Sinh video từ ảnh tham chiếu (Image-to-Video) với thời lượng khớp timeline âm thanh."""
        pass

    @abstractmethod
    async def generate_text_to_video(
        self,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        """Sinh video trực tiếp từ văn bản (Text-to-Video)."""
        pass
