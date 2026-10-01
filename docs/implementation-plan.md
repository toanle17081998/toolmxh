# Kế Hoạch Triển Khai Chi Tiết: Vietnamese Generative Video Factory
## (Engineering Implementation Plan & Roadmap)

> **Dự án:** Vietnamese Generative Video Factory  
> **Kiến trúc sư:** Principal AI Engineer & Senior Python Architect  
> **Mục tiêu:** Xây dựng Vertical Slice MVP thực thi End-to-End không có mock video.

---

## 1. Cấu Trúc Mã Nguồn Tiêu Chuẩn (Project Layout)

```
toolmxh/
├── docs/
│   ├── video-model-research.md
│   ├── research.md
│   ├── hardware.md
│   ├── architecture.md
│   └── implementation-plan.md
├── app/
│   ├── __init__.py
│   ├── __main__.py             # Entrypoint cho: python -m app
│   ├── config.py               # Settings, API keys, Hardware profiles (.env)
│   ├── cli.py                  # Giao diện dòng lệnh CLI (Argparse / Click / Rich)
│   │
│   ├── models/                 # Pydantic Data Contracts
│   │   ├── __init__.py
│   │   ├── project.py          # ProjectState, ProjectConfig, ProjectMetadata
│   │   ├── script.py           # StructuredScript, SceneScript
│   │   ├── storyboard.py       # Storyboard, SceneStoryboard, CharacterBible, VisualBible
│   │   └── timeline.py         # AudioTimeline, SceneTiming, SubtitleItem
│   │
│   ├── core/                   # State Machine & File System Management
│   │   ├── __init__.py
│   │   ├── state_manager.py    # Atomic state updates, resume, single-scene retry
│   │   ├── hardware.py         # Tự động nhận diện GPU (VRAM, CUDA, Apple Silicon, CPU)
│   │   └── cache.py            # Hashing prompt/model/seed để reuse asset
│   │
│   ├── providers/              # Abstract Interfaces & Concrete Implementations
│   │   ├── __init__.py
│   │   ├── llm/
│   │   │   ├── base.py         # LLMProvider abstract class
│   │   │   ├── gemini.py       # Google Gemini provider (JSON Schema mode)
│   │   │   ├── openai.py       # OpenAI GPT-4o provider
│   │   │   └── parser.py       # Robust JSON extractor & repair
│   │   │
│   │   ├── tts/
│   │   │   ├── base.py         # TTSProvider abstract class
│   │   │   ├── edge.py         # Microsoft Edge Neural TTS (vi-VN-HoaiMy/NamMinh)
│   │   │   └── piper.py        # Piper TTS local fallback
│   │   │
│   │   ├── image/
│   │   │   ├── base.py         # ImageGenerationProvider
│   │   │   ├── flux.py         # FLUX.1 (ComfyUI / Diffusers / Cloud API)
│   │   │   └── cloud.py        # Fal.ai / Replicate / Together Image API
│   │   │
│   │   └── video/
│   │       ├── base.py         # GenerativeVideoProvider
│   │       ├── wan.py          # Wan 2.1 (T2V & I2V)
│   │       ├── ltx.py          # LTX-Video (T2V & I2V)
│   │       ├── comfyui.py      # ComfyUI WebSocket/HTTP Client wrapper
│   │       └── cloud.py        # Cloud Video API (Fal.ai / Replicate Wan2.1/LTX)
│   │
│   ├── engines/                # Audio, Subtitle & Video Composition Engines
│   │   ├── __init__.py
│   │   ├── timeline.py         # Audio-first timeline calculator
│   │   ├── subtitle.py         # ASS & SRT generator với Karaoke highlight
│   │   ├── audio.py            # BGM ducking, volume normalization, SFX
│   │   └── composer.py         # FFmpeg orchestration (Concat, 9:16 scale, Pad, Burn Sub)
│   │
│   ├── qc/                     # Quality Control Validator
│   │   ├── __init__.py
│   │   └── validator.py        # Kiểm tra MP4 valid, resolution, duration, audio track
│   │
│   └── factory.py              # Main Orchestrator điều phối toàn bộ pipeline
│
├── assets/                     # Royalty-free local assets (BGM, SFX, Fonts)
│   ├── fonts/                  # Font hỗ trợ tiếng Việt có dấu đầy đủ (Montserrat, BeVietnamPro)
│   ├── music/                  # Nhạc nền miễn phí bản quyền (Cinematic, ambient, upbeat)
│   └── sfx/                    # Hiệu ứng âm thanh cơ bản (whoosh, hit, ocean, rain)
│
├── outputs/                    # Thư mục lưu các dự án video được tạo ra
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 2. Các Giai Đoạn Triển Khai (Roadmap)

### Giai Đoạn 1: Nền Tảng & Thiết Lập Cốt Lõi (Core Infrastructure)
1. Khởi tạo `pyproject.toml` và môi trường ảo Python.
2. Cài đặt các thư viện thiết yếu:
   - `pydantic>=2.7.0` (Data validation)
   - `edge-tts>=6.1.12` (Vietnamese Neural TTS miễn phí)
   - `google-genai` / `google-generativeai` / `openai` (Content brain)
   - `rich` (CLI terminal dashboard)
   - `aiohttp` / `requests` (API clients)
   - `imageio-ffmpeg` (Tự động cung cấp FFmpeg binary nếu máy trạm chưa cài FFmpeg toàn cục)
3. Xây dựng module nhận diện phần cứng (`HardwareDetector`) để tự động chọn cấu hình tối ưu.

### Giai Đoạn 2: Content Brain & Voice Engine (Kịch bản & Giọng đọc tiếng Việt)
1. Xây dựng `RobustJSONParser`: Làm sạch chuỗi markdown, xử lý lỗi dấu ngoặc tiếng Việt và validate Pydantic.
2. Xây dựng `GeminiLLMProvider` & `OpenAILLMProvider`:
   - `research_topic()`: Tổng hợp sự thật thú vị, góc nhìn gây tò mò.
   - `generate_script()`: Viết kịch bản tiếng Việt có hook 3 giây đầu, phân cảnh nhịp nhàng.
   - `generate_storyboard()`: Chuyển kịch bản thành danh sách shot quay chi tiết (ánh sáng, góc máy, camera motion).
3. Xây dựng `EdgeTTSProvider`:
   - Tải file âm thanh WAV giọng đọc tiếng Việt chuẩn (`vi-VN-HoaiMyNeural` / `vi-VN-NamMinhNeural`).
   - Đọc chính xác độ dài file WAV thực tế bằng thư viện `wave`.

### Giai Đoạn 3: Timeline & Subtitle Engine (Audio-First Sync & ASS Karaoke)
1. Xây dựng `TimelineEngine`:
   - Phân bổ thời lượng chính xác cho từng cảnh dựa trên giọng đọc thực tế.
2. Xây dựng `SubtitleEngine`:
   - Sinh file `subtitle.srt` truyền thống.
   - Sinh file `subtitle.ass` có hiệu ứng Karaoke Highlight (`\k`), phông chữ đẹp không lỗi dấu tiếng Việt, tự động căn vào vùng an toàn (Safe Zone) của TikTok/Shorts.

### Giai Đoạn 4: Generative Visual Engine (AI Image -> Image-to-Video)
1. Xây dựng `ImageGenerationProvider`:
   - Tạo ảnh tham chiếu `reference.png` cho từng scene với phong cách từ `VisualStyleBible`.
2. Xây dựng `GenerativeVideoProvider`:
   - Kết nối tới Cloud API (Fal.ai / Replicate Wan2.1 / LTX) hoặc Local ComfyUI.
   - Chuyển `reference.png` + `video_prompt` thành `video.mp4` chuyển động mượt mà.
3. Cơ chế Cache:
   - Lưu mã băm SHA256 của `(model, prompt, seed, reference)` để không tốn chi phí và thời gian sinh lại nếu nội dung không đổi.

### Giai Đoạn 5: Audio Mixing & FFmpeg Video Composer
1. Xây dựng `AudioEngine`:
   - Ghép giọng đọc Narration + Nhạc nền BGM.
   - Áp dụng kỹ thuật Audio Ducking: Tự động hạ âm lượng BGM xuống 18% khi có giọng nói và đẩy lên khi nghỉ câu.
2. Xây dựng `ComposerEngine`:
   - Ghép nối tuần tự các cảnh video độc lập `scene_001.mp4`, `scene_002.mp4`...
   - Chuẩn hóa độ phân giải dọc 1080x1920 (TikTok/Reels/Shorts) hoặc ngang 1920x1080 (YouTube).
   - Ghép phụ đề ASS trực tiếp vào video.
   - Xuất file hoàn thiện `master.mp4` và các biến thể theo nền tảng.

### Giai Đoạn 6: Quản Lý Dự Án, Phục Hồi Lỗi & Thử Lại (Resume / Retry)
1. Xây dựng `ProjectStateManager`:
   - Ghi nhận trạng thái từng cảnh vào `projects/{project_id}/project.json`.
   - Nếu cảnh 7 bị lỗi mạng hoặc timeout, chạy lại lệnh sẽ tự động nhận diện các cảnh 1-6 đã hoàn thành và chỉ tiếp tục từ cảnh 7.
2. Hỗ trợ lệnh tái tạo từng cảnh độc lập:
   - `python -m app regenerate --project-id ... --scene 4`

### Giai Đoạn 7: CLI Interface & Acceptance Test
1. Xây dựng giao diện dòng lệnh bằng `rich`:
   ```bash
   python -m app generate \
       --topic "Nếu Mặt Trăng biến mất thì chuyện gì sẽ xảy ra?" \
       --duration 60 \
       --platform tiktok \
       --language vi
   ```
2. Thực thi kiểm thử chấp nhận (Acceptance Test):
   - Chạy toàn bộ quy trình, kiểm tra tính hợp lệ của video đầu ra trong `outputs/{project_id}/final.mp4`.
   - Đảm bảo 100% visual do AI sinh ra, có tiếng Việt, có phụ đề, sẵn sàng đăng tải.
