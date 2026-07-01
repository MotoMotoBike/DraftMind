import argparse
import json
import cv2

from capture.screen_capture import ScreenCapture
from detector.draft_detector import DraftDetector
from config import DRAFT_REGION


def parse_args():
    parser = argparse.ArgumentParser(
        description="Распознавание героев на стадии драфта."
    )

    parser.add_argument(
        "--image",
        default="screenshot.png",
        help="Путь до скриншота. Игнорируется при --capture."
    )

    parser.add_argument(
        "--capture",
        action="store_true",
        help="Считать верхнюю область экрана через mss."
    )

    return parser.parse_args()


def load_frame(args):
    if args.capture:
        frame = ScreenCapture().get_frame()
    else:
        frame = cv2.imread(args.image)

        if frame is None:
            raise FileNotFoundError(f"Не удалось открыть {args.image}")

        # Обрезаем до области драфта
        frame = frame[
            DRAFT_REGION.y:DRAFT_REGION.y + DRAFT_REGION.height,
            DRAFT_REGION.x:DRAFT_REGION.x + DRAFT_REGION.width
        ]

    # Дебаг
    #cv2.imwrite("debug_input.png", frame)

    return frame


def main():
    args = parse_args()

    detector = DraftDetector()

    frame = load_frame(args)

    analysis = detector.analyze(frame)

    print(json.dumps(
        analysis.to_payload(),
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    main()
