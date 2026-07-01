import cv2
import os

class HeroDetector:

    def __init__(self):

        self.templates = {}

        folder = "detector/templates"

        for file in os.listdir(folder):

            hero = file.replace(".png","")

            image = cv2.imread(os.path.join(folder,file))

            self.templates[hero] = image

    def detect(self, image):

        bestHero = None
        bestScore = 0
        cv2.imwrite("debug_slot.png", image)
        print("\n===== Detect =====")

        for hero, template in self.templates.items():

            result = cv2.matchTemplate(
                image,
                template,
                cv2.TM_CCOEFF_NORMED
            )

            score = float(result.max())

            print(f"{hero:25} {score:.3f}")

            if score > bestScore:
                bestScore = score
                bestHero = hero

        print("-----------------------------")
        print(f"Winner : {bestHero}")
        print(f"Score  : {bestScore:.3f}")
        print("-----------------------------")

        if bestScore < 0.75:
            return None

        return bestHero
