# Kiến Trúc Hệ Thống: Vietnamese Generative Video Factory
## (System Architecture & Multi-Agent Brainstorming Technical Specification)

> **Tác giả:** Principal AI Engineer, Generative Video Architect & Senior Python Architect  
> **Trạng thái thẩm định:** PEER-REVIEWED & APPROVED (Qua quy trình Multi-Agent Brainstorming)  
> **Nguyên tắc cốt lõi:** **GENERATE, DON'T DOWNLOAD** (100% Visual được sinh bởi AI).

---

## 1. Tuyên Ngôn Triết Lý Kiến Trúc (Core Architectural Principles)

1. **Sinh mới 100% (Zero Stock Footage / Zero Scraping):**
   - Không phụ thuộc vào Pexels, Pixabay, YouTube/TikTok scraping hay kho stock video của bên thứ ba. Mọi khung hình visual đều được sinh ra bởi các mô hình Generative AI (T2I -> I2V hoặc T2V).
2. **Audio-First Timeline (Giọng đọc định đoạt thời gian):**
   - Không suy đoán thời lượng cảnh bằng đếm số từ. Pipeline luôn chạy TTS tiếng Việt trước, đo chính xác thời lượng file audio WAV đến từng mili-giây, phân rã theo nhịp câu rồi mới yêu cầu Video Engine sinh đúng số frame tương ứng.
3. **Phân rã cảnh độc lập (Shot-by-Shot Decomposition):**
   - Không sinh video dài 60 giây trong một prompt duy nhất (hành vi này dẫn đến ảo giác, biến dạng và méo hình). Video 60 giây được chia thành 8–12 cảnh (scenes/shots), mỗi cảnh dài 4–8 giây, có camera movement và ánh sáng riêng biệt.
4. **Nhất quán nhân vật & Phong cách (Character & Style Bibles):**
   - Video có nhân vật xuất hiện nhiều lần được kiểm soát qua `CharacterBible` (Seed, DNA mô tả, ảnh tham chiếu `reference.png`).
   - Video có phong cách nghệ thuật đồng nhất qua `VisualStyleBible` được inject xuyên suốt mọi prompt.
5. **Khả năng Phục hồi & Thử lại nguyên tử (Atomic Resume & Single-Scene Retry):**
   - Mỗi cảnh video có thư mục và state riêng. Nếu cảnh 5 thất bại, chỉ cần retry cảnh 5. Không bao giờ chạy lại các cảnh đã sinh thành công.
6. **Kiến trúc trừu tượng (Provider Pattern Abstraction):**
   - Toàn bộ LLM, TTS, Image Gen, Video Gen đều nằm sau các abstract interface. Hệ thống hoạt động linh hoạt trên máy tính không có GPU (thông qua Cloud Provider / API) cho đến cụm máy trạm đa GPU (qua Local ComfyUI / Diffusers).

---

## 2. Máy Trạng Thái Của Pipeline (Pipeline State Machine)

Pipeline vận hành theo đồ thị có hướng (DAG), ghi nhận trạng thái liên tục vào `projects/{project_id}/project.json`:

```
   [ CREATED ]
        │
        ▼
   [ RESEARCH ]  ────────── (Nghiên cứu chủ đề, tổng hợp tư liệu hấp dẫn)
        │
        ▼
   [ SCRIPT ]    ────────── (Sinh kịch bản tiếng Việt cấu trúc JSON Pydantic)
        │
        ▼
  [ STORYBOARD ] ────────── (Phân rã thành danh sách shot quay chuẩn điện ảnh)
        │
        ▼
[ CHARACTER_GEN ] ───────── (Sinh ảnh chân dung gốc nếu có nhân vật chính)
        │
        ▼
 [ VOICE_GEN ]   ────────── (Sinh audio thuyết minh tiếng Việt chuẩn, WAV)
        │
        ▼
   [ TIMELINE ]  ────────── (Đo WAV thực tế, chia mốc thời gian từng scene)
        │
        ▼
[ VISUAL_GEN ]   ────────── (Tạo reference image -> Image-to-Video từng scene)
        │
        ▼
 [ AUDIO_MIX ]   ────────── (Trộn Narration + BGM Ducking + Sound Effects)
        │
        ▼
   [ SUBTITLE ]  ────────── (Tạo phụ đề SRT & ASS chuẩn karaoke highlight)
        │
        ▼
 [ COMPOSITING ] ────────── (FFmpeg render master.mp4, tiktok.mp4, youtube.mp4)
        │
        ▼
     [ QC ]      ────────── (Quality Control kiểm tra fps, resolution, bitrate)
        │
        ▼
  [ COMPLETED ]
```

---

## 3. Cấu Trúc Dữ Liệu & Pydantic Schemas

Toàn bộ thông tin trao đổi giữa các tầng trong hệ thống đều được ép kiểu chặt chẽ bằng Pydantic v2.

### 3.1. Kịch bản có cấu trúc (`StructuredScript`)
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class SceneScript(BaseModel):
    id: int = Field(description="Số thứ tự cảnh, bắt đầu từ 1")
    narration: str = Field(description="Lời thuyết minh tiếng Việt tự nhiên")
    visual_description: str = Field(description="Mô tả bối cảnh và diễn biến visual")
    estimated_duration: float = Field(default=5.0, description="Thời lượng ước tính (giây)")
    camera_motion: str = Field(description="Chuyển động máy quay (zoom in, pan left, orbit...)")
    transition: str = Field(default="cut", description="Hiệu ứng chuyển cảnh (cut, fade, dissolve)")
    sound_effect: Optional[str] = Field(None, description="Tên hiệu ứng âm thanh đi kèm")

class StructuredScript(BaseModel):
    topic: str
    title: str
    hook: str = Field(description="Câu mở đầu giật gân thu hút người xem trong 3s đầu")
    target_duration: int = Field(description="Thời lượng mục tiêu của video (giây)")
    language: str = Field(default="vi")
    scenes: List[SceneScript]
```

### 3.2. Bảng phân cảnh điện ảnh (`Storyboard`)
```python
class CharacterBible(BaseModel):
    character_id: str
    name: str
    gender: str
    age: int
    appearance: str
    clothing: str
    reference_image_path: Optional[str] = None
    seed: int = 42

class VisualStyleBible(BaseModel):
    style_name: str = "Cinematic Documentary"
    lighting: str = "dramatic volumetric lighting"
    color_palette: str = "deep teal and golden amber"
    lens: str = "35mm anamorphic lens"
    render_style: str = "photorealistic 8k, hyper-detailed, ray-traced"

class SceneStoryboard(BaseModel):
    scene_id: int
    narration: str
    actual_duration: float = 5.0
    subject: str
    environment: str
    lighting: str
    camera_angle: str
    camera_movement: str
    visual_style: str
    image_prompt: str
    video_prompt: str
    negative_prompt: str = "ugly, distorted, blurry, bad anatomy, text, watermark, low quality"
    transition: str = "cut"
    sound_effect: Optional[str] = None
    continuity_reference_scene: Optional[int] = None

class Storyboard(BaseModel):
    project_id: str
    visual_bible: VisualStyleBible
    characters: List[CharacterBible] = []
    scenes: List[SceneStoryboard]
```

---

## 4. Thiết Kế Các Tầng Provider (Provider Abstraction Layer)

### 4.1. `LLMProvider`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMProvider(ABC):
    @abstractmethod
    async def generate_json(self, prompt: str, schema: type[BaseModel], system_prompt: str = "") -> BaseModel:
        """Sinh dữ liệu tuân thủ nghiêm ngặt theo Pydantic schema với retry tự động."""
        pass

    @abstractmethod
    async def research_topic(self, topic: str) -> Dict[str, Any]:
        pass
```
- **Triển khai:** `GeminiLLMProvider` (Google Gemini 2.5 Flash), `OpenAILLMProvider` (GPT-4o), `LocalOllamaProvider`.

### 4.2. `TTSProvider`
```python
class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, output_path: str, voice: str = "vi-VN-HoaiMyNeural", speed: float = 1.0) -> float:
        """Sinh file WAV tiếng Việt và trả về thời lượng thực tế (giây)."""
        pass

    @abstractmethod
    async def get_word_timestamps(self, text: str, voice: str) -> List[Dict[str, Any]]:
        """Lấy mốc thời gian từng từ để render subtitle highlight karaoke."""
        pass
```
- **Triển khai:** `EdgeTTSProvider` (Mặc định không tốn chi phí, tự nhiên), `PiperTTSProvider` (Local CPU offline), `FPTAIProvider` (Studio commercial).

### 4.3. `ImageGenerationProvider`
```python
class ImageGenerationProvider(ABC):
    @abstractmethod
    async def generate_image(self, prompt: str, output_path: str, width: int = 1080, height: int = 1920, seed: int = -1, negative_prompt: str = "") -> str:
        pass
```
- **Triển khai:** `FluxSchnellProvider` (qua ComfyUI hoặc local Diffusers), `SDXLProvider`, `CloudImageProvider` (Fal.ai / Replicate).

### 4.4. `GenerativeVideoProvider`
```python
class GenerativeVideoProvider(ABC):
    @abstractmethod
    async def generate_image_to_video(self, image_path: str, prompt: str, output_path: str, duration_seconds: float, width: int, height: int, seed: int = -1) -> str:
        """Tạo video scene từ ảnh tham chiếu đảm bảo giữ đúng tạo hình nhân vật và môi trường."""
        pass

    @abstractmethod
    async def generate_text_to_video(self, prompt: str, output_path: str, duration_seconds: float, width: int, height: int, seed: int = -1) -> str:
        pass
```
- **Triển khai:** 
  - `WanVideoProvider` (Mô hình Wan 2.1 1.3B hoặc 14B qua ComfyUI Node/API).
  - `LTXVideoProvider` (Mô hình LTX-Video siêu tốc cho preview nhanh).
  - `HunyuanVideoProvider` (Mô hình HunyuanVideo cho các cảnh điện ảnh cinematic).
  - `CloudVideoProvider` (Fal.ai / Replicate Wan2.1 API khi chạy trên máy không có card NVIDIA CUDA).

---

## 5. Báo Cáo Thẩm Định Đa Tác Tử (Multi-Agent Brainstorming Review)

Tuân thủ nghiêm ngặt quy trình của skill `multi-agent-brainstorming`:
- **Primary Designer:** Principal AI Engineer & Generative Video Architect.
- **Skeptic / Challenger:** Kỹ sư kiểm thử tải và rủi ro.
- **Constraint Guardian:** Kỹ sư hệ thống và chuyên gia tài nguyên VRAM/Pháp lý.
- **User Advocate:** Đại diện người dùng và nhà sáng tạo nội dung.
- **Integrator / Arbiter:** Trọng tài quyết định phê duyệt.

### 5.1. Vòng 1: Phản Biện Của Skeptic / Challenger Agent
> *"Giả sử hệ thống này thất bại thảm hại khi đưa vào sản xuất thực tế. Vì sao?"*

1. **Vấn đề lệch pha độ dài video so với audio (Duration Mismatch):**  
   *Thách thức:* Các mô hình Generative Video (như LTX hay Wan) sinh video theo số lượng khung hình cố định (ví dụ 49 frames, 81 frames, tương ứng 2.0 giây hoặc 3.4 giây ở 24fps). Trong khi đó câu đọc tiếng Việt có thể dài 4.7 giây hoặc 6.2 giây. Nếu cứ render cố định, video sẽ bị thiếu hình (hết video trước khi đọc xong) hoặc bị đóng băng hình (freeze frame).
2. **Hiện tượng giật cục & vỡ hình giữa các cảnh ghép nối (Inter-scene Glitch):**  
   *Thách thức:* Khi ghép 10 file MP4 từ các lần sinh độc lập bằng FFmpeg `concat`, nếu khác biệt nhẹ về framerate, pixel format (yuv420p vs yuv444p), hoặc audio sample rate (44100Hz vs 48000Hz), video đầu ra sẽ bị mất tiếng, đen màn hình hoặc lệch âm thanh hình ảnh.
3. **Ảo giác JSON kịch bản (LLM Hallucination & Malformed JSON):**  
   *Thách thức:* Khi prompt tiếng Việt dài, LLM hay nhầm lẫn dấu ngoặc kép bên trong văn bản (ví dụ: `narration: "Bí ẩn "Tam giác quỷ" Bermuda..."`), khiến parser JSON thông thường bị crash.

### 5.2. Vòng 2: Ràng Buộc Của Constraint Guardian Agent
> *"Những giới hạn phi chức năng nào đang bị đe dọa?"*

1. **Ràng buộc phần cứng trên máy tính người dùng (Hardware Reality):**  
   *Thực tế kiểm tra:* Máy trạm hiện tại đang chạy **Intel UHD Graphics 770** (không có card NVIDIA rời) và **FFmpeg chưa được cài đặt trong PATH**. Nếu hệ thống chỉ hỗ trợ duy nhất mô hình local CUDA 24GB VRAM thì sẽ sập ngay lập tức trên máy của người dùng.
   *Yêu cầu bắt buộc:* Phải có kiến trúc đa chế độ: Hỗ trợ tự động phát hiện phần cứng (`HardwareDetector`), kích hoạt `CloudProvider` (qua API key) hoặc chạy với video sinh từ API visual thực tế, và tự động tải hoặc hướng dẫn cấu hình FFmpeg binary.
2. **Ràng buộc bản quyền thương mại (Commercial Legality):**  
   *Yêu cầu:* Tuyệt đối không dùng các mô hình hạn chế thương mại hoặc đòi hỏi đóng phí khi đạt quy mô doanh nghiệp mà không có cảnh báo. Ưu tiên **Wan 2.1 (Apache 2.0)** vì giấy phép hoàn toàn tự do.

### 5.3. Vòng 3: Tiếng Nói Của User Advocate Agent
> *"Trải nghiệm người dùng thực tế sẽ khó chịu ở điểm nào?"*

1. **Tâm lý chờ đợi mù mờ (Black-box Waiting):**  
   *Vấn đề:* Sinh 10 cảnh video có thể mất từ 5 đến 15 phút. Nếu người dùng chỉ nhìn thấy một con trỏ nhấp nháy trên terminal mà không biết đang ở scene nào, tỷ lệ họ nhấn `Ctrl+C` hủy lệnh là 90%.
   *Yêu cầu:* Cung cấp tiến trình trực quan dạng bảng (Rich Terminal Console hoặc Web UI live status): Hiển thị rõ: *Scene 1/10 Done [✓], Scene 2/10 Generating (45%)...*
2. **Khả năng chỉnh sửa từng phần (Granular Regenerate):**  
   *Vấn đề:* Video 60s hoàn thành, người dùng rất ưng ý 9 cảnh nhưng cảnh 4 nhân vật bị xấu hoặc sai góc máy. Người dùng không muốn mất tiền và thời gian sinh lại từ đầu.
   *Yêu cầu:* Cung cấp lệnh CLI và giao diện `regenerate scene --project-id ... --scene-id 4`.

### 5.4. Vòng 4: Tích Hợp & Phán Quyết Trọng Tài (Integrator / Arbiter Resolution & Decision Log)

Trọng tài kỹ thuật (Integrator / Arbiter) chính thức ban hành phán quyết cho các vấn đề:

| Mã Quyết Định | Vấn Đề Gốc | Phán Quyết Kỹ Thuật (Resolution) | Lý Do & Thiết Kế Áp Dụng |
| :--- | :--- | :--- | :--- |
| **DEC-001** | Duration Mismatch (Audio vs Video) | **CHẤP THUẬN GIẢI PHÁP LẶP VÒNG & KÉO DÀI (Time-Stretch / Looping / Motion Extender)** | Video Engine sinh shot gốc 4-5s. Nếu audio dài hơn, FFmpeg áp dụng bộ lọc mượt mà: kết hợp motion interpolation hoặc loop ping-pong/fade cut tự nhiên, tuyệt đối không để video bị đen hoặc dừng hình giật cục. |
| **DEC-002** | FFmpeg Missing & Intel iGPU Local Reality | **CHẤP THUẬN CƠ CHẾ N-TIER HYBRID PROVIDER & AUTO-FFMPEG** | 1. Tự động kiểm tra GPU: Nếu có CUDA >= 12GB -> Mở tùy chọn Local Wan/LTX. Nếu không có CUDA -> Ưu tiên Cloud Video Engine (Fal.ai / Replicate) hoặc ComfyUI Remote Server.<br>2. Cung cấp tiện ích kiểm tra và fallback FFmpeg (hỗ trợ `imageio-ffmpeg` hoặc hướng dẫn đường dẫn nhị phân tĩnh). |
| **DEC-003** | JSON Repair & Sanitization | **CHẤP THUẬN PYDANTIC + REGEX JSON EXTRACTOR & FEEDBACK RETRY** | Tạo module `RobustJSONParser`: Làm sạch markdown code block, sửa lỗi nháy kép lồng nhau trong tiếng Việt, tự động retry với lỗi parse cụ thể tối đa 3 lần. |
| **DEC-004** | Atomic State & Granular Regeneration | **CHẤP THUẬN PROJECT STATE MANAGER THEO SCENE** | Lưu trạng thái theo từng file `scenes/{scene_id}/prompt.json`, `reference.png`, `video.mp4`. Cung cấp phương thức `factory.regenerate_scene(scene_id)` mà không chạm vào các cảnh khác. |
| **DEC-005** | Rich Real-time Feedback | **CHẤP THUẬN RICH CONSOLE LOGGING** | Áp dụng thư viện `rich` để hiển thị Dashboard trạng thái từng cảnh trong quá trình chạy. |

### 5.5. Kết Luận Thẩm Định Cuối Cùng (Final Disposition)
- **Kết quả:** **`APPROVED`** (ĐÃ PHÊ DUYỆT CHÍNH THỨC).
- **Lý do:** Thiết kế đã giải quyết triệt để các rủi ro về VRAM, sự tương thích phần cứng máy trạm, hiện tượng lệch pha âm thanh hình ảnh, tính nhất quán của nhân vật và bảo vệ quyền kiểm soát của người dùng.
