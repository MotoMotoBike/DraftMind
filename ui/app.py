from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2

from capture.screen_capture import ScreenCapture
from config import DRAFT_REGION, DIRE_SLOTS, RADIANT_SLOTS
from detector.draft_detector import DraftDetector
from detector.models import DraftAnalysis, SlotRecognition
from stratz.recommender import DraftRecommender


class DraftMindApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DraftMind UI")

        self.detector = DraftDetector()
        self.recommender: DraftRecommender | None = None

        self.hero_options = [""] + self._load_hero_options()
        self.source_var = tk.StringVar(value="capture")
        self.file_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Готово")

        self.slot_inputs: dict[tuple[str, int], ttk.Combobox] = {}

        self._build_layout()

    def _build_layout(self):
        root = self.root
        root.columnconfigure(0, weight=1)

        source_frame = ttk.LabelFrame(root, text="Источник")
        source_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        source_frame.columnconfigure(1, weight=1)

        ttk.Radiobutton(
            source_frame,
            text="Скрин экрана",
            variable=self.source_var,
            value="capture",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        ttk.Radiobutton(
            source_frame,
            text="Файл",
            variable=self.source_var,
            value="image",
        ).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Entry(source_frame, textvariable=self.file_var).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 6)
        )

        ttk.Button(source_frame, text="Выбрать файл", command=self._choose_file).grid(
            row=1, column=2, sticky="ew", padx=(0, 8), pady=(0, 6)
        )

        ttk.Button(source_frame, text="Анализировать", command=self._analyze_source).grid(
            row=0, column=2, sticky="ew", padx=(0, 8), pady=6
        )

        draft_frame = ttk.LabelFrame(root, text="Текущий драфт (можно исправлять вручную)")
        draft_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=8)

        ttk.Label(draft_frame, text="Radiant").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        for idx, slot in enumerate(RADIANT_SLOTS):
            combo = ttk.Combobox(draft_frame, values=self.hero_options, state="readonly", width=20)
            combo.grid(row=0, column=idx + 1, padx=4, pady=6)
            combo.set("")
            self.slot_inputs[(slot.team, slot.index)] = combo

        ttk.Label(draft_frame, text="Dire").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        for idx, slot in enumerate(DIRE_SLOTS):
            combo = ttk.Combobox(draft_frame, values=self.hero_options, state="readonly", width=20)
            combo.grid(row=1, column=idx + 1, padx=4, pady=6)
            combo.set("")
            self.slot_inputs[(slot.team, slot.index)] = combo

        ttk.Button(
            draft_frame,
            text="Пересчитать по исправленному драфту",
            command=self._recalculate_manual,
        ).grid(row=2, column=0, columnspan=6, sticky="ew", padx=8, pady=(4, 8))

        suggestions_frame = ttk.LabelFrame(root, text="Предложенные пики")
        suggestions_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=8)
        root.rowconfigure(2, weight=1)

        self.suggestions_text = tk.Text(suggestions_frame, height=18, wrap="word")
        self.suggestions_text.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        suggestions_frame.columnconfigure(0, weight=1)
        suggestions_frame.rowconfigure(0, weight=1)

        ttk.Label(root, textvariable=self.status_var).grid(
            row=3, column=0, sticky="w", padx=12, pady=(0, 10)
        )

    def _choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите изображение",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)
            self.source_var.set("image")

    def _analyze_source(self):
        try:
            frame = self._load_frame_from_source()
            analysis = self.detector.analyze(frame)
            self._apply_analysis(analysis)
            self._update_suggestions(analysis)
            self.status_var.set("Анализ выполнен")
        except Exception as exc:
            self.status_var.set("Ошибка анализа")
            messagebox.showerror("Ошибка", str(exc))

    def _recalculate_manual(self):
        analysis = self._analysis_from_inputs()
        self._update_suggestions(analysis)
        self.status_var.set("Рекомендации пересчитаны")

    def _load_frame_from_source(self):
        if self.source_var.get() == "capture":
            return ScreenCapture().get_frame()

        image_path = self.file_var.get().strip()
        if not image_path:
            raise FileNotFoundError("Выберите файл изображения")

        frame = cv2.imread(image_path)
        if frame is None:
            raise FileNotFoundError(f"Не удалось открыть {image_path}")

        return self._extract_draft_region(frame)

    @staticmethod
    def _extract_draft_region(frame):
        height, width = frame.shape[:2]
        required_width = DRAFT_REGION.x + DRAFT_REGION.width
        required_height = DRAFT_REGION.y + DRAFT_REGION.height

        if width == DRAFT_REGION.width and height == DRAFT_REGION.height:
            return frame

        if width < required_width or height < required_height:
            raise ValueError(
                "Изображение меньше области драфта: "
                f"{width}x{height}, нужно минимум {required_width}x{required_height}."
            )

        return DRAFT_REGION.crop(frame)

    def _analysis_from_inputs(self) -> DraftAnalysis:
        radiant = [
            SlotRecognition(
                team=slot.team,
                index=slot.index,
                hero=self._value_to_hero(self.slot_inputs[(slot.team, slot.index)].get()),
                score=0.0,
            )
            for slot in RADIANT_SLOTS
        ]
        dire = [
            SlotRecognition(
                team=slot.team,
                index=slot.index,
                hero=self._value_to_hero(self.slot_inputs[(slot.team, slot.index)].get()),
                score=0.0,
            )
            for slot in DIRE_SLOTS
        ]
        return DraftAnalysis(radiant=radiant, dire=dire)

    def _apply_analysis(self, analysis: DraftAnalysis):
        for slot in analysis.radiant + analysis.dire:
            combo = self.slot_inputs[(slot.team, slot.index)]
            combo.set(slot.hero or "")

    def _update_suggestions(self, analysis: DraftAnalysis):
        if self.recommender is None:
            self.recommender = DraftRecommender()

        try:
            suggestions = self.recommender.suggest(analysis=analysis, top_n=5)
            text = self._format_suggestions(suggestions)
        except Exception as exc:
            text = (
                "Не удалось получить рекомендации через STRATZ.\n"
                f"Причина: {exc}\n\n"
                "Проверьте secrets.json с STRATZ_API_TOKEN."
            )

        self.suggestions_text.configure(state="normal")
        self.suggestions_text.delete("1.0", tk.END)
        self.suggestions_text.insert("1.0", text)
        self.suggestions_text.configure(state="disabled")

    @staticmethod
    def _format_suggestions(suggestions: dict) -> str:
        lines: list[str] = [f"Источник: {suggestions.get('source', '-')}", ""]

        for team in ("radiant", "dire"):
            team_block = suggestions.get(team, {})
            lines.append(team.upper())
            lines.append(f"Синергия команды: {team_block.get('team_synergy_score', 0)}")
            lines.append(f"Свободные слоты: {team_block.get('open_slots', [])}")
            lines.append("Топ рекомендации:")

            recommended = team_block.get("recommended", [])
            if recommended:
                for item in recommended:
                    lines.append(
                        "- {name} ({hero}) | score={score} syn={syn} vs={vs}".format(
                            name=item.get("display_name", "-"),
                            hero=item.get("hero", "-"),
                            score=item.get("score", 0),
                            syn=item.get("synergy_score", 0),
                            vs=item.get("counter_score", 0),
                        )
                    )
            else:
                lines.append("- Нет")

            lines.append("Автозаполнение слотов:")
            fills = team_block.get("fills", [])
            if fills:
                for fill in fills:
                    lines.append(
                        f"- slot {fill.get('slot')}: {fill.get('display_name', '-')} ({fill.get('hero', '-')})"
                    )
            else:
                lines.append("- Нет")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _value_to_hero(value: str) -> str | None:
        hero = value.strip()
        return hero or None

    @staticmethod
    def _load_hero_options() -> list[str]:
        templates_dir = Path(__file__).resolve().parents[1] / "detector" / "templates"
        return sorted(path.stem for path in templates_dir.glob("*.png"))

    def run(self):
        self.root.mainloop()


def launch_ui():
    app = DraftMindApp()
    app.run()
