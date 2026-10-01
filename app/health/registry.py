import re
import unicodedata

from app.health.models import HealthCharacter, HealthCharacterBible, VisualMode


ENVIRONMENTS = {
    "BLOODSTREAM_WORLD": "clean stylized blood vessel interior with directional blood flow, readable vessels and red blood cells",
    "DIGESTIVE_WORLD": "clean stylized digestive tract interior, anatomically connected entry and exit, readable cutaway",
    "RESPIRATORY_WORLD": "clean stylized airway and branching bronchi environment with alveolar surfaces",
    "NERVOUS_SYSTEM_WORLD": "clean stylized neural network with readable directional neural signals",
    "ORGAN_ROOM": "clean internal human-body setting with the organ in an anatomically sensible location",
    "MICROSCOPIC_WORLD": "clear magnified biological cutaway with readable particles and tissue, no laboratory",
}

_DEFINITIONS = {
    "heart": ("asymmetric muscular anatomical heart, visible atria, ventricles and large vessel outlets; never a Valentine heart", "deep warm red", "front ventricular surface below vessel outlets", "determined", "rhythmic pumping and contraction"),
    "liver": ("broad wedge-shaped liver with recognizable large right lobe, smaller left lobe and curved underside", "reddish brown", "front surface of the large right lobe", "diligent", "subtle body movement, expressive arms and processing reactions"),
    "kidney": ("paired human kidneys, bean-shaped with inward-facing concave hila, ureter and vessel connections", "deep reddish brown", "outer convex surface of each kidney", "concentrated cooperative filtration team", "paired movement, readable internal filtration cutaways"),
    "stomach": ("J-shaped human stomach, distinct esophageal inlet, curved fundus, gastric body and pyloric outlet; not a kidney bean", "warm pink", "outer gastric body, outside the readable cutaway", "focused", "gentle gastric mixing contractions and controlled digestive flow"),
    "lungs": ("paired lobed human lungs with visible central trachea and branching bronchi; not clouds or wings", "soft healthy pink", "front surface of each lung, clear of the bronchi", "gentle", "expansion and relaxation with breathing, coughing only when relevant"),
    "brain": ("human brain with two hemispheres and recognizable folded gyri, not a smooth ball", "muted pink", "front surface, folds stay readable", "thoughtful", "subtle neural signalling and facial response"),
    "intestines": ("coiled small intestine framed by a recognizable segmented large intestine", "warm peach pink", "front outer large-intestine surface, coils remain unobscured", "patient", "gentle peristaltic waves in the direction of digestive transit"),
    "pancreas": ("elongated lobulated human pancreas, wider head and tapered tail", "warm ochre pink", "front central body", "attentive", "controlled release of relevant hormone or enzyme representations"),
    "bladder": ("rounded expandable human urinary bladder with two ureter entries and urethral outlet", "soft rose pink", "front outer bladder wall", "alert", "gradual expansion and appropriate emptying"),
    "eye": ("recognizable human eyeball with white sclera, iris, pupil and clear corneal dome", "ivory sclera and hazel iris", "eyebrows above iris; tiny expressive mouth below, never duplicate the central biological pupil", "observant", "readable gaze, blink and focus movement"),
    "tooth": ("recognizable human molar with enamel crown, gum boundary and two visible roots", "ivory enamel", "front crown, root anatomy stays visible", "cheerful", "small facial and arm motions while the dental process remains readable"),
}

ALIASES = {
    "heart": ["heart", "trái tim", "tim", "cardiac", "cardiovascular"],
    "liver": ["liver", "gan"],
    "kidney": ["kidney", "kidneys", "thận"],
    "stomach": ["stomach", "dạ dày", "bao tử"],
    "lungs": ["lung", "lungs", "phổi"],
    "brain": ["brain", "não"],
    "intestines": ["intestine", "intestines", "gut", "ruột"],
    "pancreas": ["pancreas", "pancreatic", "tụy", "tuỵ"],
    "bladder": ["bladder", "bàng quang"],
    "eye": ["eye", "eyes", "mắt", "retina", "võng mạc"],
    "tooth": ["tooth", "teeth", "răng", "dental"],
}

HEALTH_TERMS = ["blood", "artery", "cholesterol", "blood pressure", "digestion", "insulin",
                "glucose", "fatty liver", "smoking", "sleep", "hydration", "anatomy",
                "máu", "động mạch", "huyết áp", "tiêu hóa", "tiêu hoá", "khói thuốc",
                "hút thuốc", "giấc ngủ", "mất ngủ", "sức khỏe", "sức khoẻ", "cơ thể"]


def mentions(text: str, term: str) -> bool:
    text = unicodedata.normalize("NFC", text).lower()
    return bool(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text))


def detected_organs(text: str) -> list[str]:
    return [organ for organ, aliases in ALIASES.items() if any(mentions(text, term) for term in aliases)]


def resolve_visual_mode(text: str, mode: VisualMode | str = VisualMode.AUTO) -> VisualMode:
    mode = VisualMode(mode)
    if mode != VisualMode.AUTO:
        return mode
    # Common non-anatomical uses must not route astronomy/technology/weather to health.
    text = unicodedata.normalize("NFC", text).lower()
    for phrase in ("blood moon", "heart of the galaxy", "heart of a galaxy", "eye of the storm",
                   "eye of a storm", "computer sleep mode", "laptop sleep mode", "mắt bão"):
        text = text.replace(phrase, " ")
    technology = ('ai','artificial intelligence','computer','software','algorithm','technology','laptop',
                  'processor','digital','robot','tracking','máy tính','công nghệ','thuật toán','trí tuệ nhân tạo')
    medical = ('human','anatomy','health','medical','disease','neurons','brain cells','retina','insomnia',
               'sleep deprivation','body','sức khỏe','sức khoẻ','cơ thể','bệnh','tế bào','mất ngủ','giấc ngủ','võng mạc')
    organs = detected_organs(text)
    biological = any(organ not in ('brain','eye') for organ in organs) or any(mentions(text,term) for term in medical)
    if any(mentions(text,term) for term in technology) and not biological:
        return VisualMode.STANDARD
    if organs or any(mentions(text, term) for term in HEALTH_TERMS):
        return VisualMode.HEALTH_CHARACTER
    return VisualMode.STANDARD


class HealthCharacterRegistry:
    @staticmethod
    def get_character(organ: str) -> HealthCharacter:
        aliases = {"kidneys": "kidney", "gut": "intestines", "eyes": "eye", "teeth": "tooth", "lung": "lungs"}
        organ = aliases.get(organ.lower(), organ.lower())
        if organ not in _DEFINITIONS:
            raise ValueError(f"Unknown health organ: {organ}")
        shape, color, face, personality, animation = _DEFINITIONS[organ]
        character = HealthCharacter(organ=organ, shape=shape, color=color, face_placement=face,
                                    personality=personality, animation=animation,
                                    seed=17000 + list(_DEFINITIONS).index(organ) * 101)
        if organ == "eye":
            character.eyes = "the biological iris/pupil forms the expressive eye, eyebrows and lid convey expression; no extra eyeballs pasted on sclera"
        return character

    @classmethod
    def bible(cls, organs: list[str]) -> HealthCharacterBible:
        return HealthCharacterBible(characters={organ: cls.get_character(organ) for organ in dict.fromkeys(organs)})
