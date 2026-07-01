from dataclasses import dataclass

SCORE_PRECISION = 3


@dataclass(frozen=True)
class HeroMatch:
    hero: str
    score: float


@dataclass(frozen=True)
class SlotRecognition:
    team: str
    index: int
    bounds: dict[str, int]
    hero: str | None
    score: float


@dataclass(frozen=True)
class DraftAnalysis:
    radiant: list[SlotRecognition]
    dire: list[SlotRecognition]

    @property
    def radiant_picks(self) -> list[str | None]:
        return [slot.hero for slot in self.radiant]

    @property
    def dire_picks(self) -> list[str | None]:
        return [slot.hero for slot in self.dire]

    def to_payload(self) -> dict:
        return {
            "radiant": [
                {
                    "slot": slot.index,
                    "hero": slot.hero,
                    "score": self._round_score(slot.score),
                    "bounds": slot.bounds,
                }
                for slot in self.radiant
            ],
            "dire": [
                {
                    "slot": slot.index,
                    "hero": slot.hero,
                    "score": self._round_score(slot.score),
                    "bounds": slot.bounds,
                }
                for slot in self.dire
            ],
        }

    @staticmethod
    def _round_score(score: float) -> float:
        return round(score, SCORE_PRECISION)
