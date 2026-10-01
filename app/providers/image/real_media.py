import os
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List
from PIL import Image

from app.providers.image.base import ImageGenerationProvider
from app.config import settings

class RealVisualMediaEngine(ImageGenerationProvider):
    """
    Real Visual Media Engine - Đảm bảo 100% ảnh thật / hoạt hình anime thật.
    Tuyệt đối không dùng mô phỏng đồ họa hình học/toán học (procedural simulation).
    Tìm kiếm và tải ảnh quang học thật từ Wikimedia Commons (NASA, Nature, National Geographic)
    hoặc Anime Digital Art chân thực, crop chuẩn 1080x1920.
    """

    def __init__(self):
        # Thiết lập proxy nội bộ để kết nối Internet không bao giờ bị chặn
        self.proxy_url = "http://172.16.120.13:3128"
        self.opener = self._build_opener()

    def _build_opener(self):
        try:
            proxy_handler = urllib.request.ProxyHandler({
                "http": self.proxy_url,
                "https": self.proxy_url
            })
            return urllib.request.build_opener(proxy_handler)
        except Exception:
            return urllib.request.build_opener()

    def _extract_keywords(self, prompt: str) -> List[str]:
        p = prompt.lower()
        keywords = []

        is_anime = any(w in p for w in ["anime", "cartoon", "hoạt hình", "illustration", "art"])

        if any(w in p for w in ["moon", "mặt trăng", "lunar"]):
            if is_anime:
                keywords.extend(["Anime moon night sky", "Makoto Shinkai night sky", "Full moon illustration"])
            else:
                keywords.extend(["Full Moon NASA", "Moon surface Apollo", "Moon from space NASA"])

        elif any(w in p for w in ["earth", "trái đất", "orbit", "quỹ đạo"]):
            if is_anime:
                keywords.extend(["Anime earth space", "Anime space background"])
            else:
                keywords.extend(["Earth from space Apollo", "Blue Marble NASA", "Earth orbit ISS"])

        elif any(w in p for w in ["tsunami", "sóng thần", "ocean", "đại dương", "biển", "tide"]):
            if is_anime:
                keywords.extend(["Anime ocean waves", "Anime sea storm"])
            else:
                keywords.extend(["Tsunami wave ocean", "Huge ocean wave storm", "Deep sea underwater"])

        elif any(w in p for w in ["disaster", "catastrophe", "bão", "sấm sét", "storm", "hỗn loạn"]):
            if is_anime:
                keywords.extend(["Anime lightning storm sky", "Anime explosion disaster"])
            else:
                keywords.extend(["Severe storm lightning night", "Volcano eruption lava", "Hurricane satellite NASA"])

        elif any(w in p for w in ["people", "crowd", "human", "protagonist", "con người", "nhìn lên"]):
            if is_anime:
                keywords.extend(["Anime person looking at sky", "Anime crowd night", "Anime character shocked"])
            else:
                keywords.extend(["Crowd looking up sky night", "People watching stars night", "Stargazing night"])

        else:
            # Rút trích các danh từ chính từ prompt
            clean = re.sub(r"[^a-zA-Z\s]", " ", prompt)
            words = [w for w in clean.split() if len(w) > 3 and w.lower() not in ["shot", "cinematic", "photorealistic", "detailed", "lighting", "ultra", "hyper"]]
            if words:
                keywords.append(" ".join(words[:3]))
            keywords.append("Space galaxy NASA" if not is_anime else "Anime starry sky night")

        return keywords

    def search_wikimedia_image(self, query: str) -> Optional[str]:
        """Tìm URL ảnh độ phân giải cao trên Wikimedia Commons."""
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6&gsrsearch={encoded}&gsrlimit=5&prop=imageinfo&iiprop=url|mime|size&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "ToolMXH-VideoFactory/2.0 (contact: toanlv31@viettel.com.vn)"})
            with self.opener.open(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    infos = pdata.get("imageinfo", [])
                    if infos:
                        img_url = infos[0].get("url")
                        mime = infos[0].get("mime", "")
                        width = infos[0].get("width", 0)
                        height = infos[0].get("height", 0)
                        # Ưu tiên ảnh chất lượng cao trên 800px
                        if mime in ["image/jpeg", "image/png", "image/webp"] and (width >= 800 or height >= 800):
                            return img_url
        except Exception:
            pass
        return None

    def download_and_crop(self, image_url: str, output_path: str, target_w: int = 1080, target_h: int = 1920) -> bool:
        """Tải ảnh thật và crop chính giữa theo tỉ lệ chuẩn 1080x1920 sắc nét."""
        try:
            req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            temp_file = Path(output_path).with_suffix(".download.tmp")
            with self.opener.open(req, timeout=20) as resp:
                with open(temp_file, "wb") as f:
                    f.write(resp.read())

            # Mở và crop chuẩn tỉ lệ dọc TikTok/Reels
            with Image.open(str(temp_file)) as img:
                img = img.convert("RGB")
                orig_w, orig_h = img.size
                target_ratio = target_w / float(target_h)
                orig_ratio = orig_w / float(orig_h)

                if orig_ratio > target_ratio:
                    # Ảnh rộng hơn: crop 2 bên, giữ chiều cao
                    new_w = int(orig_h * target_ratio)
                    offset_x = (orig_w - new_w) // 2
                    box = (offset_x, 0, offset_x + new_w, orig_h)
                else:
                    # Ảnh cao hơn: crop trên dưới, giữ chiều rộng
                    new_h = int(orig_w / target_ratio)
                    offset_y = (orig_h - new_h) // 2
                    box = (0, offset_y, orig_w, offset_y + new_h)

                cropped = img.crop(box)
                final_img = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
                final_img.save(output_path, format="PNG", quality=95)

            if temp_file.exists():
                temp_file.unlink()
            return True
        except Exception:
            return False

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None
    ) -> str:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        # 1. Trích xuất danh sách từ khóa tìm kiếm theo ngữ nghĩa
        queries = self._extract_keywords(prompt)

        # 2. Tìm kiếm trên các kho ảnh thực tế
        for q in queries:
            img_url = self.search_wikimedia_image(q)
            if img_url:
                success = self.download_and_crop(img_url, str(out_p), target_w=width, target_h=height)
                if success and out_p.exists() and out_p.stat().st_size > 10000:
                    return str(out_p)

        # 3. Fallback: Nếu không tìm thấy từ khóa cụ thể, dùng ảnh thiên văn / vũ trụ NASA thật
        fallback_query = "Full Moon NASA" if "moon" in prompt.lower() else "Earth from space NASA"
        fallback_url = self.search_wikimedia_image(fallback_query)
        if fallback_url:
            self.download_and_crop(fallback_url, str(out_p), target_w=width, target_h=height)
            if out_p.exists():
                return str(out_p)

        # 4. Nếu máy tính offline hoàn toàn, fallback an toàn cuối cùng
        from app.providers.image.opencut_realistic import OpenCutRealisticImageProvider
        return await OpenCutRealisticImageProvider().generate_image(prompt, output_path, width, height, seed)
