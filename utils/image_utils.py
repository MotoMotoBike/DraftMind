import cv2
import numpy as np


def resize(image, width=None, height=None):
    h, w = image.shape[:2]

    if width is None and height is None:
        return image

    if width is None:
        ratio = height / h
        dim = (int(w * ratio), height)
    else:
        ratio = width / w
        dim = (width, int(h * ratio))

    return cv2.resize(image, dim, interpolation=cv2.INTER_AREA)


def to_gray(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def crop(image, x, y, w, h):
    return image[y:y+h, x:x+w]


def draw_rectangle(image, x, y, w, h, color=(0, 255, 0), thickness=2):
    cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)


def show(title, image):
    cv2.imshow(title, image)


def wait(delay=1):
    return cv2.waitKey(delay)
