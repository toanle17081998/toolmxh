# Báo Cáo Nghiên Cứu Toàn Diện Hệ Thống (Comprehensive Technology Research)

> **Dự án:** Vietnamese Generative Video Factory  
> **Kiến trúc sư:** Principal AI Engineer & Generative Video Architect

---

## 1. Nghiên Cứu Video Generation Models
*(Chi tiết benchmark và so sánh xem tại [docs/video-model-research.md](file:///d:/workspace/toolmxh/docs/video-model-research.md))*

### Tóm tắt cốt lõi:
- **Wan 2.1 (Alibaba)**: Model mạnh nhất hiện nay cho I2V và T2V, mã nguồn mở Apache 2.0. Hai kích cỡ tham số 1.3B (chạy được trên máy 8-12GB VRAM) và 14B (chất lượng SOTA điện ảnh).
- **LTX-Video (Lightricks)**: Mô hình DiT tốc độ cao nhất, suy luận cực nhanh (5-10 giây/shot trên RTX 4090), VRAM thấp (6-8GB FP8), thích hợp dựng mẫu nhanh.
- **HunyuanVideo (Tencent)**: Chất lượng cinematic đỉnh cao, cần GPU VRAM lớn (16-24GB+ FP8).
- **Chiến lược:** Hỗ trợ chuẩn trừu tượng `GenerativeVideoProvider` đa nhà cung cấp (Local ComfyUI, Local Diffusers, và Cloud Serverless API như Fal.ai / Replicate) để factory có thể hoạt động trên mọi loại máy tính.

---

## 2. Nghiên Cứu Vietnamese TTS (Text-to-Speech)

Hệ thống tuân thủ nguyên tắc: **Audio-First Timeline** (Giọng đọc quyết định thời lượng chính xác của từng cảnh). Do đó, TTS tiếng Việt phải tự nhiên, đọc đúng dấu câu, ngắt nghỉ nhịp nhàng và có thể đo đạc chính xác thời lượng file audio WAV.

### 2.1. Đánh giá các giải pháp TTS tiếng Việt:

| Giải pháp | Kiểu vận hành | Giọng đọc & Chất lượng | Chi phí | Thời gian phản hồi | Độ ổn định |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Edge-TTS (Microsoft Neural)** | Python Async client (miễn phí, không cần GPU) | `vi-VN-HoaiMyNeural` (Nữ), `vi-VN-NamMinhNeural` (Nam). Giọng cực kỳ tự nhiên, ngữ điệu chuẩn tiếng Việt. | **0 VNĐ / Free** | ~0.5s - 1.5s / đoạn | Rất cao, hỗ trợ chỉnh `rate`, `pitch`, `volume` |
| **Piper TTS (Local ONNX)** | Chạy offline 100% trên CPU | `vi_VN-25hours-single`, `vi_VN-vivos-x_low`. Giọng nghe rõ nhưng hơi đơn điệu (robotic nhẹ). | **0 VNĐ** | ~0.2s / đoạn | Tuyệt đối an toàn khi mất mạng |
| **FPT.AI / Vbee** | Cloud API Việt Nam | Nhiều chất giọng vùng miền (Bắc, Trung, Nam), chất lượng studio | Có phí theo ký tự | Phụ thuộc mạng | Thương mại tốt |
| **OpenAI TTS (`tts-1`)** | Cloud API toàn cầu | Giọng đa ngôn ngữ (Alloy, Echo, Onyx), nhưng ngữ điệu tiếng Việt bị cứng và đôi khi sai trọng âm | 0.015$ / 1k ký tự | 1-2s | Ổn định |

### 2.2. Lựa chọn thiết kế cho Factory:
- **Default Provider (MVP & Production):** **Edge-TTS** (`vi-VN-HoaiMyNeural` và `vi-VN-NamMinhNeural`). Lý do: Giọng tiếng Việt chân thực nhất hiện nay trong các giải pháp không mất phí bản quyền, không phụ thuộc VRAM GPU, tốc độ cực nhanh, có thể trích xuất timestamp từ word boundary metadata.
- **Fallback Local:** **Piper TTS** hoặc **gTTS** khi chạy môi trường isolated/air-gapped.
- **Commercial Option:** Khung giao tiếp chuẩn `TTSProvider` cho phép cắm khóa API FPT.AI hoặc Vbee khi cần giọng đặc trưng vùng miền.

---

## 3. Nghiên Cứu Content Brain: LLM Structured Script & Vietnamese Storyboarding

### 3.1. Nhà cung cấp LLM:
Factory cần một Content Brain có khả năng:
1. Nghiên cứu chủ đề (Research depth).
2. Viết kịch bản tiếng Việt hấp dẫn, có hook mạnh giữ chân người xem trong 3 giây đầu (TikTok/Reels/Shorts algorithm).
3. Phân rã cảnh (Scene Breakdown) thành mô tả hình ảnh cinematic (`image_prompt`, `video_prompt`, `camera_motion`, `lighting`, `continuity_reference`).
4. Trả về đúng định dạng **Strict JSON Schema** và validate bằng **Pydantic**.

### 3.2. Abstraction `LLMProvider`:
- **Google Gemini (Gemini 2.5 Flash / Pro)**: Xử lý context dài, hỗ trợ native JSON mode schema, chi phí thấp, tiếng Việt phong phú, tốc độ sinh cực nhanh.
- **OpenAI (GPT-4o / GPT-4o-mini)**: Reasoning logic chặt chẽ, hỗ trợ `response_format: { type: "json_object" }` hoặc Structured Outputs với Pydantic schema.
- **Tự động sửa lỗi (JSON Repair / Retry)**: Tích hợp middleware tự động sanitize markdown code block (````json ... ````), tự động dùng thuật toán regex extraction hoặc gọi retry kèm error feedback nếu payload bị lỗi định dạng.

---

## 4. Nghiên Cứu Image Generation (Visual Anchor)

Để phục vụ quy trình:
$$\text{Text Prompt} \xrightarrow{} \text{AI Image} \xrightarrow{} \text{Image-to-Video}$$

### 4.1. Lựa chọn mô hình Image Generator:
- **FLUX.1 [schnell] / [dev] (Black Forest Labs)**:
  - Hiện là SOTA về chất lượng hình ảnh, khả năng theo sát prompt (prompt adherence), render chi tiết ngón tay, mắt, ánh sáng, góc camera chuẩn điện ảnh.
  - Bản `schnell` (4 steps) chạy cực nhanh trên GPU tiêu dùng (với FP8/NF4 qua ComfyUI hoặc Diffusers) hoặc qua Fal.ai/Together API chỉ mất ~1 giây.
- **SDXL (Stable Diffusion XL)**:
  - Lựa chọn cổ điển với hệ sinh thái LoRA phong phú (Anime, Cinematic, Cyberpunk, Photorealism).
  - VRAM nhẹ (6-8GB VRAM).
- **Recraft / Ideogram / Midjourney API (qua proxy/API)**:
  - Cho chất lượng đồ họa và nghệ thuật cao nếu cấu hình Cloud Provider.

---

## 5. Nghiên Cứu Subtitle Engine & ASS Karaoke Highlight

Để tối ưu cho định dạng video ngắn trên TikTok, YouTube Shorts, Facebook Reels:
- Subtitle dạng **ASS (Advanced SubStation Alpha)** vượt trội hoàn toàn so với SRT thông thường vì hỗ trợ:
  1. **Word-by-word highlight (Karaoke effect `\k`)**: Làm nổi bật từng từ khi người đọc nói tới.
  2. **Font styling, Border, Shadow, Box Background**: Đảm bảo đọc rõ trên mọi nền video sáng hoặc tối.
  3. **Safe Zone Constraints**: Tự động né vùng giao diện tương tác của TikTok (thanh bên phải, mô tả bên dưới) và YouTube Shorts.
- **Tạo Subtitle tự động:**
  - Từ timestamp thực của Edge-TTS / Whisper alignment, ánh xạ chính xác đến từng từ (`start_time`, `end_time`).
  - Xuất song song cả `subtitle.srt` (phổ thông) và `subtitle.ass` (chuẩn TikTok motion graphic).

---

## 6. Nghiên Cứu Audio Mixing, Ducking & FFmpeg Video Composition

### 6.1. Audio Ducking tự động:
- Khi có giọng thuyết minh (Narration), nhạc nền (BGM) phải tự động giảm âm lượng xuống 15-20% (`sidechaincompress` hoặc `volume` envelope trong FFmpeg).
- Khi kết thúc câu nói hoặc khoảng nghỉ, nhạc nền tự động nâng âm lượng nhẹ nhàng (fade in/out).

### 6.2. FFmpeg Pipeline:
- Ghép nối các cảnh video độc lập (`scene_001.mp4`, `scene_002.mp4`...) không bị rách khung hình (glitch) bằng bộ lọc `concat`.
- Chuẩn hóa tỉ lệ hình ảnh: Đưa về chuẩn TikTok (1080x1920, 30fps/60fps, aspect ratio 9:16) hoặc YouTube Landscape (1920x1080, 16:9).
- Tích hợp bộ lọc phụ đề ASS trực tiếp vào video bằng `subtitles=subtitle.ass`.
- Kết xuất `master.mp4` chuẩn H.264/AAC với thông số tối ưu nén cho thuật toán mạng xã hội.
