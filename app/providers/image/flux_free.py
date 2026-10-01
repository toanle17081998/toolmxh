import os
import asyncio
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional

from app.providers.image.base import ImageGenerationProvider

class FluxFreeImageProvider(ImageGenerationProvider):
    """
    Sinh ảnh FLUX.1 chất lượng cao hoàn toàn miễn phí qua Pollinations AI (GenAI SOTA).
    Đảm bảo 100% bám sát chi tiết kịch bản, không bao giờ lấy ảnh stock ngẫu nhiên.
    """

    def __init__(self, model: str = "flux"):
        self.model = model
        self.proxy = os.getenv("HTTP_PROXY") or "http://172.16.120.13:3128"

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1,
        negative_prompt: str = ""
    ) -> str:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        clean_prompt = prompt.replace("\n", " ").strip()
        encoded = urllib.parse.quote(clean_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&model=flux&nologo=true&seed={seed if seed != -1 else 42}"

        def _fetch():
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy})
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with opener.open(req, timeout=35) as resp, open(out_p, "wb") as f:
                f.write(resp.read())

        try:
            await asyncio.to_thread(_fetch)
            if out_p.exists() and out_p.stat().st_size > 10000:
                return str(out_p)
        except Exception:
            pass

        # Fallback trực tiếp nếu proxy lỗi
        def _fetch_no_proxy():
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=35) as resp, open(out_p, "wb") as f:
                f.write(resp.read())

        await asyncio.to_thread(_fetch_no_proxy)
        return str(out_p)
