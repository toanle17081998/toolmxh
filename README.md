# Vietnamese Generative Video Factory

> **Hệ Thống Sản Xuất Video AI Tự Động 100% Cho Mạng Xã Hội (TikTok, Reels, YouTube Shorts, YouTube)**  
> **Nguyên tắc tối thượng:** **GENERATE, DON'T DOWNLOAD** (Toàn bộ Visual, Audio và Phụ đề được AI tự động sinh mới, tối ưu hóa từng mili-giây, không phụ thuộc vào kho video stock có sẵn).

---

## 🌟 Tính Năng Nổi Bật

- 🖥️ **Web GUI Studio Đẳng Cấp:** Giao diện trực quan hiện đại, theo dõi tiến trình render thời gian thực, quản lý và xem trước video trực tiếp trên trình duyệt.
- 🎲 **AI Săn Trend Trực Tuyến (Realtime Live AI Discovery):** Tự động brainstorm các chủ đề thịnh hành, hấp dẫn, đạt triệu view bằng mô hình AI trực tiếp thay vì danh sách mẫu cố định.
- 🎙️ **Studio Neural Voice Khóa Đồng Nhất:** Lồng tiếng truyền cảm bằng công nghệ Neural TTS (NamMinh Studio VTV, Hoài My, Charon, Onyx HD...), tự động khóa cứng 1 giọng thuyết minh duy nhất xuyên suốt toàn bộ video.
- 🎥 **OpenCut Real Dynamic Video Engine (Video Chuyển Động Thật 100%):** Tự động truy xuất và biên tập các clip video chuyển động thật (NASA, Wikimedia Video Archives, Pexels 4K Video) bám sát nội dung từng phân cảnh, nói KHÔNG với ảnh tĩnh phóng to (Ken Burns).
- 🎨 **Visual Engine Đa Tầng Bám Sát Ngữ Cảnh:** Tự động kết hợp kho video tư liệu thực tế (Wikimedia Commons, NASA archives) và ảnh nghệ thuật điện ảnh 8K Photorealistic (Pollinations AI).
- 🎬 **Tự Động Thêm Intro & Outro Chuẩn Truyền Thông:**
  - **Intro Hook 3s:** Mở màn thu hút sự chú ý kèm banner điện ảnh bắt mắt.
  - **Outro Bumper:** Phân cảnh kết thúc chuyên nghiệp kèm huy hiệu CTA kêu gọi người xem Follow/Đăng ký kênh.
- 🎵 **Vietnamese Subtitles Karaoke Highlight & Auto-Ducking BGM:** Phụ đề ASS đổi màu từng từ theo giọng nói (`\k`), tự động né vùng điều hướng TikTok/Reels, nhạc nền tự động hạ âm lượng 15% khi có lời thuyết minh.
- 🔄 **Khả Năng Phục Hồi & Thử Lại Từng Cảnh (Resume / Single-Scene Retry):** Cho phép tái tạo lại riêng một cảnh cụ thể mà không cần phải kết xuất lại toàn bộ video.
- ⚙️ **Độc Lập Phần Cứng (Hardware Agnostic):** Vận hành mượt mà trên máy tính văn phòng thông thường (CPU/Cloud) lẫn máy trạm GPU chuyên dụng 24GB VRAM (ComfyUI / LTX-Video / Wan 2.1).

---

## 🚀 Cài Đặt Nhanh

### 1. Yêu cầu môi trường
- Python 3.10 trở lên
- FFmpeg (được tự động cấu hình qua `imageio-ffmpeg` nếu hệ điều hành chưa cài đặt sẵn).

### 2. Cài đặt thư viện phụ thuộc
```bash
pip install -r requirements.txt
```
*(Hoặc cài đặt nhanh: `pip install pydantic pydantic-settings edge-tts gTTS imageio-ffmpeg rich pillow numpy google-genai openai fastapi uvicorn`)*

### 3. Cấu hình khóa API (Tùy chọn)
Sao chép `.env.example` thành `.env` để kích hoạt các tính năng Pro:
```bash
cp .env.example .env
```
- `GEMINI_API_KEY`: Dùng Google Gemini 2.5 Pro/Flash để tạo kịch bản chuyên sâu và phân tích hình ảnh.
- `OPENAI_API_KEY`: Dùng GPT-4o / TTS HD lồng tiếng cao cấp.
- `COMFYUI_SERVER_URL`: Địa chỉ ComfyUI cục bộ hoặc máy chủ từ xa (mặc định: `http://127.0.0.1:8188`).

---

## 🖥️ Khởi Chạy Giao Diện Web GUI Studio

Hệ thống tích hợp sẵn giao diện Web Dashboard hoàn chỉnh, trực quan và dễ sử dụng cho mọi người dùng:

### 1. Khởi chạy nhanh
Chạy một trong các lệnh sau trong terminal:
```bash
# Khởi động và tự động mở trình duyệt
python -m app web

# Hoặc dùng alias
python -m app ui

# Hoặc chạy trực tiếp với uvicorn
python -m uvicorn app.web.server:app --host 127.0.0.1 --port 7860
```

Trình duyệt sẽ tự động mở trang quản trị tại:  
👉 **`http://127.0.0.1:7860/`**

---

### 2. Trải nghiệm các tính năng trên Web GUI

| Tính Năng | Mô Tả Trực Quan |
| :--- | :--- |
| **🎲 AI Săn Trend** | Bấm nút xúc xắc để AI tự động phân tích và tạo ngay một chủ đề giật gân, cuốn hút chuẩn xu hướng TikTok / Shorts. |
| **🎛️ Bảng Điều Khiển** | Tùy chỉnh Nền tảng (*TikTok 9:16*, *Shorts*, *Reels*, *YouTube 16:9*), Thời lượng mục tiêu (*30s, 60s, 90s, 120s*), và Chọn Giọng đọc Studio. |
| **🎙️ Tùy Chọn Giọng Đọc** | Hỗ trợ các giọng Studio hàng đầu: NamMinh (VTV/Thời sự), Hoài My (Truyền cảm), Charon (Trầm ấm điện ảnh), Onyx / Nova (OpenAI HD). |
| **📊 Real-time Tracker** | Thanh tiến trình mượt mà từ 0% đến 100%, phản ánh trực quan từng bước: Kịch bản $\rightarrow$ Lồng tiếng $\rightarrow$ Sinh ảnh $\rightarrow$ Hòa âm $\rightarrow$ Xuất bản. |
| **🎬 Auto Intro & Outro** | Tự động chèn cảnh mở đầu giật tít và cảnh kết thúc kêu gọi hành động (Call To Action) tăng tương tác. |
| **📺 Xem Trước & Tải Về** | Xem trực tiếp video thành phẩm ngay trên trình duyệt, tải video MP4 1080x1920 chất lượng cao và xem trích xuất phụ đề. |

---

## 💻 Sử Dụng Qua Dòng Lệnh (CLI)

Ngoài Web GUI, bạn hoàn toàn có thể tự động hóa quy trình sản xuất qua Terminal:

### 1. Lệnh Tạo Video Hoàn Chỉnh (`generate`)
```bash
python -m app generate \
    --topic "Bí ẩn đáy biển sâu Mariana mà khoa học chưa thể giải mã" \
    --duration 60 \
    --platform tiktok \
    --voice namminh \
    --language vi
```

**Các tham số:**
- `--topic`: Chủ đề video muốn sản xuất.
- `--duration`: Thời lượng mục tiêu tính bằng giây (`30`, `60`, `90`, `180`...).
- `--platform`: Nền tảng xuất bản (`tiktok`, `shorts`, `reels`, `youtube`).
- `--voice`: Giọng đọc Studio (`namminh`, `hoaimy`, `charon`, `onyx`, `nova`...).
- `--language`: Ngôn ngữ (mặc định: `vi`).
- `--api-key` / `--gemini-key` / `--openai-key`: Khóa API bổ sung nếu không dùng file `.env`.

### 2. Lệnh Tái Tạo Một Cảnh Cụ Thể (`regenerate`)
Nếu bạn muốn thay đổi góc quay hoặc tạo lại riêng Cảnh số 3 mà giữ nguyên toàn bộ các cảnh khác:
```bash
python -m app regenerate --project-id <PROJECT_ID> --scene 3
```

### 3. Kiểm Tra Khả Năng Phần Cứng (`hardware`)
Kiểm tra cấu hình CPU, GPU, VRAM và đề xuất mô hình AI tối ưu:
```bash
python -m app hardware
```

---

## 📂 Cấu Trúc Thư Mục Kết Xuất (`outputs/{project_id}/`)

Sau khi render hoàn tất, thư mục dự án sẽ chứa đầy đủ tài nguyên sẵn sàng xuất bản:

```
outputs/{project_id}/
├── final.mp4           # Video hoàn thiện 1080x1920 (có âm thanh, nhạc nền và phụ đề ASS)
├── thumbnail.png       # Ảnh đại diện chất lượng cao trích xuất từ cảnh đầu tiên
├── script.txt          # Kịch bản chi tiết từng cảnh có phân tách thời gian
├── subtitle.ass        # File phụ đề ASS hỗ trợ hiệu ứng Karaoke Highlight
├── subtitle.srt        # File phụ đề chuẩn SRT cho các nền tảng video
└── metadata.json       # Tiêu đề SEO, mô tả, hashtag cho TikTok, YouTube và Facebook
```

---

## 📚 Tài Liệu Nghiên Cứu Kỹ Thuật

Xem thêm tài liệu kỹ thuật chuyên sâu trong thư mục `docs/`:
- [docs/video-model-research.md](docs/video-model-research.md): So sánh chuyên sâu Wan 2.1, LTX-Video, HunyuanVideo, ComfyUI, Diffusers.
- [docs/architecture.md](docs/architecture.md): Bản thiết kế kiến trúc hệ thống và báo cáo phản biện đa tác tử Multi-Agent Brainstorming.
- [docs/hardware.md](docs/hardware.md): Đặc tả phân tầng phần cứng từ Low VRAM đến Cloud GPU.
- [docs/implementation-plan.md](docs/implementation-plan.md): Lộ trình kỹ thuật và chi tiết triển khai.

---

## 📄 Bản Quyền & Giấy Phép

Phát triển bởi đội ngũ tự động hóa sáng tạo nội dung đa phương tiện. Giấy phép mã nguồn mở MIT.
