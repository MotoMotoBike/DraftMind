from detector.hero_detector import HeroDetector
from config import *

class DraftDetector:

    def __init__(self):

        self.detector = HeroDetector()

    def detect(self, frame):

        radiantPick = []
        direPick = []

        for x, y in RADIANT_SLOTS:

            hero = self.detector.detect(
                frame[y:y+ICON_HEIGHT,
                      x:x+ICON_WIDTH]
            )

            radiantPick.append(hero)

        for x, y in DIRE_SLOTS:

            hero = self.detector.detect(
                frame[y:y+ICON_HEIGHT,
                      x:x+ICON_WIDTH]
            )

            direPick.append(hero)

        return radiantPick, direPick
