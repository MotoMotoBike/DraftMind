import argparse
import json
import sys
import cv2

from capture.screen_capture import ScreenCapture
from detector.draft_detector import DraftDetector
from config import DRAFT_REGION
from stratz.recommender import DraftRecommender
from ui.app import launch_ui


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

    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Получить рекомендации по пикам через STRATZ."
    )

    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Сколько вариантов пиков показать для каждой команды."
    )

    parser.add_argument(
        "--ui",
        action="store_true",
        help="Запустить UI для анализа и ручной корректировки драфта."
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

    if args.ui:
        launch_ui()
        return

    detector = DraftDetector()
    frame = load_frame(args)
    analysis = detector.analyze(frame)
    payload = analysis.to_payload()

    if args.suggest:
        recommender = DraftRecommender()
        payload["suggestions"] = recommender.suggest(
            analysis=analysis,
            top_n=max(1, args.top),
        )

    print(json.dumps(
        payload,
        ensure_ascii=False,
        indent=2
    ))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
