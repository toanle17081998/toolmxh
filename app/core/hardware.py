import platform
import shutil
from typing import Dict, Any

class HardwareDetector:
    """Tự động kiểm tra năng lực phần cứng và đề xuất profile phù hợp."""

    @staticmethod
    def detect() -> Dict[str, Any]:
        info = {
            "os": platform.system(),
            "cpu": platform.processor(),
            "has_cuda": False,
            "gpu_name": None,
            "vram_gb": 0.0,
            "tier": "CLOUD_OR_API",
            "recommended_video_provider": "cloud"
        }

        try:
            import torch
            if torch.cuda.is_available():
                info["has_cuda"] = True
                info["gpu_name"] = torch.cuda.get_device_name(0)
                vram_bytes = torch.cuda.get_device_properties(0).total_memory
                info["vram_gb"] = round(vram_bytes / (1024 ** 3), 2)
                
                if info["vram_gb"] >= 22.0:
                    info["tier"] = "HIGH_END_GPU"
                    info["recommended_video_provider"] = "wan_14b"
                elif info["vram_gb"] >= 11.0:
                    info["tier"] = "MID_RANGE_GPU"
                    info["recommended_video_provider"] = "wan_1.3b_or_ltx"
                else:
                    info["tier"] = "LOW_VRAM"
                    info["recommended_video_provider"] = "ltx_fp8"
            else:
                info["tier"] = "LOW_OR_NO_CUDA"
                info["recommended_video_provider"] = "cloud"
        except ImportError:
            info["tier"] = "NO_TORCH"
            info["recommended_video_provider"] = "cloud"

        return info

hardware_info = HardwareDetector.detect()
