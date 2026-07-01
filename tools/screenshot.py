import cv2
import mss
import numpy as np

with mss.mss() as sct:

    monitor = sct.monitors[1]

    img = np.array(sct.grab(monitor))

    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    cv2.imwrite("screenshot.png", frame)

    print("Screenshot saved as screenshot.png")
