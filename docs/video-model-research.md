# Nghiên Cứu Chuyên Sâu Các Mô Hình Generative Video (Video Model Research)

> **Tài liệu thẩm định kỹ thuật:** Vietnamese Generative Video Factory  
> **Tác giả:** Principal AI Engineer & Generative Video Architect  
> **Mục tiêu:** Đánh giá toàn diện các mô hình Text-to-Video (T2V) và Image-to-Video (I2V) mã nguồn mở và nền tảng orchestration để làm nền tảng cho pipeline AI video tự động 100%.

---

## 1. Tổng Quan & Tiêu Chí Đánh Giá

Hệ thống **Vietnamese Generative Video Factory** đặt ra nguyên tắc cốt lõi: **GENERATE, DON'T DOWNLOAD**. Không dùng stock footage, không scrap video bên ngoài. Để sản xuất video hoàn chỉnh (ví dụ 60 giây gồm 8–12 cảnh độc lập, định dạng dọc 9:16 cho TikTok/Reels/Shorts hoặc ngang 16:9 cho YouTube), các mô hình visual sinh ra phải đáp ứng:

1. **Chất lượng hình ảnh & độ ổn định chuyển động (Motion & Visual Fidelity)**: Không bị méo biến dạng (morphing), không nhấp nháy (flickering).
2. **Hỗ trợ khung hình dọc (Vertical 9:16 Aspect Ratio)**: 1080x1920 (hoặc tối thiểu 720x1280 trước khi upscale).
3. **Chi phí phần cứng & Bộ nhớ VRAM (Hardware & VRAM Footprint)**: Khả năng chạy trên GPU tiêu dùng (8GB - 16GB VRAM) thông qua quantization (FP8, GGUF) và offloading, cũng như quy mô trên Cloud GPU (A100, H100, L40S).
4. **Hỗ trợ Image-to-Video (I2V)**: Chìa khóa cho **Character Consistency** (Nhân vật đồng nhất qua Character Bible -> AI Image -> I2V).
5. **Giấy phép bản quyền (License & Commercial Restrictions)**: Khả năng thương mại hóa hợp pháp.
6. **Hệ sinh thái tích hợp (Diffusers & ComfyUI API)**: Dễ dàng điều khiển bằng Python backend mà không bị khóa chặt vào một giao diện đồ họa thủ công.

---

## 2. Bảng So Sánh Chi Tiết Các Model Hàng Đầu (Benchmark Matrix)

| Tiêu chí | **Wan 2.1 (Alibaba)** | **LTX-Video (Lightricks)** | **HunyuanVideo (Tencent)** | **CogVideoX-5B (THUDM)** | **Stable Video Diffusion (SVD-XT)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Kiến trúc cốt lõi** | 3D DiT + Flow Matching + Cross-Attention | 3D DiT + Spatial-Temporal Causal VAE | Dual-stream DiT (MLLM + CLIP text encoder) | 3D VAE + Expert DiT | Temporal UNet (SD 2.1 Latent) |
| **Kích thước tham số** | **1.3B** (nhẹ) & **14B** (SOTA) | **~2B** parameters | **13B** parameters | **2B** & **5B** parameters | **~1.5B** parameters |
| **Giấy phép (License)** | **Apache 2.0** (Hoàn toàn mở, thương mại tự do) | **LTX Community License** (Miễn phí nếu doanh thu < 10M$ USD) | **Tencent Hunyuan Community License** (Miễn phí có điều kiện) | **Apache 2.0** (Thương mại tự do) | **Stability AI Community License** (Hạn chế doanh thu >1M$) |
| **Khả năng T2V** | Rất mạnh (1.3B & 14B) | Tốt, chuyển động nhanh | Xuất sắc (Cinematic) | Tốt | Không hỗ trợ chính thức T2V |
| **Khả năng I2V** | **Xuất sắc** (14B-I2V-720P / 480P) | Hỗ trợ tốt (v0.9.5+) | Hỗ trợ qua HunyuanVideo-1.5 | Hỗ trợ CogVideoX-5B-I2V | Khá (chuẩn mực cũ, dễ trôi dạt) |
| **Độ phân giải & Tỉ lệ 9:16** | Hỗ trợ native 720x1280 & 480x854 | Hỗ trợ native 512x768 & 768x512 | Native 720x1280 (24fps) | Hỗ trợ 720x480 / 480x720 | Native 576x1024 |
| **VRAM tối thiểu (Quantized)** | 1.3B: **8GB** (FP8/GGUF)<br>14B: **12-16GB** (GGUF/FP8) | **6-8GB** (FP8 + CPU offload) | **12-16GB** (FP8 + Block Offload) | **10-12GB** (INT8/FP8) | **8-10GB** |
| **VRAM tiêu chuẩn (FP16/BF16)**| 1.3B: 12GB<br>14B: 32-48GB | 12-16GB | 48-60GB | 16-24GB | 12-16GB |
| **Tốc độ sinh (RTX 4090)** | 1.3B: ~15-25s / shot<br>14B: ~60-90s / shot | **~5-12s / shot** (Cực nhanh) | ~90-150s / shot | ~40-60s / shot | ~20-30s / shot |
| **Độ mượt & Chuyển động** | Rất tự nhiên, biên độ chuyển động lớn | Nhanh, đôi khi quá đà nếu prompt mạnh | Cinematic, camera mượt mà | Ổn định, chuyển động vừa phải | Chuyển động vi mô (micro-motion) |
| **Character Consistency** | Rất cao khi dùng I2V 14B | Khá (cần seed cố định & reference) | Cao | Khá | Dễ biến đổi khuôn mặt |
| **ComfyUI Support** | Hoàn toàn hỗ trợ (Native & Wrapper) | Hoàn toàn hỗ trợ (ComfyUI-LTXVideo) | Hoàn toàn hỗ trợ (ComfyUI-HunyuanVideo) | Hoàn toàn hỗ trợ | Native node tích hợp sẵn |
| **Diffusers Support** | Có trong Hugging Face Diffusers | Có trong Diffusers (`LTXPipeline`) | Có (`HunyuanVideoPipeline`) | Có (`CogVideoXPipeline`) | Có (`StableVideoDiffusionPipeline`)|
| **Khả năng chạy Windows** | Tốt (với PyTorch 2.4+ / ComfyUI) | Tốt | Tốt (cần cẩn thận swap RAM) | Tốt | Tốt |

---

## 3. Phân Tích Chuyên Sâu Từng Ứng Cử Viên

### 3.1. Wan 2.1 (Alibaba Cloud) — Lựa Chọn Chiến Lược Cho Production
- **Điểm mạnh vượt trội:**
  - Giấy phép **Apache 2.0**: Cho phép sử dụng thương mại, đóng gói SaaS, chỉnh sửa mô hình không lo rủi ro pháp lý.
  - Phân tầng mô hình hoàn hảo: Bản **1.3B** cực nhẹ cho local/mid-range testing và bản **14B** cho chất lượng điện ảnh sánh ngang Sora hay Runway Gen-3.
  - Khả năng **Image-to-Video (I2V)** được huấn luyện chuyên biệt (không phải add-on chắp vá), cho phép giữ nguyên vẹn chi tiết khuôn mặt nhân vật từ ảnh tham chiếu (Character Bible).
  - Tỉ lệ khung hình linh hoạt: Cho phép render trực tiếp 720x1280 (9:16 dọc) mà không bị crop méo.
- **Điểm cần lưu ý:**
  - Bản 14B cần ít nhất 16GB VRAM (khi dùng GGUF Q4_K_M hoặc FP8) và tối thiểu 32GB RAM hệ thống để offload text encoder.

### 3.2. LTX-Video / LTX-2 (Lightricks) — Lựa Chọn Tối Ưu Tốc Độ & VRAM Thấp
- **Điểm mạnh:**
  - Tốc độ sinh video nhanh nhất hiện nay trong dòng DiT mở (nhờ kiến trúc nén VAE không gian 32x và thời gian 8x).
  - Bản 2B chạy mượt mà trên các GPU phổ thông như RTX 3060 12GB, RTX 4060 Ti 16GB, thậm chí 8GB khi bật CPU offload.
  - Hỗ trợ tốt độ phân giải dọc 512x768 trước khi qua upscaler/interpolator.
- **Hạn chế:**
  - Chi tiết vi mô khuôn mặt có thể bị mờ nếu chuyển động camera quá gắt.
  - Bản quyền giới hạn cho doanh nghiệp có doanh thu trên 10 triệu USD (phải mua license riêng).

### 3.3. HunyuanVideo (Tencent) — Cinematic Quality Đỉnh Cao
- **Điểm mạnh:**
  - Chất lượng điện ảnh hàng đầu hiện nay trong phân khúc mã nguồn mở. Khả năng hiểu prompt phức tạp nhờ LLM text encoder.
  - Ánh sáng, đổ bóng và vật lý chất lỏng/khói lửa rất chân thực.
- **Hạn chế:**
  - Mô hình 13B cực kỳ nặng. Bản FP16 ngốn 60GB VRAM.
  - Dù cộng đồng đã tạo bản FP8 và GGUF giúp hạ xuống 14-16GB VRAM, thời gian suy luận trên GPU phổ thông vẫn khá lâu (2-3 phút cho một đoạn 5 giây).
  - Giấy phép Tencent Community License đòi hỏi đăng ký nếu vượt ngưỡng người dùng.

### 3.4. Stable Video Diffusion (SVD / SVD-XT) — Mô Hình Tiền Nhiệm
- **Nhận định:**
  - Từng là tiêu chuẩn năm 2023-2024, nhưng hiện tại đã lỗi thời so với DiT thế hệ mới (Wan 2.1, LTX).
  - Chỉ tạo được clip ngắn 14-25 frame (2-3 giây), khó kiểm soát camera trajectory, chuyển động khuôn mặt dễ bị trôi và méo.
  - Chỉ nên dùng làm baseline fallback thử nghiệm nếu không có tài nguyên chạy DiT.

---

## 4. Hệ Thống Orchestration: ComfyUI vs Diffusers

Một video factory tự động hóa cần một backend thực thi video linh hoạt:

### Cách tiếp cận 1: Pure Diffusers Pipeline (Python In-Process)
- **Ưu điểm:**
  - Nhúng trực tiếp vào worker Python (FastAPI/Celery/ARQ).
  - Không cần duy trì thêm một process server trung gian.
  - Dễ debug luồng xử lý dữ liệu và tích hợp tensor hook.
- **Nhược điểm:**
  - Quản lý bộ nhớ VRAM khi chuyển đổi giữa Text Encoder, DiT và VAE đòi hỏi tự code cơ chế offloading/tiling phức tạp.
  - Cập nhật mô hình mới chậm hơn so với cộng đồng node ComfyUI.

### Cách tiếp cận 2: ComfyUI Headless Execution (qua WebSocket / REST API)
- **Ưu điểm:**
  - Tối ưu VRAM tốt nhất thế giới mã nguồn mở: Tự động dọn dẹp VRAM (memory garbage collection), block swapping, GGUF/bitsandbytes quantization tích hợp sẵn.
  - Đội ngũ cộng đồng cập nhật mô hình mới chỉ trong vòng 24-48 giờ sau khi paper/weights ra mắt.
  - Cho phép xuất luồng (workflow) dạng JSON API (`workflow_api.json`) và điều khiển hoàn toàn bằng Python script qua WebSocket.
- **Nhược điểm:**
  - Cần duy trì ComfyUI như một service daemon chạy nền (`python main.py --listen --headless`).

### Kết luận kiến trúc:
Xây dựng lớp trừu tượng `GenerativeVideoProvider` hỗ trợ **CẢ HAI**:
1. `ComfyUIProvider`: Kết nối tới ComfyUI instance (cục bộ hoặc trên server GPU từ xa qua WebSocket/REST).
2. `DiffusersProvider`: Chạy trực tiếp qua Hugging Face Diffusers trên node có GPU độc lập.
3. `CloudAPIProvider`: Kết nối tới các serverless endpoints (Fal.ai, Replicate, RunPod) khi máy chủ local không có GPU CUDA.

---

## 5. Kiến Trúc Pipeline Visual: Text-to-Image -> Image-to-Video (T2I -> I2V)

Để đảm bảo video có chất lượng cao nhất và nhân vật nhất quán, pipeline không phụ thuộc hoàn toàn vào Text-to-Video trực tiếp.

```
[Prompt + Character Bible + Style Bible]
                  │
                  ▼
         [AI Image Generator] ─── (FLUX.1-schnell / SDXL / Recraft / Imagen)
                  │
                  ▼
         scene_reference.png (Độ phân giải cao, bố cục chuẩn, nhân vật đúng tạo hình)
                  │
                  ▼
         [Image-to-Video Engine] ─── (Wan 2.1 I2V / LTX-Video I2V)
                  │
                  ▼
         scene_00X.mp4 (Chuyển động mượt mà, camera cinematic, nhân vật không biến dạng)
```

**Tại sao đây là giải pháp vượt trội?**
1. **Kiểm soát bố cục (Composition Control)**: Mô hình tạo ảnh tĩnh (như FLUX.1) có độ chi tiết và khả năng render chữ, chi tiết trang phục, ánh sáng vượt xa khả năng của mô hình T2V trực tiếp.
2. **Nhất quán nhân vật (Character Consistency)**: Nhờ có `reference_image.png`, mô hình I2V nhận điều kiện ảnh gốc (image latent conditioning) nên khuôn mặt và trang phục không bị hallucinate ngẫu nhiên giữa các cảnh.
3. **Tiết kiệm chi phí thử nghiệm**: Nếu prompt chưa ưng ý, chỉ cần re-generate ảnh tĩnh (mất 1-3 giây) thay vì phải generate lại cả đoạn video (mất 60-120 giây).

---

## 6. Lựa Chọn Tối Ưu Cho Từng Phân Cấp Phần Cứng

Xem chi tiết cấu hình tại `docs/hardware.md`. Tóm tắt phân bổ:
- **Low VRAM (6GB - 10GB)**: LTX-Video FP8 + CPU Offload hoặc Wan2.1-1.3B GGUF Q4. Fallback sang Cloud API Provider.
- **Mid-Range GPU (12GB - 16GB)**: Wan2.1-1.3B FP16 hoặc Wan2.1-14B GGUF Q4_K_M (qua ComfyUI), kết hợp FLUX.1-schnell FP8.
- **High-End GPU (24GB+)**: Wan2.1-14B FP8 native hoặc HunyuanVideo FP8, render native 720p 9:16.
- **Cloud / Serverless**: Wan2.1 14B / HunyuanVideo trên RunPod, Modal, Fal.ai API.
