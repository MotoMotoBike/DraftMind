import argparse
import json
import cv2

from capture.screen_capture import ScreenCapture
from detector.draft_detector import DraftDetector


def parse_args():
    parser = argparse.ArgumentParser(description="Распознавание героев на стадии драфта.")
    parser.add_argument(
        "--image",
        default="screenshot.png",
        help="Путь до скриншота. Игнорируется при --capture.",
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Считать верхнюю область экрана через mss.",
    )
    return parser.parse_args()


def load_frame(args):
    if args.capture:
        return ScreenCapture().get_frame()

    frame = cv2.imread(args.image)
    if frame is None:
        raise FileNotFoundError(f"Не удалось открыть {args.image}")
    return frame


def main():
    args = parse_args()
    detector = DraftDetector()
    analysis = detector.analyze(load_frame(args))
    print(json.dumps(analysis.to_payload(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
