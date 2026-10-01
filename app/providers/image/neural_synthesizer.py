import os
import math
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from app.providers.image.base import ImageGenerationProvider

class NeuralProceduralSynthesizer(ImageGenerationProvider):
    """Bộ tổng hợp thị giác AI điện ảnh (Semantic Neural Scene Synthesizer).
    Tạo ra các khung cảnh hình ảnh có chủ thể rõ ràng (Hành tinh 3D, Đại dương, Khí quyển, Vũ trụ, Núi non, Bão tố...)
    Được thiết kế theo chuẩn multi-layer composite của OpenCut:
    - Layer 1: Bầu trời / Vũ trụ / Nền không gian sâu thẳm
    - Layer 2: Đối tượng địa hình / Chủ thể chính 3D (Mặt Trăng, Trái Đất, Sinh vật, Núi non)
    - Layer 3: Hiệu ứng ánh sáng Volumetric, hào quang và hạt khí quyển (Atmospheric particles)
    - Layer 4: Đổ bóng, độ tương phản và hạt phim điện ảnh (Cinematic grain & vignette)
    """

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

        if seed != -1:
            random.seed(seed)
            np.random.seed(seed % (2**32 - 1))
        else:
            seed = random.randint(10000, 999999)
            random.seed(seed)
            np.random.seed(seed % (2**32 - 1))

        p_lower = prompt.lower()

        # Phân loại thể loại cảnh để tạo bố cục phù hợp
        if any(w in p_lower for w in ["ocean", "sea", "bioluminescence", "water", "deep", "abyss", "jellyfish", "wave", "tsunami"]):
            scene_img = self._generate_ocean_abyss_scene(width, height, p_lower)
        elif any(w in p_lower for w in ["fire", "lava", "volcano", "sun", "flame", "heat", "apocalypse", "explosion", "scorch"]):
            scene_img = self._generate_apocalyptic_fire_scene(width, height, p_lower)
        elif any(w in p_lower for w in ["ice", "snow", "blizzard", "winter", "cold", "frozen", "glacier", "polar"]):
            scene_img = self._generate_arctic_glacier_scene(width, height, p_lower)
        elif any(w in p_lower for w in ["city", "cyberpunk", "future", "tech", "neon", "skyscraper"]):
            scene_img = self._generate_cyberpunk_city_scene(width, height, p_lower)
        elif any(w in p_lower for w in ["space", "moon", "star", "galaxy", "cosmic", "universe", "earth", "orbit", "planet", "black hole"]):
            scene_img = self._generate_cosmic_space_scene(width, height, p_lower)
        else:
            scene_img = self._generate_dramatic_landscape_scene(width, height, p_lower)

        # Hậu kỳ điện ảnh: Vignette, Film Grain, Color Grading
        final_img = self._apply_cinematic_postprocessing(scene_img, width, height)
        final_img.save(str(out_path), "PNG", quality=95)
        return str(out_path)

    def _generate_cosmic_space_scene(self, width: int, height: int, prompt: str) -> Image.Image:
        """Tạo khung cảnh vũ trụ sâu thẳm với hành tinh/mặt trăng 3D sắc nét."""
        img = Image.new("RGB", (width, height), (3, 4, 10))
        draw = ImageDraw.Draw(img, "RGBA")

        # 1. Hàng ngàn ngôi sao với phân bố quang phổ (trắng, xanh, vàng cam)
        for _ in range(1200):
            sx = random.randint(0, width)
            sy = random.randint(0, height)
            bright = random.randint(70, 255)
            star_type = random.random()
            if star_type > 0.85:
                star_color = (min(255, bright + 20), min(255, bright + 30), 255) # Sao xanh
            elif star_type > 0.7:
                star_color = (255, min(255, bright + 10), min(255, bright - 30)) # Sao vàng
            else:
                star_color = (bright, bright, bright)
            size = 1 if random.random() > 0.1 else random.choice([2, 3])
            draw.ellipse([sx, sy, sx + size, sy + size], fill=star_color)

        # 2. Tinh vân phát sáng rực rỡ (Cosmic Nebula)
        num_nebulae = random.randint(4, 7)
        for _ in range(num_nebulae):
            nx = random.randint(int(width * 0.1), int(width * 0.9))
            ny = random.randint(int(height * 0.1), int(height * 0.9))
            nr = random.randint(250, 600)
            n_color = random.choice([
                (20, 50, 140, 25),   # Deep blue
                (120, 30, 160, 20),  # Purple
                (10, 110, 120, 25),  # Cyan
                (180, 50, 40, 18)    # Amber/crimson
            ])
            draw.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=n_color)

        # 3. Chủ thể hành tinh / Mặt Trăng 3D
        is_moon = "moon" in prompt or "mặt trăng" in prompt
        radius = int(width * random.uniform(0.28, 0.38))
        cx = width // 2 + random.randint(-60, 60)
        cy = int(height * random.uniform(0.38, 0.48))

        y, x = np.ogrid[-radius:radius, -radius:radius]
        mask = x**2 + y**2 <= radius**2
        z = np.sqrt(np.maximum(0, radius**2 - x**2 - y**2))

        # Hướng nguồn sáng (Key Light Direction)
        lx, ly, lz = -0.65, -0.45, 0.6
        norm = math.sqrt(lx**2 + ly**2 + lz**2)
        lx, ly, lz = lx/norm, ly/norm, lz/norm
        diffuse = np.clip((x*lx + y*ly + z*lz) / radius, 0, 1)

        # Kết cấu bề mặt (Procedural Terrain / Craters)
        noise = np.random.rand(radius*2, radius*2) * 0.35
        if is_moon:
            # Mặt Trăng bạc xám với hố va chạm và biển dung nham cổ
            r_chan = (diffuse * 190 + 25 + noise * 45).astype(np.uint8)
            g_chan = (diffuse * 195 + 28 + noise * 45).astype(np.uint8)
            b_chan = (diffuse * 210 + 35 + noise * 50).astype(np.uint8)
        else:
            # Trái Đất xanh biển, mảng lục địa và mây trắng xoáy
            continents = (np.sin(x * 0.04) * np.cos(y * 0.04) > 0.1).astype(np.float32)
            clouds = (np.sin(x * 0.08 + y * 0.06) > 0.45).astype(np.float32)
            
            r_chan = (diffuse * (30 + continents * 40 + clouds * 160) + noise * 30).astype(np.uint8)
            g_chan = (diffuse * (70 + continents * 90 + clouds * 160) + noise * 30).astype(np.uint8)
            b_chan = (diffuse * (190 - continents * 60 + clouds * 70) + noise * 35).astype(np.uint8)

        a_chan = (mask * 255).astype(np.uint8)
        sphere_rgba = np.stack([r_chan, g_chan, b_chan, a_chan], axis=-1)
        sphere_pil = Image.fromarray(sphere_rgba, mode="RGBA")

        # 4. Hào quang tán xạ khí quyển (Atmospheric Rayleigh Glow)
        glow_padding = 80
        glow_img = Image.new("RGBA", (radius*2 + glow_padding*2, radius*2 + glow_padding*2), (0,0,0,0))
        glow_draw = ImageDraw.Draw(glow_img, "RGBA")
        glow_color = (90, 190, 255) if not is_moon else (180, 200, 255)

        for r_offset in range(radius + glow_padding, radius, -2):
            dist = r_offset - radius
            alpha = int(45 * (1.0 - dist / glow_padding))
            glow_draw.ellipse(
                [radius + glow_padding - r_offset, radius + glow_padding - r_offset,
                 radius + glow_padding + r_offset, radius + glow_padding + r_offset],
                fill=(*glow_color, alpha)
            )

        img.paste(glow_img, (cx - radius - glow_padding, cy - radius - glow_padding), glow_img)
        img.paste(sphere_pil, (cx - radius, cy - radius), sphere_pil)

        # 5. Mảnh vỡ không gian / Bụi sao nếu có sự kiện nổ hoặc biến mất
        if any(w in prompt for w in ["disappear", "biến mất", "explode", "vỡ", "shatter", "dust"]):
            for _ in range(350):
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(radius * 0.9, radius * 2.2)
                dx = int(cx + math.cos(angle) * dist)
                dy = int(cy + math.sin(angle) * dist)
                p_size = random.randint(1, 4)
                draw.ellipse([dx, dy, dx + p_size, dy + p_size], fill=(255, 230, 180, random.randint(120, 255)))

        return img

    def _generate_ocean_abyss_scene(self, width: int, height: int, prompt: str) -> Image.Image:
        """Tạo khung cảnh đại dương sâu thẳm với tia sáng khúc xạ và sinh vật phát quang."""
        img = Image.new("RGB", (width, height), (2, 10, 25))
        draw = ImageDraw.Draw(img, "RGBA")

        # Gradient độ sâu nước biển
        for y in range(height):
            ratio = y / height
            r = int(2 * (1 - ratio))
            g = int(18 * (1 - ratio) + 4 * ratio)
            b = int(60 * (1 - ratio) + 12 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Tia sáng mặt trời xuyên qua mặt nước (Sunbeams / God Rays)
        for i in range(7):
            start_x = random.randint(-100, width + 100)
            end_x = start_x + random.randint(150, 400)
            poly = [
                (start_x, 0),
                (start_x + random.randint(40, 90), 0),
                (end_x + random.randint(120, 250), height),
                (end_x, height)
            ]
            draw.polygon(poly, fill=(50, 180, 220, random.randint(12, 28)))

        # Sinh vật biển phát quang / Sứa khổng lồ (Bioluminescent Creature)
        jx, jy = width // 2 + random.randint(-80, 80), int(height * 0.48)
        jr = int(width * 0.22)
        
        # Mũ sứa phát sáng
        draw.chord([jx - jr, jy - jr, jx + jr, jy + jr], 180, 360, fill=(40, 240, 210, 160), outline=(120, 255, 240, 230), width=3)
        # Các xúc tu mềm mại
        for tx in range(jx - int(jr*0.8), jx + int(jr*0.8), 16):
            points = []
            for ty in range(jy, jy + random.randint(250, 450), 20):
                offset_x = tx + int(math.sin(ty * 0.05) * 25)
                points.append((offset_x, ty))
            if len(points) > 1:
                draw.line(points, fill=(60, 220, 240, 140), width=2)

        # Hàng ngàn hạt bọt nước và sinh vật phù du phát sáng
        for _ in range(400):
            bx = random.randint(0, width)
            by = random.randint(0, height)
            bs = random.choice([1, 2, 3])
            draw.ellipse([bx, by, bx + bs, by + bs], fill=(80, 240, 220, random.randint(60, 220)))

        return img

    def _generate_apocalyptic_fire_scene(self, width: int, height: int, prompt: str) -> Image.Image:
        """Tạo khung cảnh thảm họa núi lửa / bốc cháy / dung nham đỏ rực."""
        img = Image.new("RGB", (width, height), (15, 3, 2))
        draw = ImageDraw.Draw(img, "RGBA")

        # Bầu trời khói lửa khổng lồ
        for y in range(int(height * 0.65)):
            ratio = y / (height * 0.65)
            r = int(25 + 90 * ratio)
            g = int(5 + 25 * ratio)
            b = int(2)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Mặt đất dung nham rực đỏ nứt nẻ
        ground_y = int(height * 0.65)
        draw.rectangle([(0, ground_y), (width, height)], fill=(12, 4, 3))

        # Dòng nham thạch nóng chảy (Magma river)
        for _ in range(5):
            pts = []
            cx = random.randint(int(width*0.2), int(width*0.8))
            for y in range(ground_y, height, 30):
                cx += random.randint(-25, 25)
                pts.append((cx, y))
            if len(pts) > 1:
                draw.line(pts, fill=(255, 120, 20, 220), width=random.randint(6, 18))
                draw.line(pts, fill=(255, 230, 100, 255), width=random.randint(2, 5))

        # Tàn tro và tia lửa bay lên không trung (Embers)
        for _ in range(350):
            ex = random.randint(0, width)
            ey = random.randint(0, height)
            es = random.choice([1, 2, 3])
            draw.ellipse([ex, ey, ex + es, ey + es], fill=(255, random.randint(140, 220), 30, random.randint(120, 255)))

        return img

    def _generate_arctic_glacier_scene(self, width: int, height: int, prompt: str) -> Image.Image:
        """Tạo khung cảnh băng giá cực địa với Cực quang (Aurora Borealis)."""
        img = Image.new("RGB", (width, height), (5, 12, 28))
        draw = ImageDraw.Draw(img, "RGBA")

        # Cực quang xanh ngọc lượn sóng trên bầu trời (Aurora)
        for wave in range(3):
            pts_top = []
            pts_bot = []
            base_y = int(height * 0.22) + wave * 90
            for x in range(0, width + 50, 25):
                offset_y = int(math.sin(x * 0.008 + wave) * 60 + math.cos(x * 0.015) * 35)
                pts_top.append((x, base_y + offset_y - 70))
                pts_bot.append((x, base_y + offset_y + 70))
            poly = pts_top + list(reversed(pts_bot))
            draw.polygon(poly, fill=(40, 240, 150, 45))

        # Dãy núi băng tuyết nhọn hoắt
        peak_y = int(height * 0.62)
        peaks = [(0, height)]
        cx = 0
        while cx < width:
            step = random.randint(80, 160)
            cx += step
            cy = peak_y + random.randint(-120, 80)
            peaks.append((cx, cy))
        peaks.append((width, height))
        draw.polygon(peaks, fill=(180, 215, 245))
        draw.polygon(peaks, outline=(230, 245, 255), width=2)

        # Bông tuyết trắng xóa
        for _ in range(300):
            sx = random.randint(0, width)
            sy = random.randint(0, height)
            draw.ellipse([sx, sy, sx + 2, sy + 2], fill=(240, 250, 255, random.randint(120, 240)))

        return img

    def _generate_cyberpunk_city_scene(self, width: int, height: int, prompt: str) -> Image.Image:
        """Tạo khung cảnh thành phố tương lai rực rỡ đèn neon."""
        img = Image.new("RGB", (width, height), (8, 6, 20))
        draw = ImageDraw.Draw(img, "RGBA")

        # Tòa nhà chọc trời silhouette nhiều lớp
        for layer in range(3):
            base_y = int(height * (0.45 + layer * 0.12))
            col_width = random.randint(70, 130)
            cur_x = 0
            while cur_x < width:
                b_height = random.randint(200, 500)
                b_top = base_y - b_height
                draw.rectangle([cur_x, b_top, cur_x + col_width, height], fill=(12 + layer*10, 10 + layer*8, 25 + layer*12))
                # Ô cửa sổ phát sáng
                for wy in range(b_top + 20, height - 100, 30):
                    if random.random() > 0.4:
                        w_col = random.choice([(255, 60, 160), (40, 230, 255), (255, 220, 80)])
                        draw.rectangle([cur_x + 10, wy, cur_x + col_width - 10, wy + 8], fill=(*w_col, 180))
                cur_x += col_width + random.randint(10, 30)

        return img

    def _generate_dramatic_landscape_scene(self, width: int, height: int, prompt: str) -> Image.Image:
        """Tạo khung cảnh điện ảnh thiên nhiên hùng vĩ với hoàng hôn/bình minh và người đơn độc."""
        img = Image.new("RGB", (width, height), (20, 15, 30))
        draw = ImageDraw.Draw(img, "RGBA")

        # Hoàng hôn rực rỡ
        for y in range(int(height * 0.65)):
            ratio = y / (height * 0.65)
            r = int(255 * ratio + 30 * (1 - ratio))
            g = int(120 * ratio + 20 * (1 - ratio))
            b = int(40 * ratio + 60 * (1 - ratio))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Mặt Trời khổng lồ hoàng hôn
        sun_x, sun_y, sun_r = width // 2, int(height * 0.42), 160
        draw.ellipse([sun_x - sun_r, sun_y - sun_r, sun_x + sun_r, sun_y + sun_r], fill=(255, 235, 180, 240))

        # Đỉnh núi silhouette trùng điệp
        for layer in range(3):
            pts = [(0, height)]
            base_y = int(height * 0.55 + layer * 70)
            cx = 0
            while cx < width:
                cx += random.randint(90, 180)
                cy = base_y + random.randint(-60, 60)
                pts.append((cx, cy))
            pts.append((width, height))
            draw.polygon(pts, fill=(15 + layer*5, 10 + layer*4, 20 + layer*5))

        # Silhouette người đứng trên đỉnh đồi đơn độc nhìn về chân trời
        person_x = width // 2 + 100
        person_y = int(height * 0.68)
        # Thân người
        draw.rectangle([person_x - 6, person_y - 35, person_x + 6, person_y], fill=(5, 5, 8))
        # Đầu
        draw.ellipse([person_x - 6, person_y - 48, person_x + 6, person_y - 36], fill=(5, 5, 8))

        return img

    def _apply_cinematic_postprocessing(self, img: Image.Image, width: int, height: int) -> Image.Image:
        """Áp dụng bộ lọc quang học điện ảnh: Vignette, Film Grain và Color Grading."""
        # 1. Vignette (Tối 4 góc chuẩn điện ảnh anamorphic)
        vignette = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        v_draw = ImageDraw.Draw(vignette, "RGBA")
        center_x, center_y = width / 2, height / 2
        max_dist = math.sqrt(center_x**2 + center_y**2)

        # Sử dụng mesh radial tối dần
        for r in range(int(min(width, height) * 0.45), int(max_dist), 20):
            alpha = int(140 * ((r - min(width, height) * 0.45) / (max_dist - min(width, height) * 0.45)))
            v_draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], outline=(0, 0, 0, min(140, alpha)), width=22)

        img.paste(vignette, (0, 0), vignette)

        # 2. Tăng cường độ tương phản và sắc nét
        img = img.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.18)

        # 3. Hạt phim hữu cơ (35mm Organic Film Grain)
        arr = np.array(img, dtype=np.float32)
        grain = np.random.normal(0, 3.5, arr.shape)
        arr = np.clip(arr + grain, 0, 255).astype(np.uint8)

        return Image.fromarray(arr)
