import cv2
import logging
from pathlib import Path

from config import MATCH_THRESHOLD
from detector.models import HeroMatch

logger = logging.getLogger(__name__)


class HeroDetector:

    def __init__(self, template_dir=None, threshold=MATCH_THRESHOLD):
        self.threshold = threshold

        # Чем больше nfeatures, тем лучше качество
        self.orb = cv2.ORB_create(
            nfeatures=1000,
            scaleFactor=1.2,
            nlevels=8
        )

        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        self.templates = {}

        folder = Path(template_dir or Path(__file__).resolve().parent / "templates")

        if not folder.exists():
            raise FileNotFoundError(folder)

        for file in sorted(folder.glob("*.png")):

            hero = file.stem

            image = cv2.imread(str(file))

            if image is None:
                continue

            gray = self._prepare_image(image)

            kp, des = self.orb.detectAndCompute(gray, None)

            if des is None:
                logger.warning("%s: no descriptors", hero)
                continue

            self.templates[hero] = {
                "kp": kp,
                "des": des
            }

        logger.info("Loaded %d templates", len(self.templates))

    def detect(self, image, alias):

        if image is None or image.size == 0:
            return None

        gray = self._prepare_image(image)

        cv2.imwrite(f"{alias}_debug_slot.png", gray)

        kp, des = self.orb.detectAndCompute(gray, None)

        if des is None:
            return None

        bestHero = None
        bestScore = 0

        debug = []

        for hero, template in self.templates.items():

            matches = self.matcher.knnMatch(
                des,
                template["des"],
                k=2
            )

            good = []

            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    good.append(m)

            score = len(good)

            debug.append((hero, score))

            if score > bestScore:
                bestScore = score
                bestHero = hero

        debug.sort(key=lambda x: x[1], reverse=True)

        print(f"\n====== {alias} ======")
        for hero, score in debug[:10]:
            print(f"{hero:25} {score}")

        print(f"Winner: {bestHero} ({bestScore})")

        if bestHero is None:
            return None

        if bestScore < self.threshold:
            return None

        return HeroMatch(
            hero=bestHero,
            score=bestScore
        )

    def _prepare_image(self, image):

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gray = cv2.equalizeHist(gray)

        return gray
