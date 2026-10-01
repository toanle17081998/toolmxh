import sys
import asyncio
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.config import settings
from app.factory import VietnameseVideoFactory
from app.core.hardware import hardware_info
from app.core.state_manager import ProjectStateManager
from app.models.project import SceneStatus

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True, legacy_windows=False)

def print_banner():
    banner = """
    ==================================================================
                 VIETNAMESE GENERATIVE VIDEO FACTORY              
        San Xuat Video AI 100% Tu Dong - Generate, Don't Download 
    ==================================================================
    """
    console.print(Panel(banner, style="bold cyan"))

def cmd_hardware():
    table = Table(title="Thông Tin Phần Cứng & Đề Xuất Mô Hình AI")
    table.add_column("Thuộc tính", style="cyan")
    table.add_column("Giá trị", style="green")
    for k, v in hardware_info.items():
        table.add_row(str(k), str(v))
    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Vietnamese Generative Video Factory CLI")
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # Command: generate
    gen_parser = subparsers.add_parser("generate", help="Sinh video hoàn chỉnh từ chủ đề")
    gen_parser.add_argument("--topic", type=str, required=True, help="Chủ đề của video")
    gen_parser.add_argument("--duration", type=int, default=60, help="Thời lượng mong muốn (giây)")
    gen_parser.add_argument("--platform", type=str, default="tiktok", choices=["tiktok", "shorts", "reels", "youtube"])
    gen_parser.add_argument("--language", type=str, default="vi", help="Ngôn ngữ thuyết minh (mặc định vi)")
    gen_parser.add_argument("--project-id", type=str, default=None, help="Mã dự án (nếu muốn đặt trước)")

    # Command: regenerate
    regen_parser = subparsers.add_parser("regenerate", help="Tái tạo một scene cụ thể")
    regen_parser.add_argument("--project-id", type=str, required=True, help="Mã dự án")
    regen_parser.add_argument("--scene", type=int, required=True, help="Số thứ tự scene cần tạo lại")

    # Command: hardware
    subparsers.add_parser("hardware", help="Kiểm tra cấu hình phần cứng")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    print_banner()

    if args.command == "hardware":
        cmd_hardware()
    elif args.command == "generate":
        factory = VietnameseVideoFactory(console_output=True)
        result = asyncio.run(factory.generate_video(
            topic=args.topic,
            duration=args.duration,
            platform=args.platform,
            language=args.language,
            project_id=args.project_id
        ))
        console.print(Panel(f"[bold green]Video đã sẵn sàng tại:[/bold green]\n{result['final_video_path']}", title="XUẤT BẢN THÀNH CÔNG"))
    elif args.command == "regenerate":
        state_mgr = ProjectStateManager(args.project_id)
        state_mgr.update_scene_status(args.scene, SceneStatus.PENDING)
        console.print(f"[bold yellow]Đã reset Scene {args.scene} về PENDING. Đang chạy lại pipeline...[/bold yellow]")
        state = state_mgr.load_state()
        factory = VietnameseVideoFactory(console_output=True)
        asyncio.run(factory.generate_video(
            topic=state.config.topic,
            duration=state.config.target_duration,
            platform=state.config.platform,
            language=state.config.language,
            project_id=args.project_id
        ))

if __name__ == "__main__":
    main()
