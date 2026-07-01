import mss
import numpy as np
import cv2

from config import *

class ScreenCapture:

    def __init__(self):
        self.sct = mss.mss()

        self.monitor = {
            "left": DRAFT_X,
            "top": DRAFT_Y,
            "width": DRAFT_WIDTH,
            "height": DRAFT_HEIGHT
        }

    def get_frame(self):

        img = np.array(self.sct.grab(self.monitor))

        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
