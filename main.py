#from capture.screen_capture import ScreenCapture
#from detector.draft_detector import DraftDetector

#capture = ScreenCapture()
#detector = DraftDetector()

#while True:

#    frame = capture.get_frame()

#    radiantPick, direPick = detector.detect(frame)

#    print("Radiant:", radiantPick)
#    print("Dire:", direPick)

import cv2

from detector.draft_detector import DraftDetector

IMAGE = "screenshot.png"

detector = DraftDetector()

frame = cv2.imread(IMAGE)

if frame is None:
    raise FileNotFoundError(f"Не удалось открыть {IMAGE}")

radiantPick, direPick = detector.detect(frame)

print("Radiant:", radiantPick)
print("Dire:", direPick)

cv2.imshow("Screenshot", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
