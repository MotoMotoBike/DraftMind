import cv2
import os

INPUT_IMAGE = "screenshot.png"
OUTPUT_DIR = "templates"

os.makedirs(OUTPUT_DIR, exist_ok=True)

image = cv2.imread(INPUT_IMAGE)

# Координаты нужно подобрать под свое разрешение
slots = [
    (420, 42, 62, 36),
    (488, 42, 62, 36),
    (556, 42, 62, 36),
    (624, 42, 62, 36),
    (692, 42, 62, 36),

    (1166, 42, 62, 36),
    (1234, 42, 62, 36),
    (1302, 42, 62, 36),
    (1370, 42, 62, 36),
    (1438, 42, 62, 36),
]

for index, (x, y, w, h) in enumerate(slots):
    crop = image[y:y+h, x:x+w]
    cv2.imwrite(f"{OUTPUT_DIR}/slot_{index}.png", crop)

print("Templates exported.")
