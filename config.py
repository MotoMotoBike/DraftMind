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
ICON_WIDTH = 62
ICON_HEIGHT = 36
# Базовый порог для иконок, подобранный для нормализованных шаблонов 62x36.
MATCH_THRESHOLD = 0.72

RADIANT_SLOTS = (
    HeroSlot("radiant", 0, 20, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 1, 90, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 2, 160, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 3, 230, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("radiant", 4, 300, 45, ICON_WIDTH, ICON_HEIGHT),
)

DIRE_SLOTS = (
    HeroSlot("dire", 0, 790, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 1, 860, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 2, 930, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 3, 1000, 45, ICON_WIDTH, ICON_HEIGHT),
    HeroSlot("dire", 4, 1070, 45, ICON_WIDTH, ICON_HEIGHT),
)

ALL_SLOTS = RADIANT_SLOTS + DIRE_SLOTS
