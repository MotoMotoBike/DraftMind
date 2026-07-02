from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean
import re

from detector.models import DraftAnalysis
from stratz.client import StratzClient


HERO_CONSTANTS_QUERY = """
query HeroConstants {
  constants {
    heroes {
      id
      name
      shortName
      displayName
      roles {
        roleId
      }
    }
  }
}
"""


DRAFT_STATS_QUERY = """
query DraftStats($matchupsTake: Int!, $metaTake: Int!) {
  heroStats {
    matchUp(bracketBasicIds: [DIVINE_IMMORTAL], take: $matchupsTake) {
      heroId
      vs {
        heroId1
        heroId2
        synergy
      }
      with {
        heroId1
        heroId2
        synergy
      }
    }
    winWeek(
      take: $metaTake
      bracketIds: [DIVINE, IMMORTAL]
      gameModeIds: [ALL_PICK_RANKED]
    ) {
      heroId
      matchCount
      winCount
    }
  }
}
"""


LEGACY_HERO_ALIASES = {
    "centaur": "centaur_warrunner",
    "doom_bringer": "doom",
    "furion": "natures_prophet",
    "life_stealer": "lifestealer",
    "magnataur": "magnus",
    "necrolyte": "necrophos",
    "nevermore": "shadow_fiend",
    "obsidian_destroyer": "outworld_destroyer",
    "queenofpain": "queen_of_pain",
    "rattletrap": "clockwerk",
    "shredder": "timbersaw",
    "skeleton_king": "wraith_king",
    "treant": "treant_protector",
    "vengefulspirit": "vengeful_spirit",
    "windrunner": "windranger",
    "wisp": "io",
    "zuus": "zeus",
}


@dataclass(frozen=True)
class HeroInfo:
    hero_id: int
    short_name: str
    display_name: str
    role_ids: list[int]


@dataclass(frozen=True)
class Recommendation:
    hero_id: int
    short_name: str
    display_name: str
    score: float
    win_rate: float
    match_count: int
    synergy_score: float
    counter_score: float
    role_ids: list[int]

    def to_payload(self) -> dict:
        return {
            "hero_id": self.hero_id,
            "hero": self.short_name,
            "display_name": self.display_name,
            "score": round(self.score, 4),
            "win_rate": round(self.win_rate, 4),
            "match_count": self.match_count,
            "synergy_score": round(self.synergy_score, 4),
            "counter_score": round(self.counter_score, 4),
            "role_ids": self.role_ids,
        }


class DraftRecommender:

    def __init__(self, client: StratzClient | None = None):
        self.client = client or StratzClient()
        self._hero_pool: dict[int, HeroInfo] | None = None
        self._hero_index: dict[str, HeroInfo] | None = None
        self._meta: dict[int, dict] | None = None
        self._matchups: dict[int, dict[str, dict[int, float]]] | None = None

    def suggest(self, analysis: DraftAnalysis, top_n: int = 5) -> dict:
        heroes_by_id = self._load_heroes()
        matchups, meta = self._load_stats()

        radiant_ids = self._resolve_team(analysis.radiant_picks)
        dire_ids = self._resolve_team(analysis.dire_picks)
        taken = set(radiant_ids) | set(dire_ids)
        average_win_rate = self._average_win_rate(meta)

        return {
            "source": "STRATZ",
            "radiant": self._suggest_for_team(
                open_slots=self._open_slots(analysis.radiant),
                allied_ids=radiant_ids,
                enemy_ids=dire_ids,
                taken_ids=taken,
                heroes_by_id=heroes_by_id,
                matchups=matchups,
                meta=meta,
                average_win_rate=average_win_rate,
                top_n=top_n,
            ),
            "dire": self._suggest_for_team(
                open_slots=self._open_slots(analysis.dire),
                allied_ids=dire_ids,
                enemy_ids=radiant_ids,
                taken_ids=taken,
                heroes_by_id=heroes_by_id,
                matchups=matchups,
                meta=meta,
                average_win_rate=average_win_rate,
                top_n=top_n,
            ),
        }

    def _load_heroes(self) -> dict[int, HeroInfo]:
        if self._hero_pool is not None:
            return self._hero_pool

        data = self.client.execute(HERO_CONSTANTS_QUERY)
        heroes = data["constants"]["heroes"]
        hero_pool: dict[int, HeroInfo] = {}
        hero_index: dict[str, HeroInfo] = {}

        for hero in heroes:
            info = HeroInfo(
                hero_id=hero["id"],
                short_name=hero["shortName"],
                display_name=hero["displayName"],
                role_ids=[role["roleId"] for role in hero.get("roles", [])],
            )
            hero_pool[info.hero_id] = info

            lookup_keys = {
                hero.get("name", ""),
                info.short_name,
                info.display_name,
                info.short_name.replace("_", ""),
                hero.get("name", "").removeprefix("npc_dota_hero_"),
            }

            for key in lookup_keys:
                normalized = self._normalize(key)
                if normalized:
                    hero_index[normalized] = info

        self._hero_pool = hero_pool
        self._hero_index = hero_index
        return hero_pool

    def _load_stats(self) -> tuple[dict[int, dict[str, dict[int, float]]], dict[int, dict]]:
        if self._matchups is not None and self._meta is not None:
            return self._matchups, self._meta

        take = len(self._load_heroes()) + 16
        data = self.client.execute(
            DRAFT_STATS_QUERY,
            variables={
                "matchupsTake": take,
                "metaTake": take,
            },
        )

        hero_stats = data["heroStats"]
        meta: dict[int, dict] = {}
        matchups: dict[int, dict[str, dict[int, float]]] = {}

        for row in hero_stats.get("winWeek", []):
            hero_id = row["heroId"]
            match_count = row.get("matchCount") or 0
            win_count = row.get("winCount") or 0
            meta[hero_id] = {
                "match_count": match_count,
                "win_rate": 0.0 if match_count == 0 else win_count / match_count,
            }

        for row in hero_stats.get("matchUp", []):
            hero_id = row["heroId"]
            matchups[hero_id] = {
                "with": self._relation_map(row.get("with", []), hero_id),
                "vs": self._relation_map(row.get("vs", []), hero_id),
            }

        self._meta = meta
        self._matchups = matchups
        return matchups, meta

    def _resolve_team(self, picks: list[str | None]) -> list[int]:
        hero_index = self._hero_index or {}
        resolved: list[int] = []

        for hero_name in picks:
            if hero_name is None:
                continue

            normalized = self._normalize(LEGACY_HERO_ALIASES.get(hero_name, hero_name))
            hero = hero_index.get(normalized)

            if hero is not None:
                resolved.append(hero.hero_id)

        return resolved

    def _suggest_for_team(
        self,
        open_slots: list[int],
        allied_ids: list[int],
        enemy_ids: list[int],
        taken_ids: set[int],
        heroes_by_id: dict[int, HeroInfo],
        matchups: dict[int, dict[str, dict[int, float]]],
        meta: dict[int, dict],
        average_win_rate: float,
        top_n: int,
    ) -> dict:
        recommendations: list[Recommendation] = []

        if open_slots:
            recommendations = self._rank_candidates(
                allied_ids=allied_ids,
                enemy_ids=enemy_ids,
                taken_ids=taken_ids,
                heroes_by_id=heroes_by_id,
                matchups=matchups,
                meta=meta,
                average_win_rate=average_win_rate,
                top_n=top_n,
            )

        fills = self._fill_open_slots(
            open_slots=open_slots,
            allied_ids=allied_ids,
            enemy_ids=enemy_ids,
            taken_ids=taken_ids,
            heroes_by_id=heroes_by_id,
            matchups=matchups,
            meta=meta,
            average_win_rate=average_win_rate,
        )

        return {
            "open_slots": open_slots,
            "recommended": [item.to_payload() for item in recommendations],
            "fills": fills,
        }

    def _rank_candidates(
        self,
        allied_ids: list[int],
        enemy_ids: list[int],
        taken_ids: set[int],
        heroes_by_id: dict[int, HeroInfo],
        matchups: dict[int, dict[str, dict[int, float]]],
        meta: dict[int, dict],
        average_win_rate: float,
        top_n: int,
    ) -> list[Recommendation]:
        ranked: list[Recommendation] = []

        for hero_id, hero in heroes_by_id.items():
            if hero_id in taken_ids:
                continue

            meta_row = meta.get(hero_id)
            if meta_row is None or meta_row["match_count"] == 0:
                continue

            synergy_score = self._average_relation(matchups, hero_id, allied_ids, "with")
            counter_score = self._average_relation(matchups, hero_id, enemy_ids, "vs")
            meta_delta = meta_row["win_rate"] - average_win_rate
            total_score = synergy_score + counter_score + meta_delta

            ranked.append(Recommendation(
                hero_id=hero_id,
                short_name=hero.short_name,
                display_name=hero.display_name,
                score=total_score,
                win_rate=meta_row["win_rate"],
                match_count=meta_row["match_count"],
                synergy_score=synergy_score,
                counter_score=counter_score,
                role_ids=hero.role_ids,
            ))

        ranked.sort(
            key=lambda item: (
                item.score,
                item.win_rate,
                item.match_count,
            ),
            reverse=True,
        )

        return ranked[:top_n]

    def _fill_open_slots(
        self,
        open_slots: list[int],
        allied_ids: list[int],
        enemy_ids: list[int],
        taken_ids: set[int],
        heroes_by_id: dict[int, HeroInfo],
        matchups: dict[int, dict[str, dict[int, float]]],
        meta: dict[int, dict],
        average_win_rate: float,
    ) -> list[dict]:
        fills: list[dict] = []
        simulated_allies = list(allied_ids)
        simulated_taken = set(taken_ids)

        for slot in open_slots:
            ranked = self._rank_candidates(
                allied_ids=simulated_allies,
                enemy_ids=enemy_ids,
                taken_ids=simulated_taken,
                heroes_by_id=heroes_by_id,
                matchups=matchups,
                meta=meta,
                average_win_rate=average_win_rate,
                top_n=1,
            )

            if not ranked:
                break

            best = ranked[0]
            simulated_allies.append(best.hero_id)
            simulated_taken.add(best.hero_id)
            fills.append({
                "slot": slot,
                **best.to_payload(),
            })

        return fills

    @staticmethod
    def _relation_map(rows: list[dict], hero_id: int) -> dict[int, float]:
        relations: dict[int, float] = {}

        for row in rows:
            left = row.get("heroId1")
            right = row.get("heroId2")

            if left == hero_id:
                other_id = right
            elif right == hero_id:
                other_id = left
            else:
                other_id = right if right is not None else left

            if other_id is None:
                continue

            relations[other_id] = float(row.get("synergy") or 0.0)

        return relations

    @staticmethod
    def _average_relation(
        matchups: dict[int, dict[str, dict[int, float]]],
        hero_id: int,
        other_ids: list[int],
        relation_type: str,
    ) -> float:
        if not other_ids:
            return 0.0

        relation_rows = matchups.get(hero_id, {}).get(relation_type, {})
        values: list[float] = []

        for other_id in other_ids:
            direct = relation_rows.get(other_id)
            if direct is not None:
                values.append(direct)
                continue

            reverse = matchups.get(other_id, {}).get(relation_type, {}).get(hero_id)
            if reverse is not None:
                values.append(reverse)

        if not values:
            return 0.0

        return fmean(values)

    @staticmethod
    def _average_win_rate(meta: dict[int, dict]) -> float:
        win_rates = [
            row["win_rate"]
            for row in meta.values()
            if row["match_count"] > 0
        ]

        if not win_rates:
            return 0.0

        return fmean(win_rates)

    @staticmethod
    def _open_slots(team_slots) -> list[int]:
        return [
            slot.index
            for slot in team_slots
            if slot.hero is None
        ]

    @staticmethod
    def _normalize(value: str | None) -> str:
        if not value:
            return ""

        return re.sub(r"[^a-z0-9]+", "", value.lower())
