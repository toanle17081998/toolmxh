# Vietnamese Generative Video Factory

> **Hệ Thống Sản Xuất Video AI Tự Động 100% Cho Mạng Xã Hội (TikTok, Reels, YouTube Shorts, YouTube)**  
> **Nguyên tắc tối thượng:** **GENERATE, DON'T DOWNLOAD** (Toàn bộ Visual, Audio và Phụ đề được AI tự động sinh mới, không dùng stock footage).

---

## 🌟 Tính Năng Nổi Bật

- **Visual Pipeline Generative 100%:** Sử dụng cơ chế phân tầng (T2I $\rightarrow$ I2V) với các mô hình SOTA DiT (Wan 2.1, LTX-Video, FLUX.1) và bộ sinh chuyển động camera điện ảnh thực tế (30fps, 1080x1920).
- **Audio-First Timeline Synchronization:** Không đoán độ dài văn bản. Giọng thuyết minh tiếng Việt chuẩn (Neural TTS) quyết định chính xác thời lượng từng cảnh đến từng mili-giây.
- **Vietnamese Subtitles Karaoke Highlight:** Tự động sinh file phụ đề `.ass` hỗ trợ hiệu ứng nổi bật từng từ khi nói (`\k`), phông chữ nét căng, tự động né vùng an toàn giao diện tương tác của TikTok / Reels.
- **Auto-Ducking Background Music:** Tự động hạ âm lượng nhạc nền xuống 15% khi có giọng thuyết minh và nâng nhẹ nhàng khi ngắt câu.
- **Khả Năng Phục Hồi & Thử Lại Từng Cảnh (Resume / Single-Scene Retry):** Nếu một cảnh bị lỗi hoặc người dùng muốn đổi góc quay, chỉ cần chạy lệnh `regenerate` cho cảnh đó mà không phải render lại toàn bộ video.
- **Độc Lập Phần Cứng (Hardware Agnostic):** Tự động thích ứng từ máy tính không có card rời (qua Cloud Provider / Fallback Synthesizer) đến máy trạm GPU 24GB VRAM (ComfyUI / Diffusers).

---

## 🚀 Cài Đặt Nhanh

### 1. Yêu cầu môi trường
- Python 3.10+
- FFmpeg (được tự động cấu hình qua `imageio-ffmpeg` nếu hệ thống chưa cài toàn cục).

### 2. Cài đặt thư viện
```bash
pip install -r requirements.txt
```
*(hoặc `pip install pydantic pydantic-settings edge-tts gTTS imageio-ffmpeg rich pillow numpy google-genai openai`)*

### 3. Cấu hình khóa API (Tùy chọn)
Sao chép `.env.example` thành `.env` và điền khóa API mong muốn:
```bash
cp .env.example .env
```
- `GEMINI_API_KEY`: Dùng Google Gemini 2.5 Flash / Imagen 3.
- `OPENAI_API_KEY`: Dùng GPT-4o / DALL-E 3.
- `COMFYUI_SERVER_URL`: Địa chỉ ComfyUI cục bộ hoặc máy chủ từ xa (mặc định `http://127.0.0.1:8188`).

---

## 🎬 Hướng Dẫn Sử Dụng

### 1. Lệnh Tạo Video Hoàn Chỉnh (Generate)
```bash
python -m app generate \
    --topic "Nếu Mặt Trăng biến mất thì chuyện gì sẽ xảy ra?" \
    --duration 60 \
    --platform tiktok \
    --language vi
```

Các tùy chọn:
- `--topic`: Chủ đề video muốn khai thác.
- `--duration`: Thời lượng mục tiêu tính bằng giây (30, 60, 180...).
- `--platform`: Nền tảng xuất bản (`tiktok`, `shorts`, `reels`, `youtube`).
- `--language`: Ngôn ngữ (mặc định `vi`).

### 2. Lệnh Tái Tạo Một Cảnh Cụ Thể (Regenerate Single Scene)
Nếu bạn muốn tạo lại riêng Cảnh 4 mà không ảnh hưởng tới các cảnh khác:
```bash
python -m app regenerate --project-id <PROJECT_ID> --scene 4
```

### 3. Kiểm Tra Khả Năng Phần Cứng (Hardware Profile)
```bash
python -m app hardware
```

---

## 📂 Cấu Trúc File Xuất Bản (`outputs/{project_id}/`)

Sau khi hoàn thành, hệ thống sẽ kết xuất bộ tài nguyên sẵn sàng đăng tải:
```
outputs/{project_id}/
├── final.mp4           # Video hoàn thiện 1080x1920 (có âm thanh, nhạc nền và phụ đề ASS)
├── thumbnail.png       # Ảnh đại diện chất lượng cao trích xuất từ cảnh đầu tiên
├── script.txt          # Kịch bản chi tiết từng cảnh có phân tách thời gian
├── subtitle.srt        # File phụ đề chuẩn SRT
└── metadata.json       # Tiêu đề SEO, mô tả, hashtag cho TikTok, YouTube và Facebook
```

---

## 📚 Tài Liệu Nghiên Cứu Kỹ Thuật

Xem chi tiết trong thư mục `docs/`:
- [docs/video-model-research.md](docs/video-model-research.md): So sánh chuyên sâu Wan 2.1, LTX-Video, HunyuanVideo, ComfyUI, Diffusers.
- [docs/architecture.md](docs/architecture.md): Bản thiết kế kiến trúc hệ thống và báo cáo phản biện đa tác tử Multi-Agent Brainstorming.
- [docs/hardware.md](docs/hardware.md): Đặc tả phân tầng phần cứng từ Low VRAM đến Cloud GPU.
- [docs/implementation-plan.md](docs/implementation-plan.md): Lộ trình kỹ thuật và chi tiết triển khai.
