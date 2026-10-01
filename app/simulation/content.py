"""Extensible content families and seed-driven ideas; no renderer or AI imports."""
import random
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ContentFamily:
    id: str
    label: str
    world: str | None
    description: str
    ideas: tuple[str, ...]

    def public(self):
        return {**asdict(self), 'renderable': self.world is not None}


FAMILIES = (
    ContentFamily('obstacle_course', 'Vượt chướng ngại vật', 'course', 'Một thiết kế chạy qua một đường thử liên tục.',
                  ('Xe brick vượt đường thử vật lý', 'Crawler vượt bậc thang và khoảng trống', 'Đường thử với cú rơi platform')),
    ContentFamily('build_challenge', 'Xây xe giải thử thách', 'bridge', 'Lắp ráp một thiết kế và kiểm tra khả năng vượt cầu.',
                  ('Xây xe vừa với cây cầu hẹp', 'Thiết kế xe vượt một nhịp cầu', 'Lắp xe thấp và ổn định để qua cầu')),
    ContentFamily('improve_retry', 'Sửa thiết kế và thử lại', 'bridge', 'Kết quả lượt trước quyết định cách sửa lượt sau.',
                  ('Xe rơi khỏi cầu: sửa cấu trúc rồi thử lại', 'Thu hẹp trục bánh để vượt cầu', 'Tối ưu thiết kế sau mỗi lần thử')),
    ContentFamily('design_comparison', 'So sánh thiết kế', 'bridge', 'Các thiết kế khác nhau trên cùng một thử thách.',
                  ('Xe rộng, xe hẹp và xe 6 bánh qua cùng một cầu', 'Ba chassis: thiết kế nào qua cầu?', 'So sánh xe thấp với xe cao trên cầu hẹp')),
    ContentFamily('parameter_test', 'Thử một thông số', 'bridge', 'Chỉ đổi một thông số của xe; giữ nguyên thử thách.',
                  ('Bánh nhỏ và bánh lớn: khác nhau thế nào?', 'Chiều dài cơ sở ảnh hưởng vượt cầu ra sao?', 'Xe nhẹ và xe nặng trên cùng đường thử')),
    ContentFamily('destruction', 'Va chạm và phá khối', 'impact', 'Đâm vào một khối brick có các phần tử vật lý độc lập.',
                  ('Xe nào đẩy vỡ khối brick tốt hơn?', 'Tăng khối lượng xe để phá tường', 'Bumper thường và bumper dài đâm vào cùng tường')),
    ContentFamily('durability', 'Thả rơi và tiếp đất', 'drop', 'Đo độ nghiêng, tốc độ rơi và trạng thái tiếp đất.',
                  ('Thả xe từ ba độ cao', 'Xe thấp hay xe cao tiếp đất ổn định hơn?', 'Bốn bánh và sáu bánh khi rơi từ platform')),
    ContentFamily('bridge_engineering', 'Xây và thử tải cầu', 'bridge', 'Thay kết cấu cầu; giữ nguyên xe thử tải.',
                  ('Cầu dầm, cầu ghép và cầu gia cố chịu tải', 'Cầu ghép brick có bị gãy dưới xe?', 'Gia cố mối nối cầu rồi thử cùng một tải')),
    ContentFamily('cargo_balance', 'Chở hàng và cân bằng', 'bridge', 'Hàng là rigid body gắn vào xe; vị trí và tải trọng có tác dụng thật.',
                  ('Xe chở khối nặng qua cầu', 'Hàng thấp và hàng cao: xe nào ổn định?', 'Tăng tải trọng trên cùng chassis')),
    ContentFamily('time_trial', 'Thi đấu tính giờ', 'bridge', 'Các xe thử lần lượt trên cùng đường; xếp hạng theo thời gian đo được.',
                  ('Ba mẫu xe thi đấu tính giờ', 'Bốn bánh và sáu bánh trên cùng đường', 'Mẫu nào qua cầu nhanh nhất?')),
    ContentFamily('budget_build', 'Giới hạn vật liệu', None, 'Cần builder kiểm soát chính xác số brick; chưa có renderer.',
                  ('Chỉ dùng 20 brick để xây xe qua cầu', 'Xe tối giản chở được bao nhiêu?', 'Cầu chỉ dùng một số lượng brick giới hạn')),
    ContentFamily('mechanisms', 'Máy móc và cơ cấu', None, 'Cần cơ cấu khớp/motor riêng; chưa có renderer.',
                  ('Cần cẩu brick nâng vật nặng', 'Máy xúc dọn vật cản', 'So sánh ba cơ cấu truyền động')),
    ContentFamily('chain_reaction', 'Chuỗi phản ứng', 'domino', 'Các khối domino đổ do gravity và va chạm.',
                  ('Một khối đẩy đổ cả hàng domino', 'Khoảng cách domino quyết định phản ứng dây chuyền', 'Domino ngắn và domino dài: chuỗi nào hoàn tất?')),
    ContentFamily('marble_run', 'Đường bi', 'ball', 'Quả bi lăn bằng gravity trên đường dốc có vật cản.',
                  ('Bi vượt đường dốc với các chốt brick', 'Xây đường bi gravity đơn giản', 'Quả bi tìm đường qua chướng ngại vật')),
    ContentFamily('ball_race', 'Đua bóng', 'ball_race', 'Ba quả bóng cùng xuất phát; đo thời gian qua vạch đích.',
                  ('Ba quả bóng đua xuống đường dốc', 'Bóng nhỏ và bóng lớn thi đấu', 'Đua bóng với độ bám khác nhau')),
    ContentFamily('survival', 'Thử thách sinh tồn', 'course', 'Các lượt thử ngắn với drop/gap/ramp; thất bại được ghi nhận.',
                  ('Xe sống sót qua cú rơi lớn?', 'Ba thiết kế đối mặt với cùng đường thử', 'Vượt bậc thang rồi rơi xuống platform')),
    ContentFamily('limit_test', 'Tăng độ khó đến giới hạn', 'bridge', 'Giữ nguyên xe, tăng khoảng trống qua các lượt thử.',
                  ('Khoảng trống lớn đến đâu xe còn vượt được?', 'Tăng độ khó cầu qua từng lượt', 'Tìm khoảng trống đầu tiên khiến xe thất bại')),
)
CONTENT_FAMILIES = {family.id: family for family in FAMILIES}


def validate_content_type(value):
    if not isinstance(value,str):
        raise ValueError('Content type must be a string')
    if value == 'auto':
        return value
    family = CONTENT_FAMILIES.get(value)
    if family is None:
        raise ValueError(f'Unknown simulation content type: {value}')
    if family.world is None:
        raise ValueError(f'{family.label} is an idea category; its renderer is not implemented yet')
    return value


class SimulationIdeaGenerator:
    def generate(self, seed, content_type='auto', count=3, history=(), include_planned=False):
        if content_type != 'auto' and content_type not in CONTENT_FAMILIES:
            raise ValueError('Unknown content type')
        rng = random.Random(seed)
        families = [f for f in FAMILIES if (include_planned or f.world is not None)
                    and (content_type == 'auto' or f.id == content_type)]
        pool = [(family, index) for family in families for index in range(len(family.ideas))]
        if not pool:
            raise ValueError('No renderable ideas in this content type')
        unseen = [item for item in pool if f'{item[0].id}:{item[1]}' not in history]
        rng.shuffle(unseen)
        remainder = [item for item in pool if item not in unseen]
        rng.shuffle(remainder)
        choices = unseen + remainder
        if content_type == 'auto':
            first, later, seen = [], [], set()
            for item in choices:
                if item[0].id not in seen:
                    first.append(item)
                    seen.add(item[0].id)
                else:
                    later.append(item)
            choices = first + later
        ideas = []
        for family, index in choices[:count]:
            ideas.append(self.resolve(f'{family.id}:{index}', seed))
        return ideas

    def resolve(self, idea_id, seed):
        try:
            family_id, index_text = idea_id.rsplit(':', 1)
            family = CONTENT_FAMILIES[family_id]
            index = int(index_text)
            if not 0 <= index < len(family.ideas):
                raise ValueError('Invalid idea index')
        except (ValueError, KeyError) as error:
            raise ValueError('Unknown simulation idea') from error
        return {'id': idea_id, 'content_type': family.id, 'title': family.ideas[index],
                'description': family.description, 'world': family.world,
                'renderable': family.world is not None, 'seed': seed,
                'beats': ['build', 'test', 'measure', 'refine' if family.id == 'improve_retry' else 'compare']}
