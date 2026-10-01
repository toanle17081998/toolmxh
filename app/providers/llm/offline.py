import re
from typing import Dict, Any, Optional
from app.providers.llm.base import LLMProvider
from app.models.script import StructuredScript, SceneScript
from app.models.storyboard import Storyboard, SceneStoryboard, VisualStyleBible

class OfflineBrainProvider(LLMProvider):
    """Content Brain tích hợp sẵn, hỗ trợ phân tích và tạo kịch bản tiếng Việt chất lượng cao khi chưa có API key."""

    async def research_topic(self, topic: str) -> Dict[str, Any]:
        return {
            "facts": [
                f"Sự biến mất hoặc bí ẩn của {topic} có thể làm thay đổi hoàn toàn trục quay và khí hậu toàn cầu.",
                "Thủy triều đại dương sẽ giảm tới 60%, dẫn tới sự sụp đổ của hệ sinh thái ven biển trên diện rộng.",
                "Các loài sinh vật săn mồi ban đêm sẽ mất đi ánh sáng định vị tự nhiên, gây đảo lộn chuỗi thức ăn."
            ],
            "core_angle": f"Khám phá chuỗi hiệu ứng cánh bướm kinh hoàng và tráng lệ nếu {topic} thực sự xảy ra.",
            "emotional_hook": "Sự tò mò tột độ pha lẫn cảm giác choáng ngợp trước quy luật khắc nghiệt của vũ trụ."
        }

    async def generate_script(
        self,
        topic: str,
        target_duration: int = 60,
        platform: str = "tiktok",
        language: str = "vi"
    ) -> StructuredScript:
        # Xây dựng kịch bản 8 cảnh kịch tính theo chuẩn cấu trúc video ngắn
        scenes = [
            SceneScript(
                id=1,
                narration=f"Chào mừng bạn đến với kênh khám phá bí ẩn! Bạn có bao giờ tự hỏi: Nếu một ngày {topic}, thế giới của chúng ta sẽ ra sao?",
                visual=f"Cảnh mở màn ấn tượng, bầu trời đêm tối đen huyền bí, mặt trăng lung linh bỗng nhiên tan biến thành làn khói ánh sáng",
                estimated_duration=5.0,
                camera_motion="dramatic slow zoom in",
                transition="fade in",
                sound_effect="cosmic whoosh impact"
            ),
            SceneScript(
                id=2,
                narration="Chỉ trong vài giây đầu tiên, bầu trời đêm chìm vào bóng tối hoàn toàn, chỉ còn lại những vì sao xa xôi.",
                visual="Thành phố hiện đại nhìn từ trên cao, bầu trời đen kịt không còn ánh trăng bạc chiếu rọi",
                estimated_duration=5.5,
                camera_motion="cinematic tilt down",
                transition="fade",
                sound_effect="night wind ambience"
            ),
            SceneScript(
                id=3,
                narration="Nhưng thảm họa thực sự chỉ mới bắt đầu dưới đại dương. Lực hấp dẫn biến mất, khiến thủy triều giảm hơn 60%.",
                visual="Sóng biển đại dương cuộn trào dữ dội rồi bất ngờ rút cạn, để lộ đáy biển kỳ bí",
                estimated_duration=6.0,
                camera_motion="wide sweeping pan left",
                transition="cut",
                sound_effect="deep ocean roar"
            ),
            SceneScript(
                id=4,
                narration="Hàng triệu sinh vật biển ven bờ bị mắc cạn, hệ sinh thái đại dương rơi vào khủng hoảng hỗn loạn chưa từng có.",
                visual="Bãi biển hoang vu với những rạn san hô phát quang sinh học phát sáng mờ ảo trong bóng đêm",
                estimated_duration=5.5,
                camera_motion="macro tracking shot",
                transition="cut",
                sound_effect="subtle water droplet"
            ),
            SceneScript(
                id=5,
                narration="Không còn lực kéo cân bằng, trục tự quay của Trái Đất bắt đầu rung lắc mất kiểm soát.",
                visual="Góc nhìn vũ trụ 3D thấy Trái Đất xoay quanh trục nghiêng, khí quyển phát ra ánh sáng cực quang kỳ ảo",
                estimated_duration=6.0,
                camera_motion="epic orbital rotation",
                transition="dissolve",
                sound_effect="low gravitational hum"
            ),
            SceneScript(
                id=6,
                narration="Thời tiết toàn cầu trở nên điên loạn: Một nửa hành tinh là mùa đông băng giá, nửa còn lại là sa mạc thiêu đốt!",
                visual="Sự đối lập giữa bão tuyết trắng xóa ở một phía và dung nham sa mạc rực lửa ở phía đối diện",
                estimated_duration=6.5,
                camera_motion="fast dynamic push through",
                transition="cut",
                sound_effect="howling blizzard"
            ),
            SceneScript(
                id=7,
                narration="Một ngày trên Trái Đất lúc này sẽ chỉ còn kéo dài từ 6 đến 12 tiếng do tốc độ quay tăng vọt.",
                visual="Cảnh hoàng hôn và bình minh vụt qua với tốc độ chóng mặt trên đỉnh núi tuyết hùng vĩ",
                estimated_duration=5.5,
                camera_motion="timelapse hyperlapse forward",
                transition="cut",
                sound_effect="time ticking acceleration"
            ),
            SceneScript(
                id=8,
                narration="Liệu bạn có muốn khám phá thêm nhiều điều kỳ thú khác? Hãy nhấn like và theo dõi kênh để không bỏ lỡ những bí ẩn tiếp theo nhé!",
                visual="Khung cảnh outro điện ảnh, một nhà thám hiểm đứng trên vách đá nhìn về phía chân trời vô tận đầy sao lấp lánh, hiệu ứng mờ dần",
                estimated_duration=5.5,
                camera_motion="slow crane pull back to stars",
                transition="fade to black",
                sound_effect="cinematic outro crescendo"
            )
        ]

        title = f"Điều Gì Sẽ Xảy Ra Nếu {topic}?"
        hook = f"Nếu {topic}, Trái Đất sẽ sụp đổ trong bao lâu?"

        return StructuredScript(
            title=title,
            hook=hook,
            target_duration=target_duration,
            language=language,
            scenes=scenes
        )

    async def generate_storyboard(
        self,
        script: StructuredScript,
        visual_bible: Optional[VisualStyleBible] = None
    ) -> Storyboard:
        vb = visual_bible or VisualStyleBible()
        scenes_sb = []
        for s in script.scenes:
            scenes_sb.append(
                SceneStoryboard(
                    scene_id=s.id,
                    duration=s.estimated_duration,
                    narration=s.narration,
                    subject=f"Key visual element representing scene {s.id}: {s.visual}",
                    environment=f"Cinematic environment setting for {script.title}",
                    lighting=vb.lighting,
                    camera_angle="cinematic dynamic angle",
                    camera_movement=s.camera_motion,
                    visual_style=vb.style,
                    image_prompt=f"Cinematic 8k photorealistic shot of {s.visual}, {vb.lighting}, {vb.lens}, {vb.contrast}, masterwork composition, hyper-detailed, ray-traced, 9:16 vertical framed",
                    video_prompt=f"Cinematic camera {s.camera_motion}, subtle atmospheric volumetric fog drift, continuous coherent physics motion, 8k documentary quality",
                    negative_prompt="ugly, distorted, blurry, low quality, artifacts, watermark, text, cartoon, 3d render plastic",
                    transition=s.transition,
                    sound_effect=s.sound_effect
                )
            )

        return Storyboard(
            project_id="temp",
            visual_bible=vb,
            scenes=scenes_sb
        )

    async def generate_metadata(
        self,
        topic: str,
        script: StructuredScript
    ) -> Dict[str, Any]:
        return {
            "tiktok_caption": f"Sự thật rợn người nếu {topic}! Bạn có tin con người sẽ sống sót? #khampha #khoahoc #vutru #fyp",
            "youtube_title": f"Chuyện Gì Xảy Ra Nếu {topic}? | Bí Ẩn Vũ Trụ Chưa Kể",
            "youtube_description": f"Video phân tích chi tiết viễn cảnh khoa học giả định: {topic}. Cùng khám phá chuỗi thảm họa địa chất và khí hậu toàn cầu.",
            "facebook_caption": f"Nếu một ngày {topic}, thế giới sẽ ra sao? Xem ngay để biết câu trả lời!",
            "hashtags": ["#khampha", "#khoahoc", "#vutru", "#bian", "#tiktokvietnam"],
            "keywords": [topic, "khoa học vũ trụ", "khám phá bí ẩn", "thảm họa thiên nhiên"],
            "thumbnail_text": "TRÁI ĐẤT SỤP ĐỔ?"
        }
