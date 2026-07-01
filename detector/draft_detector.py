from detector.hero_detector import HeroDetector
from config import ALL_SLOTS, DRAFT_REGION
from detector.models import DraftAnalysis, SlotRecognition

class DraftDetector:

    def __init__(self):
        self.detector = HeroDetector()

    def analyze(self, frame):
        draft_frame = self._extract_draft_frame(frame)
        detections = {team: [] for team in ("radiant", "dire")}

        for slot in ALL_SLOTS:
            match = self.detector.detect(slot.crop(draft_frame))
            detections[slot.team].append(
                SlotRecognition(
                    team=slot.team,
                    index=slot.index,
                    bounds=slot.bounds,
                    hero=None if match is None else match.hero,
                    score=0.0 if match is None else match.score,
                )
            )

        return DraftAnalysis(
            radiant=detections["radiant"],
            dire=detections["dire"],
        )

    def detect(self, frame):
        analysis = self.analyze(frame)
        return analysis.radiant_picks, analysis.dire_picks

    def _extract_draft_frame(self, frame):
        height, width = frame.shape[:2]

        if width == DRAFT_REGION.width and height == DRAFT_REGION.height:
            return frame

        if width < DRAFT_REGION.x + DRAFT_REGION.width or height < DRAFT_REGION.y + DRAFT_REGION.height:
            raise ValueError(
                "Frame is smaller than the configured draft region: "
                f"got {width}x{height}, expected at least "
                f"{DRAFT_REGION.x + DRAFT_REGION.width}x{DRAFT_REGION.y + DRAFT_REGION.height}."
            )

        return DRAFT_REGION.crop(frame)
