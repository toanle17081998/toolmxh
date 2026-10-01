from abc import ABC, abstractmethod

class ImageGenerationProvider(ABC):
    """Lớp trừu tượng cho công cụ sinh ảnh AI tham chiếu (Visual Anchor)."""

    supports_health_characters = False
    supports_reference_images = False

    async def generate_health_image(self, prompt, output_path, width=1080, height=1920,
                                    seed=-1, reference_images=None):
        raise RuntimeError(f"{type(self).__name__} does not support health character generation")

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
