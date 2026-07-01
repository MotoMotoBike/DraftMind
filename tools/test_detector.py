import cv2

from detector.hero_detector import HeroDetector

detector = HeroDetector()

image = cv2.imread("test.png")

hero = detector.detect(image)

print("--------------------------------")
print("Detected hero:", hero)
print("--------------------------------")
