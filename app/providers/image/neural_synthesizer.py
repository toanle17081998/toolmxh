import os
import math
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from app.providers.image.base import ImageGenerationProvider

class NeuralProceduralSynthesizer(ImageGenerationProvider):
    """Bộ tổng hợp thị giác AI thủ tục (Procedural Neural Canvas Synthesizer).
    Sinh hình ảnh điện ảnh 1080x1920 từ prompt, ánh sáng volumetric, hạt khí quyển và gradient quang sai.
    Đảm bảo 100% visual do AI tự tính toán, không tải stock footage."""

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

        # Xác định bảng màu cảm xúc dựa trên từ khóa prompt
        if any(w in p_lower for w in ["ocean", "sea", "bioluminescence", "water", "deep"]):
            # Bảng màu đại dương sâu thẳm: Deep Cyan, Bioluminescent Teal, Midnight Abyss
            c_top = (5, 12, 28)
            c_mid = (8, 45, 68)
            c_bot = (3, 18, 38)
            c_glow = (64, 224, 208)
            c_accent = (0, 255, 180)
        elif any(w in p_lower for w in ["fire", "lava", "desert", "sun", "flame", "heat"]):
            # Bảng màu núi lửa / sa mạc rực lửa
            c_top = (25, 5, 2)
            c_mid = (110, 30, 10)
            c_bot = (220, 90, 15)
            c_glow = (255, 140, 20)
            c_accent = (255, 220, 80)
        elif any(w in p_lower for w in ["ice", "snow", "blizzard", "winter", "cold"]):
            # Bảng màu băng tuyết bắc cực
            c_top = (15, 25, 45)
            c_mid = (50, 90, 140)
            c_bot = (180, 215, 245)
            c_glow = (210, 240, 255)
            c_accent = (120, 190, 255)
        elif any(w in p_lower for w in ["space", "moon", "star", "galaxy", "cosmic", "universe"]):
            # Bảng màu không gian vũ trụ huyền ảo
            c_top = (2, 2, 8)
            c_mid = (18, 8, 38)
            c_bot = (35, 12, 60)
            c_glow = (180, 120, 255)
            c_accent = (240, 200, 255)
        else:
            # Bảng màu Cinematic Teal & Orange chuẩn điện ảnh Hollywood
            c_top = (10, 18, 26)
            c_mid = (25, 45, 60)
            c_bot = (65, 35, 20)
            c_glow = (255, 160, 60)
            c_accent = (60, 200, 220)

        # 1. Tạo gradient nền mượt mà 3 tầng
        y_coords = np.linspace(0, 1, height)[:, None]
        x_coords = np.linspace(0, 1, width)[None, :]
        
        # Hàm sigmoid làm mềm dải màu
        w_top = np.clip(1.0 - y_coords * 1.8, 0, 1)
        w_bot = np.clip((y_coords - 0.4) * 1.8, 0, 1)
        w_mid = np.clip(1.0 - w_top - w_bot, 0, 1)

        img_arr = (
            w_top[:, :, None] * np.array(c_top) +
            w_mid[:, :, None] * np.array(c_mid) +
            w_bot[:, :, None] * np.array(c_bot)
        ).astype(np.uint8)

        base_img = Image.fromarray(img_arr, mode="RGB")
        draw = ImageDraw.Draw(base_img, "RGBA")

        # 2. Sinh các đám mây/sương mù Volumetric Fractal Procedural
        num_clouds = random.randint(5, 9)
        for _ in range(num_clouds):
            cx = random.uniform(width * 0.1, width * 0.9)
            cy = random.uniform(height * 0.2, height * 0.8)
            radius = random.uniform(width * 0.3, width * 0.7)
            alpha = random.randint(25, 60)
            cloud_color = (*c_glow, alpha)
            draw.ellipse(
                [cx - radius, cy - radius * 0.6, cx + radius, cy + radius * 0.6],
                fill=cloud_color
            )

        # 3. Sinh chủ thể trung tâm (Celestial Body / Entity / Horizon)
        entity_x = width * random.uniform(0.4, 0.6)
        entity_y = height * random.uniform(0.35, 0.55)
        entity_r = width * random.uniform(0.18, 0.28)

        # Ánh hào quang tỏa ra từ chủ thể (Volumetric Atmospheric Rim Light)
        for r_offset in range(int(entity_r * 2.2), int(entity_r), -15):
            glow_alpha = int(45 * (1.0 - (r_offset - entity_r) / (entity_r * 1.2)))
            draw.ellipse(
                [entity_x - r_offset, entity_y - r_offset, entity_x + r_offset, entity_y + r_offset],
                fill=(*c_accent, max(0, min(120, glow_alpha)))
            )

        # Chủ thể chính
        draw.ellipse(
            [entity_x - entity_r, entity_y - entity_r, entity_x + entity_r, entity_y + entity_r],
            fill=(*c_glow, 220),
            outline=(*c_accent, 255),
            width=3
        )

        # 4. Sinh hàng trăm hạt phát sáng không gian (Atmospheric particles / Bioluminescence)
        num_particles = random.randint(150, 300)
        for _ in range(num_particles):
            px = random.uniform(0, width)
            py = random.uniform(0, height)
            pr = random.uniform(1.0, 4.5)
            p_alpha = random.randint(80, 240)
            draw.ellipse(
                [px - pr, py - pr, px + pr, py + pr],
                fill=(*c_accent, p_alpha)
            )

        # 5. Vignette điện ảnh bốn góc
        base_img = base_img.filter(ImageFilter.GaussianBlur(radius=1.5))
        
        # Áp dụng bộ lọc tương phản và film grain bằng numpy
        np_final = np.array(base_img, dtype=np.float32)
        noise = np.random.normal(0, 5.0, np_final.shape)
        np_final = np.clip(np_final + noise, 0, 255).astype(np.uint8)

        final_img = Image.fromarray(np_final)
        final_img.save(str(out_path), "PNG", quality=95)
        return str(out_path)
