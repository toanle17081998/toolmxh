from pathlib import Path
from typing import List
from app.models.timeline import AudioTimeline, SceneTiming

class SubtitleEngine:
    """Tạo phụ đề tiếng Việt chuẩn định dạng SRT và ASS hỗ trợ Karaoke Highlight cho TikTok."""

    @staticmethod
    def format_srt_time(seconds: float) -> str:
        millis = int((seconds - int(seconds)) * 1000)
        secs = int(seconds) % 60
        mins = (int(seconds) // 60) % 60
        hours = int(seconds) // 3600
        return f"{hours:02d}:{mins:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def format_ass_time(seconds: float) -> str:
        cs = int((seconds - int(seconds)) * 100)
        secs = int(seconds) % 60
        mins = (int(seconds) // 60) % 60
        hours = int(seconds) // 3600
        return f"{hours:1d}:{mins:02d}:{secs:02d}.{cs:02d}"

    def generate_srt(self, timeline: AudioTimeline, output_path: str) -> str:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        idx = 1
        for scene in timeline.scenes:
            t_start = self.format_srt_time(scene.start_time)
            t_end = self.format_srt_time(scene.end_time)
            text = " ".join([w.word for w in scene.words]) if scene.words else ""
            lines.append(f"{idx}\n{t_start} --> {t_end}\n{text}\n")
            idx += 1

        with open(out_p, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return str(out_p)

    def generate_ass(self, timeline: AudioTimeline, output_path: str, platform: str = "tiktok", title: str = "") -> str:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        # MarginV cao để né thanh giao diện TikTok phía dưới
        margin_v = 240 if platform in ["tiktok", "shorts", "reels"] else 60

        header = f"""[Script Info]
Title: Vietnamese Generative Video Factory Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TikTokStyle,Arial,48,&H00FFFFFF,&H0000FFFF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,4,2,2,40,40,{margin_v},1
Style: IntroHeader,Arial,36,&H0000FFFF,&H00FFFFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,3,4,2,8,40,40,90,1
Style: OutroCTA,Arial,40,&H0000FFFF,&H0000FFFF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,3,4,2,2,40,40,{margin_v + 130},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []

        # 1. Intro Title Bumper Overlay (hiển thị 3.8s đầu với hiệu ứng fade in/out)
        if title:
            intro_end_time = min(3.8, timeline.total_duration)
            t_intro_start = self.format_ass_time(0.0)
            t_intro_end = self.format_ass_time(intro_end_time)
            clean_title = title.replace("\n", " ").strip()
            events.append(f"Dialogue: 1,{t_intro_start},{t_intro_end},IntroHeader,,0,0,0,,{{\\fad(400,600)}}🎬 {clean_title} 🎬")

        # 2. Phụ đề chính từng cảnh (Karaoke Highlight)
        for scene in timeline.scenes:
            t_start = self.format_ass_time(scene.start_time)
            t_end = self.format_ass_time(scene.end_time)

            if scene.words:
                # Tạo hiệu ứng karaoke highlight \k<thời gian centiseconds>
                k_text_parts = []
                for w in scene.words:
                    duration_cs = max(1, int(round((w.end_time - w.start_time) * 100)))
                    k_text_parts.append(f"{{\\k{duration_cs}}}{w.word}")
                line_content = " ".join(k_text_parts)
            else:
                line_content = ""

            events.append(f"Dialogue: 0,{t_start},{t_end},TikTokStyle,,0,0,0,,{line_content}")

        # 3. Outro Call-To-Action Overlay (hiển thị 4.0s cuối cùng)
        if timeline.total_duration > 5.0:
            outro_start_time = max(0.0, timeline.total_duration - 4.0)
            t_outro_start = self.format_ass_time(outro_start_time)
            t_outro_end = self.format_ass_time(timeline.total_duration)
            events.append(f"Dialogue: 1,{t_outro_start},{t_outro_end},OutroCTA,,0,0,0,,{{\\fad(500,500)}}👉 THEO DÕI KÊNH ĐỂ XEM TIẾP NHÉ! 🔔")

        with open(out_p, "w", encoding="utf-8") as f:
            f.write(header + "\n".join(events) + "\n")

        return str(out_p)
