# Đặc Tả Kỹ Thuật Phần Cứng & Phân Tầng Tài Nguyên (Hardware Specifications & Resource Tiers)

> **Dự án:** Vietnamese Generative Video Factory  
> **Kiến trúc sư:** Principal AI Engineer & Senior Python Architect

---

## 1. Thách Thức Kỹ Thuật Của Generative Video Trên Phần Cứng

Tạo video bằng Generative AI (đặc biệt là các mô hình Diffusion Transformer - DiT thế hệ mới) là tác vụ ngốn tài nguyên tính toán và bộ nhớ VRAM lớn nhất hiện nay trong lĩnh vực AI tiêu dùng. Khác với Text Generation (chỉ xử lý chuỗi 1D) hay Image Generation (xử lý tensor 2D), Video Generation xử lý **tensor không-thời gian 3D** (Spatial-Temporal 3D Latents: $B \times C \times T \times H \times W$).

Một đoạn video 5 giây ở độ phân giải 720p 24fps tương đương với 120 khung hình. Nếu không có kiến trúc phân tầng và tối ưu hóa bộ nhớ chặt chẽ, hệ thống sẽ lập tức rơi vào trạng thái:
- **CUDA Out of Memory (OOM)**
- **Windows Paging Thrashing** (khi driver NVIDIA trên Windows tự động hoán đổi VRAM tràn sang RAM hệ thống qua PCIe bus, làm suy giảm tốc độ suy luận từ 50 đến 100 lần, gây đơ toàn bộ máy tính).

---

## 2. Các Kỹ Thuật Tối Ưu Hóa Bộ Nhớ Bắt Buộc Trong Factory

Để vận hành ổn định trên các dòng GPU khác nhau, Factory tích hợp sẵn các kỹ thuật:

1. **Quantization (Lượng tử hóa FP8 / GGUF / NF4)**:
   - Thay vì chạy FP16/BF16 ngốn bộ nhớ, mô hình Transformer DiT được nén xuống **FP8 E4M3/E5M2** hoặc **GGUF Q4_K_M / Q8_0**, giúp giảm 50% - 70% dung lượng VRAM mà chất lượng hình ảnh gần như tương đương mắt thường.
2. **Sequential Model CPU Offloading**:
   - Khi Text Encoder (ví dụ T5-XXL hoặc MLLM Llama-3) hoàn thành nhiệm vụ sinh text embeddings, nó lập tức được chuyển từ VRAM sang RAM hệ thống trước khi mô hình DiT chính được nạp vào VRAM.
3. **Spatial & Temporal VAE Tiling**:
   - Bộ giải mã VAE 3D (giải mã latent thành pixel video) chia khung hình thành các ô lưới (tiles) nhỏ và giải mã tuần tự, tránh hiện tượng sập VRAM ở bước cuối cùng của pipeline.
4. **CUDA Cache Garbage Collection & Worker Isolation**:
   - Sau mỗi cảnh video sinh xong, worker giải phóng explicit cache (`torch.cuda.empty_cache()` và `gc.collect()`), ngăn chặn hiện tượng rò rỉ bộ nhớ (memory fragmentation).

---

## 3. Phân Tầng Phần Cứng & Đề Xuất Mô Hình (Hardware Matrix)

Dưới đây là 4 cấu hình phần cứng chuẩn và danh mục mô hình đề xuất cho từng phân khúc:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      HARDWARE RESOURCE TIERS                           │
├──────────────────┬──────────────────┬─────────────────┬────────────────┤
│    LOW VRAM      │   MID-RANGE GPU  │  HIGH-END GPU   │   CLOUD GPU    │
│   (6GB - 10GB)   │  (12GB - 16GB)   │     (24GB+)     │ (A100/H100/L40)│
├──────────────────┼──────────────────┼─────────────────┼────────────────┤
│ RTX 3060 6GB     │ RTX 3060 12GB    │ RTX 3090 24GB   │ RunPod         │
│ RTX 4050/4060 8G │ RTX 4070 12GB    │ RTX 4090 24GB   │ Modal Labs     │
│ Apple Silicon M  │ RTX 4060 Ti 16GB │ RTX 6000 Ada    │ Fal.ai API     │
└──────────────────┴──────────────────┴─────────────────┴────────────────┘
```

---

### Phân Cấp 1: LOW VRAM (6GB – 10GB VRAM)
- **Thiết bị tiêu biểu:** NVIDIA RTX 3060 6GB Laptop, RTX 4050 6GB, RTX 3070 8GB, RTX 4060 8GB.
- **Chiến lược sinh visual:**
  1. **Tạo ảnh tĩnh tham chiếu (T2I):** FLUX.1-schnell (quantized GGUF Q4/NF4) hoặc SDXL Turbo / Lightning (4-8 steps, FP16).
  2. **Tạo video (I2V / T2V):** 
     - **LTX-Video 2B (FP8 + CPU Offload)**: Độ phân giải 512x768 (9:16 dọc), 24-30 frames (~1.5 - 2s/shot), sau đó dùng FFmpeg/RIFE nội suy.
     - **Wan 2.1 1.3B (GGUF Q4_K_M)**: Độ phân giải 480x854 (480p dọc).
  3. **Chế độ Remote Fallback:** Tự động kích hoạt `CloudProvider` (Fal.ai / Replicate) nếu phát hiện VRAM < 6GB hoặc chỉ có card Intel/AMD không hỗ trợ CUDA.
- **Yêu cầu hệ thống:** RAM tối thiểu 16GB (khuyến nghị 32GB để offload model weights).

---

### Phân Cấp 2: MID-RANGE GPU (12GB – 16GB VRAM)
- **Thiết bị tiêu biểu:** NVIDIA RTX 3060 12GB, RTX 4070 / 4070 Super 12GB, RTX 4060 Ti 16GB, RTX 4070 Ti Super 16GB.
- **Chiến lược sinh visual:**
  1. **Tạo ảnh tĩnh tham chiếu (T2I):** FLUX.1-schnell (FP8) hoặc FLUX.1-dev (Q4_K_S) tạo ra ảnh gốc cực kỳ sắc nét ở độ phân giải 768x1360 hoặc 1080x1920.
  2. **Tạo video (I2V / T2V):**
     - **Wan 2.1 14B (GGUF Q4_K_M qua ComfyUI Node)**: Độ phân giải 480p hoặc 720p với dynamic offloading. Đạt chất lượng chuyển động và điện ảnh vượt trội.
     - **Wan 2.1 1.3B (FP16 Native)**: Chạy tốc độ cao cho các cảnh chuyển động đơn giản.
     - **LTX-Video 2B (FP16/BF16)**: Độ phân giải 720p mượt mà chỉ mất 8-12 giây một cảnh.
- **Yêu cầu hệ thống:** RAM 32GB DDR4/DDR5, ổ cứng NVMe SSD trống ít nhất 100GB lưu cache weights.

---

### Phân Cấp 3: HIGH-END GPU (24GB+ VRAM Độc Lập)
- **Thiết bị tiêu biểu:** NVIDIA GeForce RTX 3090 24GB, RTX 4090 24GB, RTX A5000 / A6000, RTX 6000 Ada.
- **Chiến lược sinh visual:**
  1. **Tạo ảnh tĩnh tham chiếu (T2I):** FLUX.1-dev full FP16 hoặc FLUX.1 Pro quality.
  2. **Tạo video (I2V / T2V):**
     - **Wan 2.1 14B (FP8 / BF16 I2V & T2V Native)**: Độ phân giải native 720x1280 (9:16) ở 24fps, thời lượng 4-6 giây mỗi shot.
     - **HunyuanVideo 13B (FP8 Native)**: Cho các dự án đòi hỏi phong cách điện ảnh tả thực (Cinematic Photorealism).
  3. **Khả năng concurrency:** Có thể xử lý 1 cảnh video trong khi đồng thời chạy pipeline TTS và chuẩn bị prompt cho cảnh tiếp theo.
- **Yêu cầu hệ thống:** CPU đa nhân (Intel Core i7/i9 13-14th gen hoặc AMD Ryzen 7/9 7000/9000), 64GB RAM, NVMe PCIe 4.0.

---

### Phân Cấp 4: CLOUD GPU & SERVERLESS API
- **Nền tảng tiêu biểu:** RunPod Serverless / Dedicated, Modal Labs, Fal.ai, Together AI, Replicate.
- **Chiến lược vận hành:**
  - Không cần đầu tư phần cứng đắt tiền tại văn phòng hoặc máy cá nhân.
  - Phù hợp nhất cho môi trường triển khai SaaS nhiều người dùng đồng thời (Multi-tenancy).
  - Tận dụng GPU NVIDIA A100 80GB, H100 80GB, L40S 48GB trên đám mây.
  - Chi phí cực rẻ theo pay-per-second: Sinh 1 scene video 5s mất khoảng 0.03$ - 0.08$ USD trên Fal.ai / RunPod.
  - Video Factory đóng vai trò là Orchestrator trung tâm quản lý logic, timeline, giọng đọc và ghép nối FFmpeg cục bộ hoặc container cloud.

---

## 4. Quản Lý GPU Worker Queue & Cơ Chế Chống Treo Máy (Deadlock Prevention)

Trong kiến trúc của Factory, tiến trình xử lý GPU được điều phối qua module `GPUWorkerPool`:
- `max_concurrent_gpu_jobs = 1` (đối với máy cá nhân có 1 GPU vật lý): Đảm bảo không bao giờ nạp đồng thời mô hình Image Gen và Video Gen cùng lúc.
- **Vòng đời tác vụ (Task Lifecycle):**
  1. `Acquire GPU Lock`
  2. `Clear PyTorch CUDA cache`
  3. `Load required model weights`
  4. `Execute inference (T2I hoặc I2V)`
  5. `Release weights / Offload to RAM`
  6. `Clear PyTorch CUDA cache`
  7. `Release GPU Lock`
  8. Trả kết quả artifact vào thư mục dự án `projects/{project_id}/scenes/{scene_id}/`.
