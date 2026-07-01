from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    x: int
    y: int
    width: int
    height: int

    def crop(self, frame):
        return frame[self.y:self.y + self.height, self.x:self.x + self.width]


@dataclass(frozen=True)
class HeroSlot:
    team: str
    index: int
    x: int
    y: int
    width: int
    height: int

    def crop(self, frame):
        return frame[self.y:self.y + self.height, self.x:self.x + self.width]

    @property
    def bounds(self):
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


DRAFT_REGION = Region(x=180, y=0, width=1560, height=120)
ICON_WIDTH = 127
ICON_HEIGHT = 80
# Базовый порог для иконок, подобранный для нормализованных шаблонов 62x36.
MATCH_THRESHOLD = 4

RADIANT_SLOTS = (
    HeroSlot("radiant", 0, 25, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 1, 148, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 2, 270, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 3, 395, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 4, 525, 0, ICON_WIDTH, ICON_HEIGHT),
)

DIRE_SLOTS = (
    HeroSlot("dire", 0, 920, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 1, 1042, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 2, 1160, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 3, 1290, 0, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 4, 1409, 0, ICON_WIDTH, ICON_HEIGHT),
)

ALL_SLOTS = RADIANT_SLOTS + DIRE_SLOTS
