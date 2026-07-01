import mss
import numpy as np
import cv2

from config import DRAFT_REGION

class ScreenCapture:

    def __init__(self):
        self.sct = mss.mss()

        self.monitor = {
            "left": DRAFT_REGION.x,
            "top": DRAFT_REGION.y,
            "width": DRAFT_REGION.width,
            "height": DRAFT_REGION.height
        }

    def get_frame(self):

        img = np.array(self.sct.grab(self.monitor))

        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        #cv2.imwrite("debug_screen_capture.png", frame)

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
