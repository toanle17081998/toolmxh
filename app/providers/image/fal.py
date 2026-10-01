import os
import json
import urllib.request
from pathlib import Path
from typing import Optional
from app.providers.image.base import ImageGenerationProvider
from app.config import settings

class FalImageProvider(ImageGenerationProvider):
    """Mô hình tạo ảnh AI hàng đầu FLUX.1 qua Fal.ai (giống kiến trúc OpenCut)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "fal-ai/flux/schnell"):
        self.api_key = api_key or settings.FAL_KEY or os.getenv("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY không được tìm thấy để sử dụng Fal.ai FLUX.")
        self.model = model

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1,
        negative_prompt: str = ""
    ) -> str:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        url = f"https://queue.fal.run/{self.model}"
        payload = {
            "prompt": f"masterpiece, photorealistic cinematic film still, 8k resolution, vertical 9:16: {prompt}",
            "image_size": {
                "width": 768,
                "height": 1344
            },
            "num_images": 1,
            "enable_safety_checker": False
        }
        if seed != -1:
            payload["seed"] = seed

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
        )

        resp = urllib.request.urlopen(req, timeout=30)
        res_data = json.loads(resp.read().decode("utf-8"))
        
        # Fal.ai returns image URL in 'images'
        img_url = res_data["images"][0]["url"]
        img_req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        img_data = urllib.request.urlopen(img_req, timeout=30).read()

        with open(out_path, "wb") as f:
            f.write(img_data)

        return str(out_path)
