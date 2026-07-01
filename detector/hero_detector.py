import cv2
from pathlib import Path

from config import ICON_HEIGHT, ICON_WIDTH, MATCH_THRESHOLD
from detector.models import HeroMatch

class HeroDetector:

    def __init__(self, template_dir=None, threshold=MATCH_THRESHOLD):
        self.templates = {}
        self.threshold = threshold
        self.slot_size = (ICON_WIDTH, ICON_HEIGHT)

        folder = Path(template_dir or Path(__file__).resolve().parent / "templates")

        for file in sorted(folder.glob("*.png")):
            hero = file.stem
            image = cv2.imread(str(file))
            if image is None:
                continue
            self.templates[hero] = self._prepare_image(image)

    def detect(self, image):
        if image is None or image.size == 0:
            return None

        candidate = self._prepare_image(image)
        best_hero = None
        best_score = 0.0

        for hero, template in self.templates.items():
            score = self._match(candidate, template)
            if score > best_score:
                best_score = score
                best_hero = hero

        if best_score < self.threshold or best_hero is None:
            return None

        return HeroMatch(hero=best_hero, score=best_score)

    def _prepare_image(self, image):
        resized = cv2.resize(image, self.slot_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (3, 3), 0)

    def _match(self, image, template):
        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        return float(result.max())
