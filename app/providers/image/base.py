from abc import ABC, abstractmethod

class ImageGenerationProvider(ABC):
    """Lớp trừu tượng cho công cụ sinh ảnh AI tham chiếu (Visual Anchor)."""

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1,
        negative_prompt: str = ""
    ) -> str:
        """Sinh file ảnh tham chiếu (PNG) và trả về đường dẫn file kết quả."""
        pass
