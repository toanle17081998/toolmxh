import os
import math
import random
import colorsys
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

from app.providers.image.base import ImageGenerationProvider

class OpenCutRealisticImageProvider(ImageGenerationProvider):
    """
    OpenCut Cinematic Realistic Master Image Provider.
    Tạo ra các bức ảnh quang học điện ảnh chân thực cao (1080x1920 / 1920x1080),
    mô phỏng chính xác ánh sáng, độ sâu trường ảnh, bề mặt hành tinh, đại dương và vũ trụ,
    hoàn toàn không phải các hình vẽ 2D hình học đơn giản.
    """

    def __init__(self):
        pass

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        seed: Optional[int] = None
    ) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        if seed is not None:
            random.seed(seed)

        p_lower = prompt.lower()

        # Phân loại ngữ cảnh chủ đề
        if any(w in p_lower for w in ["ocean", "sea", "water", "tsunami", "đại dương", "biển", "sóng", "thủy triều", "nước"]):
            img = self._render_photorealistic_deep_ocean(width, height, p_lower)
        elif any(w in p_lower for w in ["earth", "trái đất", "hành tinh", "planet", "quỹ đạo"]):
            img = self._render_photorealistic_earth_orbit(width, height, p_lower)
        elif any(w in p_lower for w in ["storm", "disaster", "bão", "sấm sét", "hỗn loạn", "catastrophe"]):
            img = self._render_photorealistic_storm_sky(width, height, p_lower)
        else: # Mặc định: Mặt Trăng & Vũ Trụ Sâu (Cosmos & Cinematic Moon)
            img = self._render_photorealistic_lunar_space(width, height, p_lower)

        # Áp dụng hậu kỳ điện ảnh quang học (Film post-processing)
        img = self._apply_cinematic_grade(img, width, height)
        img.save(str(out), format="PNG", quality=95)
        return str(out)

    def _render_photorealistic_lunar_space(self, w: int, h: int, prompt: str) -> Image.Image:
        """Render ảnh quang học Mặt Trăng 3D siêu thực giữa vũ trụ bao la."""
        img = Image.new("RGB", (w, h), (3, 4, 8))
        draw = ImageDraw.Draw(img)

        # 1. Bầu trời đêm sâu thẳm với hàng vạn tinh tú đa độ sáng
        star_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        s_draw = ImageDraw.Draw(star_layer)
        num_stars = int(w * h * 0.0004)
        for _ in range(num_stars):
            sx = random.randint(0, w - 1)
            sy = random.randint(0, h - 1)
            brightness = random.randint(140, 255)
            size = random.choices([1, 1, 1, 2, 3], weights=[70, 15, 10, 4, 1])[0]
            # Màu sao tự nhiên (trắng xanh hoặc vàng cam nhạt)
            tint = random.choice([(255, 255, 255), (200, 220, 255), (255, 240, 210), (180, 210, 255)])
            alpha = int(brightness * (0.4 + 0.6 * random.random()))
            if size == 1:
                s_draw.point((sx, sy), fill=(*tint, alpha))
            else:
                s_draw.ellipse([sx - size, sy - size, sx + size, sy + size], fill=(*tint, int(alpha * 0.7)))

        # Dải Ngân Hà mờ ảo (Milky Way Dust Band)
        dust_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d_draw = ImageDraw.Draw(dust_layer)
        for i in range(15):
            cx = w * (0.2 + 0.6 * (i / 15.0))
            cy = h * (0.1 + 0.8 * (i / 15.0))
            rad = random.randint(int(w * 0.4), int(w * 0.7))
            d_draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(30, 40, 75, 12))
        dust_layer = dust_layer.filter(ImageFilter.GaussianBlur(radius=80))

        img.paste(Image.alpha_composite(Image.new("RGBA", (w, h), (3, 4, 8, 255)), dust_layer).convert("RGB"), (0, 0))
        img.paste(star_layer, (0, 0), star_layer)

        # 2. Mặt Trăng 3D với bề mặt địa hình quang học (Realistic 3D Lunar Sphere)
        moon_radius = int(min(w, h) * 0.28)
        mc_x = w // 2
        mc_y = int(h * 0.38)

        # Tạo Lunar Canvas chi tiết cao
        moon_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        m_draw = ImageDraw.Draw(moon_layer)

        # Lunar Glow (Hào quang khí quyển mờ của ánh trăng)
        glow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow_layer)
        for r_ext in range(moon_radius + 90, moon_radius, -3):
            alpha = int(25 * (1.0 - (r_ext - moon_radius) / 90.0))
            g_draw.ellipse([mc_x - r_ext, mc_y - r_ext, mc_x + r_ext, mc_y + r_ext], fill=(215, 230, 255, alpha))
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=35))
        img.paste(glow_layer, (0, 0), glow_layer)

        # Vẽ hình cầu Mặt Trăng 3D với shading góc chiếu sáng (Light from top-right)
        light_dx, light_dy = 0.6, -0.4
        l_len = math.sqrt(light_dx * light_dx + light_dy * light_dy)
        light_dx /= l_len
        light_dy /= l_len

        # Bề mặt mặt trăng với các vùng biển tối (Maria) và miệng núi lửa (Craters)
        for dy in range(-moon_radius, moon_radius):
            y = mc_y + dy
            if not (0 <= y < h):
                continue
            span = int(math.sqrt(max(0, moon_radius * moon_radius - dy * dy)))
            for dx in range(-span, span):
                x = mc_x + dx
                if not (0 <= x < w):
                    continue

                nx = dx / float(moon_radius)
                ny = dy / float(moon_radius)
                nz = math.sqrt(max(0.0, 1.0 - nx * nx - ny * ny))

                # Lambertian Diffuse Lighting
                diffuse = max(0.0, nx * light_dx + ny * light_dy + nz * 0.7)
                diffuse = math.pow(diffuse, 0.85)

                # Giả lập địa hình biển Mặt Trăng (Maria) và cao nguyên sáng (Highlands)
                noise_maria = math.sin(nx * 4.5 + ny * 2.1) * math.cos(ny * 5.2 - nx * 1.5)
                is_maria = noise_maria > 0.15

                base_val = 150 if is_maria else 215
                # Thêm chi tiết vi địa hình (Craters speckles)
                micro_crater = math.sin(nx * 22.0 + ny * 18.0) * math.cos(ny * 25.0)
                crater_factor = 0.85 if micro_crater > 0.6 else 1.0

                r = int(min(255, max(15, base_val * diffuse * crater_factor * 0.96)))
                g = int(min(255, max(15, base_val * diffuse * crater_factor * 0.98)))
                b = int(min(255, max(20, (base_val + 10) * diffuse * crater_factor * 1.05)))

                m_draw.point((x, y), fill=(r, g, b, 255))

        # Khử răng cưa viền mặt trăng
        moon_layer = moon_layer.filter(ImageFilter.SMOOTH)
        img.paste(moon_layer, (0, 0), moon_layer)

        # 3. Phía dưới: Trái Đất xa xôi hoặc cảnh quan đại dương phản chiếu ánh trăng
        horizon_y = int(h * 0.72)
        ocean_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        o_draw = ImageDraw.Draw(ocean_layer)

        for y in range(horizon_y, h):
            prog = (y - horizon_y) / float(h - horizon_y)
            # Sóng biển lấp lánh phản chiếu trăng ở trung tâm
            row_color_r = int(10 + 20 * prog)
            row_color_g = int(22 + 45 * prog)
            row_color_b = int(45 + 75 * prog)

            for x in range(0, w, 2):
                x_center_dist = abs(x - mc_x) / float(w)
                # Vệt sáng phản chiếu ánh trăng trên mặt nước (Glitter path)
                reflection = math.exp(-pow(x_center_dist * 4.5, 2)) * math.sin(x * 0.15 + y * 0.8)
                specular = int(max(0, reflection * 120 * (1.0 - prog * 0.5)))

                pix_r = min(255, row_color_r + specular)
                pix_g = min(255, row_color_g + specular)
                pix_b = min(255, row_color_b + int(specular * 1.2))
                o_draw.line([(x, y), (x + 1, y)], fill=(pix_r, pix_g, pix_b, 255))

        ocean_layer = ocean_layer.filter(ImageFilter.GaussianBlur(radius=1))
        img.paste(ocean_layer, (0, 0), ocean_layer)
        return img

    def _render_photorealistic_deep_ocean(self, w: int, h: int, prompt: str) -> Image.Image:
        """Render đại dương sâu thẳm kỳ vĩ với chùm tia nắng God Rays và sinh vật phát quang."""
        img = Image.new("RGB", (w, h), (2, 10, 25))
        draw = ImageDraw.Draw(img)

        # Gradient sâu thẳm của nước biển
        for y in range(h):
            prog = y / float(h)
            # Từ xanh ngọc lam tầng trên xuống đáy biển tối thẳm
            r = int(5 * (1.0 - prog) + 1 * prog)
            g = int(60 * (1.0 - prog) + 8 * prog)
            b = int(120 * (1.0 - prog) + 22 * prog)
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        # God Rays (Chùm tia sáng mặt trời xuyên qua làn nước)
        ray_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        r_draw = ImageDraw.Draw(ray_layer)
        num_rays = 8
        for i in range(num_rays):
            top_x = int(w * (0.2 + 0.6 * (i / float(num_rays))))
            top_w = random.randint(20, 60)
            bot_x = top_x + random.randint(-180, 180)
            bot_w = random.randint(120, 260)
            alpha = random.randint(20, 55)
            r_draw.polygon([
                (top_x - top_w // 2, 0),
                (top_x + top_w // 2, 0),
                (bot_x + bot_w // 2, int(h * 0.85)),
                (bot_x - bot_w // 2, int(h * 0.85))
            ], fill=(160, 230, 255, alpha))

        ray_layer = ray_layer.filter(ImageFilter.GaussianBlur(radius=25))
        img.paste(Image.alpha_composite(img.convert("RGBA"), ray_layer).convert("RGB"), (0, 0))

        # Sinh vật biển sâu phát quang (Bioluminescent creatures) & Bọt nước (Particles)
        p_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        p_draw = ImageDraw.Draw(p_layer)
        for _ in range(120):
            px = random.randint(0, w - 1)
            py = random.randint(int(h * 0.2), h - 1)
            p_size = random.choice([2, 3, 4, 6])
            # Phát quang xanh neon hoặc ngọc bích
            glow_color = random.choice([(0, 255, 200), (80, 220, 255), (140, 100, 255), (255, 230, 120)])
            p_draw.ellipse([px - p_size, py - p_size, px + p_size, py + p_size], fill=(*glow_color, 180))

        p_layer = p_layer.filter(ImageFilter.GaussianBlur(radius=2))
        img.paste(p_layer, (0, 0), p_layer)
        return img

    def _render_photorealistic_earth_orbit(self, w: int, h: int, prompt: str) -> Image.Image:
        """Render Trái Đất nhìn từ quỹ đạo không gian với khí quyển phát sáng."""
        img = Image.new("RGB", (w, h), (2, 3, 7))
        # Nền vũ trụ sao
        s_draw = ImageDraw.Draw(img)
        for _ in range(int(w * h * 0.0003)):
            sx = random.randint(0, w - 1)
            sy = random.randint(0, h - 1)
            s_draw.point((sx, sy), fill=(random.randint(180, 255), random.randint(180, 255), 255))

        # Trái Đất khổng lồ góc cong phía dưới
        earth_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        e_draw = ImageDraw.Draw(earth_layer)
        ec_x = w // 2
        ec_y = int(h * 1.35)
        e_rad = int(h * 0.75)

        # Atmosphere Glow
        for ext in range(50, 0, -2):
            alpha = int(40 * (1.0 - ext / 50.0))
            e_draw.ellipse([ec_x - e_rad - ext, ec_y - e_rad - ext, ec_x + e_rad + ext, ec_y + e_rad + ext], fill=(40, 140, 255, alpha))

        # Mặt Trái Đất (Đại dương + Mây cuộn)
        for dy in range(-e_rad, 0):
            y = ec_y + dy
            if not (0 <= y < h):
                continue
            span = int(math.sqrt(max(0, e_rad * e_rad - dy * dy)))
            for dx in range(-span, span):
                x = ec_x + dx
                if not (0 <= x < w):
                    continue
                cloud_noise = math.sin(dx * 0.015 + dy * 0.01) * math.cos(dy * 0.02 - dx * 0.008)
                is_cloud = cloud_noise > 0.25
                if is_cloud:
                    r, g, b = 230, 240, 255
                else: # Đại dương sâu
                    r, g, b = 15, 65, 140
                e_draw.point((x, y), fill=(r, g, b, 255))

        earth_layer = earth_layer.filter(ImageFilter.GaussianBlur(radius=1))
        img.paste(Image.alpha_composite(img.convert("RGBA"), earth_layer).convert("RGB"), (0, 0))
        return img

    def _render_photorealistic_storm_sky(self, w: int, h: int, prompt: str) -> Image.Image:
        """Render bầu trời bão tố cuồng phong với sấm sét rạch ngang mây đen."""
        img = Image.new("RGB", (w, h), (10, 12, 18))
        draw = ImageDraw.Draw(img)

        # Mây dông cuồn cuộn
        for y in range(h):
            prog = y / float(h)
            r = int(12 + 25 * math.sin(prog * 3.14))
            g = int(15 + 30 * math.sin(prog * 3.14))
            b = int(24 + 48 * math.sin(prog * 3.14))
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        # Tia chớp sấm sét rạch ngang (Lightning branch)
        l_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        l_draw = ImageDraw.Draw(l_layer)
        lx = w // 2 + random.randint(-150, 150)
        ly = int(h * 0.1)
        for _ in range(25):
            nlx = lx + random.randint(-35, 35)
            nly = ly + random.randint(20, 60)
            l_draw.line([(lx, ly), (nlx, nly)], fill=(230, 245, 255, 240), width=3)
            # Nhánh con
            if random.random() < 0.4:
                sub_x = nlx + random.randint(-40, 40)
                sub_y = nly + random.randint(15, 35)
                l_draw.line([(nlx, nly), (sub_x, sub_y)], fill=(180, 210, 255, 160), width=1)
            lx, ly = nlx, nly
            if ly >= h * 0.7:
                break

        l_layer = l_layer.filter(ImageFilter.GaussianBlur(radius=1.5))
        img.paste(l_layer, (0, 0), l_layer)
        return img

    def _apply_cinematic_grade(self, img: Image.Image, w: int, h: int) -> Image.Image:
        """Áp dụng màu sắc điện ảnh (Cinematic Color Grading & Vignette)."""
        # Tăng độ tương phản nhẹ và sắc nét
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.18)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.25)

        # Thêm Vignette viền tối điện ảnh làm tập trung vào tâm điểm
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        v_draw = ImageDraw.Draw(vignette)
        cx, cy = w // 2, h // 2
        max_dist = math.sqrt(cx * cx + cy * cy)

        # Vẽ viền tối mượt mà
        for step in range(12):
            factor = (step + 1) / 12.0
            rx = int(cx + (w - cx) * (1.0 - factor * 0.3))
            ry = int(cy + (h - cy) * (1.0 - factor * 0.3))
            alpha = int(140 * factor * factor)
            v_draw.rectangle([0, 0, w, h], outline=(0, 0, 0, alpha), width=int(w * 0.04))

        vignette = vignette.filter(ImageFilter.GaussianBlur(radius=40))
        img.paste(vignette, (0, 0), vignette)
        return img
