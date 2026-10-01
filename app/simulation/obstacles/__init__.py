from .ramp import RampObstacle
from .stairs import StairsObstacle
from .rotating_bar import RotatingBarObstacle
from .hammer import HammerObstacle
from .moving_platform import MovingPlatformObstacle
from .platform_drop import PlatformDropObstacle
from .gap import GapObstacle

OBSTACLES = {'ramp': RampObstacle, 'stairs': StairsObstacle, 'rotating_bar': RotatingBarObstacle,
             'hammer': HammerObstacle, 'moving_platform': MovingPlatformObstacle,
             'platform_drop':PlatformDropObstacle, 'gap':GapObstacle}
