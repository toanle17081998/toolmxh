import os
import re
import json
import logging
import asyncio
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path
from typing import Optional, List

from app.providers.video.base import GenerativeVideoProvider
from app.providers.video.motion_engine import CinematicMotionVideoEngine
from app.config import settings, get_ffmpeg_binary

logger = logging.getLogger(__name__)

class RealFootageVideoEngine(GenerativeVideoProvider):
    """OpenCut-Style Real Motion Video Engine:
    Tự động truy xuất và biên tập VIDEO CHUYỂN ĐỘNG THẬT 100% (Real Dynamic Footage)
    từ các kho tư liệu thực tế (Wikimedia Commons Video, Pexels Video API) bám sát từng cảnh kịch bản,
    thay vì chỉ dùng ảnh tĩnh di chuyển (Ken Burns).
    """

    def __init__(self, pexels_key: Optional[str] = None, pixabay_key: Optional[str] = None):
        self.pexels_key = pexels_key or os.getenv("PEXELS_API_KEY") or getattr(settings, "PEXELS_API_KEY", None)
        self.pixabay_key = pixabay_key or os.getenv("PIXABAY_API_KEY") or getattr(settings, "PIXABAY_API_KEY", None)
        self.fallback_engine = CinematicMotionVideoEngine()

        proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy") or "http://172.16.120.13:3128"
        self.proxy = proxy
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        )

    def _extract_search_keywords(self, prompt: str) -> List[str]:
        """Trích xuất từ khóa tìm kiếm video thực tế từ prompt kịch bản."""
        # Loại bỏ các từ kỹ thuật render AI
        noise = [
            "cinematic", "photorealistic", "hyper-detailed", "masterpiece", "8k", "4k",
            "volumetric lighting", "rim light", "anamorphic", "high-end", "cgi look",
            "fast zoom in", "slow zoom in", "camera movement", "shot of", "close up",
            "wide shot", "orbit", "pan", "tilt", "dramatic", "epic", "35mm", "lens",
            "ultra detailed", "unreal engine", "octane render"
        ]
        clean_p = prompt.lower()
        for n in noise:
            clean_p = clean_p.replace(n, " ")
        words = re.findall(r'[^\W\d_]{3,}', clean_p, flags=re.UNICODE)
        
        # Chọn 2-4 từ khóa đặc trưng nhất
        stopwords = {"the", "and", "with", "from", "that", "this", "over", "into", "around", "their", "will", "than", "then"}
        core_words = [w for w in words if w not in stopwords]
        
        queries = []
        if len(core_words) >= 2:
            queries.append(" ".join(core_words[:3]))
            queries.append(" ".join(core_words[:2]))
        if core_words:
            queries.append(core_words[0])
            
        return queries

    async def _search_pexels_video(self, query: str, orientation: str = "portrait") -> Optional[str]:
        """Tìm kiếm video chuyển động thật từ Pexels Video API nếu có key."""
        if not self.pexels_key:
            return None
        try:
            url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&orientation={orientation}&per_page=3"
            req = urllib.request.Request(url, headers={
                "Authorization": self.pexels_key,
                "User-Agent": "VietnameseVideoFactory/2.0"
            })
            resp = await asyncio.to_thread(self.opener.open, req, timeout=8)
            data = json.loads(resp.read().decode())
            videos = data.get("videos", [])
            for v in videos:
                files = v.get("video_files", [])
                # Ưu tiên HD MP4
                for f in files:
                    if f.get("file_type") == "video/mp4" and f.get("quality") in ["hd", "sd"]:
                        return f.get("link")
        except Exception as e:
            logger.debug(f"Pexels search error for '{query}': {e}")
        return None

    async def _search_wikimedia_video(self, query: str) -> Optional[str]:
        """Tìm kiếm video tài liệu thực tế từ Wikimedia Commons (27,000+ video khoa học, vũ trụ, lịch sử)."""
        try:
            search_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&list=search"
                f"&srsearch={urllib.parse.quote(query)}+filetype:video&srnamespace=6&format=json&srlimit=5"
            )
            req = urllib.request.Request(search_url, headers={
                "User-Agent": "OpenCutVideoFactory/2.0 (contact@toolmxh.org)"
            })
            resp = await asyncio.to_thread(self.opener.open, req, timeout=8)
            data = json.loads(resp.read().decode())
            hits = data.get("query", {}).get("search", [])
            if not hits:
                return None

            # Lấy thông tin URL trực tiếp của video đầu tiên
            title = hits[0].get("title")
            info_url = (
                f"https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(title)}"
                f"&prop=imageinfo&iiprop=url|mime|size&format=json"
            )
            req2 = urllib.request.Request(info_url, headers={
                "User-Agent": "OpenCutVideoFactory/2.0 (contact@toolmxh.org)"
            })
            resp2 = await asyncio.to_thread(self.opener.open, req2, timeout=8)
            data2 = json.loads(resp2.read().decode())
            pages = data2.get("query", {}).get("pages", {})
            for pid, p in pages.items():
                info = p.get("imageinfo", [{}])[0]
                url = info.get("url")
                if url and any(url.lower().endswith(ext) or ext in url.lower() for ext in [".webm", ".mp4", ".ogv"]):
                    return url
        except Exception as e:
            logger.debug(f"Wikimedia video search error for '{query}': {e}")
        return None

    async def _download_stream_chunk(self, video_url: str, temp_file_path: Path, max_bytes: int = 15 * 1024 * 1024) -> bool:
        """Tải dữ liệu video stream dung lượng vừa đủ cho cảnh."""
        def _download():
            req = urllib.request.Request(video_url, headers={"User-Agent": "Mozilla/5.0"})
            with self.opener.open(req, timeout=15) as resp, open(temp_file_path, "wb") as f:
                downloaded = 0
                while downloaded < max_bytes:
                    chunk = resp.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
            return temp_file_path.exists() and temp_file_path.stat().st_size > 50000

        try:
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.warning(f"Download stream error: {e}")
            return False

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
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        img_p = Path(image_path)

        orientation = "portrait" if height >= width else "landscape"
        queries = self._extract_search_keywords(prompt)

        direct_video_url = None
        # 1. Thử Pexels Video nếu có API key
        for q in queries:
            direct_video_url = await self._search_pexels_video(q, orientation=orientation)
            if direct_video_url:
                logger.info(f"Đã tìm thấy video Pexels cho '{q}'")
                break

        # 2. Thử Wikimedia Commons Video Archive (Miễn phí 100%, NASA/Tài liệu thật)
        if not direct_video_url:
            for q in queries:
                direct_video_url = await self._search_wikimedia_video(q)
                if direct_video_url:
                    logger.info(f"Đã tìm thấy video Wikimedia cho '{q}'")
                    break

        # 3. Nếu tìm thấy video động thật -> Tải & Biên tập bằng FFmpeg
        if direct_video_url:
            temp_raw = out_p.with_suffix(".temp_raw_stream")
            success = await self._download_stream_chunk(direct_video_url, temp_raw)
            if success:
                ffmpeg_bin = get_ffmpeg_binary()
                # Cắt đúng thời lượng, căn chỉnh tỷ lệ 1080x1920 hoặc 1920x1080, 30fps
                cmd = [
                    ffmpeg_bin, "-y",
                    "-stream_loop", "-1",
                    "-i", str(temp_raw),
                    "-t", str(duration_seconds),
                    "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    str(out_p)
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                await proc.wait()

                if temp_raw.exists():
                    try:
                        temp_raw.unlink()
                    except Exception:
                        pass

                if out_p.exists() and out_p.stat().st_size > 10000:
                    # Trích xuất 1 frame thật từ video để cập nhật reference.png
                    thumb_cmd = [
                        ffmpeg_bin, "-y",
                        "-i", str(out_p),
                        "-ss", "00:00:01",
                        "-vframes", "1",
                        str(img_p)
                    ]
                    try:
                        t_proc = await asyncio.create_subprocess_exec(
                            *thumb_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        await t_proc.wait()
                    except Exception:
                        pass

                    logger.info(f"Xuất bản video động thật thành công: {out_p.name} ({duration_seconds:.2f}s)")
                    return str(out_p)

        # 4. Fallback an toàn: Nếu không tìm thấy video clip phù hợp, dùng Motion Camera Engine từ ảnh tham chiếu
        logger.info(f"Chuyển sang Motion Camera Engine cho scene: '{prompt[:40]}...'")
        return await self.fallback_engine.generate_image_to_video(
            image_path=image_path,
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            seed=seed
        )

    async def generate_text_to_video(
        self,
        prompt: str,
        output_path: str,
        duration_seconds: float,
        width: int = 1080,
        height: int = 1920,
        seed: int = -1
    ) -> str:
        # Giả lập tạm image_path trống rồi thực thi tìm kiếm video thật
        temp_img = Path(output_path).with_suffix(".thumb.png")
        return await self.generate_image_to_video(
            image_path=str(temp_img),
            prompt=prompt,
            output_path=output_path,
            duration_seconds=duration_seconds,
            width=width,
            height=height,
            seed=seed
        )
