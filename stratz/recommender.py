from __future__ import annotations

from dataclasses import dataclass
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


META_STATS_QUERY = """
query MetaStats($metaTake: Int!) {
  heroStats {
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


HERO_MATCHUP_QUERY = """
query HeroMatchup($heroId: Short!) {
  heroStats {
    heroVsHeroMatchup(heroId: $heroId, bracketBasicIds: [DIVINE_IMMORTAL]) {
      advantage {
        heroId
        with {
          heroId2
          synergy
        }
        vs {
          heroId2
          synergy
        }
      }
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
        self._matchup_cache: dict[int, dict[str, dict[int, float]]] = {}

    def suggest(self, analysis: DraftAnalysis, top_n: int = 5) -> dict:
        heroes_by_id = self._load_heroes()
        meta = self._load_meta()

        radiant_ids = self._resolve_team(analysis.radiant_picks)
        dire_ids = self._resolve_team(analysis.dire_picks)
        taken = set(radiant_ids) | set(dire_ids)

        all_draft_ids = list(set(radiant_ids + dire_ids))
        matchups = self._load_hero_matchups(all_draft_ids)

        radiant_synergy = self._team_synergy(matchups, radiant_ids)
        dire_synergy = self._team_synergy(matchups, dire_ids)

        return {
            "source": "STRATZ",
            "radiant": {
                "team_synergy_score": round(radiant_synergy, 4),
                **self._suggest_for_team(
                    open_slots=self._open_slots(analysis.radiant),
                    allied_ids=radiant_ids,
                    enemy_ids=dire_ids,
                    taken_ids=taken,
                    heroes_by_id=heroes_by_id,
                    meta=meta,
                    top_n=top_n,
                ),
            },
            "dire": {
                "team_synergy_score": round(dire_synergy, 4),
                **self._suggest_for_team(
                    open_slots=self._open_slots(analysis.dire),
                    allied_ids=dire_ids,
                    enemy_ids=radiant_ids,
                    taken_ids=taken,
                    heroes_by_id=heroes_by_id,
                    meta=meta,
                    top_n=top_n,
                ),
            },
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

    def _load_meta(self) -> dict[int, dict]:
        if self._meta is not None:
            return self._meta

        take = len(self._load_heroes()) + 16
        data = self.client.execute(
            META_STATS_QUERY,
            variables={"metaTake": take},
        )

        meta: dict[int, dict] = {}
        for row in data["heroStats"].get("winWeek", []):
            hero_id = row["heroId"]
            match_count = row.get("matchCount") or 0
            win_count = row.get("winCount") or 0
            meta[hero_id] = {
                "match_count": match_count,
                "win_rate": 0.0 if match_count == 0 else win_count / match_count,
            }

        self._meta = meta
        return meta

    def _load_hero_matchups(
        self, hero_ids: list[int]
    ) -> dict[int, dict[str, dict[int, float]]]:
        for hero_id in hero_ids:
            if hero_id in self._matchup_cache:
                continue

            data = self.client.execute(
                HERO_MATCHUP_QUERY,
                variables={"heroId": hero_id},
            )

            advantage_list = (
                data.get("heroStats", {})
                .get("heroVsHeroMatchup", {})
                .get("advantage", [])
            )

            entry = next(
                (e for e in advantage_list if e.get("heroId") == hero_id),
                advantage_list[0] if advantage_list else None,
            )

            if entry is not None:
                self._matchup_cache[hero_id] = {
                    "with": self._relation_map(entry.get("with", [])),
                    "vs": self._relation_map(entry.get("vs", [])),
                }
            else:
                self._matchup_cache[hero_id] = {"with": {}, "vs": {}}

        return {hid: self._matchup_cache[hid] for hid in hero_ids}

    def _load_hero_matchup(self, hero_id: int) -> dict[str, dict[int, float]]:
        return self._load_hero_matchups([hero_id])[hero_id]

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
        meta: dict[int, dict],
        top_n: int,
    ) -> dict:
        recommendations: list[Recommendation] = []

        if open_slots:
            recommendations = self._rank_candidates(
                allied_ids=allied_ids,
                enemy_ids=enemy_ids,
                taken_ids=taken_ids,
                heroes_by_id=heroes_by_id,
                meta=meta,
                top_n=top_n,
            )

        fills = self._fill_open_slots(
            open_slots=open_slots,
            allied_ids=allied_ids,
            enemy_ids=enemy_ids,
            taken_ids=taken_ids,
            heroes_by_id=heroes_by_id,
            meta=meta,
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
        meta: dict[int, dict],
        top_n: int,
    ) -> list[Recommendation]:
        ranked: list[Recommendation] = []

        for hero_id, hero in heroes_by_id.items():
            if hero_id in taken_ids:
                continue

            meta_row = meta.get(hero_id)
            if meta_row is None or meta_row["match_count"] == 0:
                continue

            hero_matchups = self._load_hero_matchup(hero_id)
            synergy_score = self._sum_relation(hero_matchups.get("with", {}), allied_ids)
            counter_score = self._sum_relation(hero_matchups.get("vs", {}), enemy_ids)
            total_score = synergy_score + counter_score

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
        meta: dict[int, dict],
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
                meta=meta,
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
    def _team_synergy(
        matchups: dict[int, dict[str, dict[int, float]]], team_ids: list[int]
    ) -> float:
        total = 0.0
        for i, hero_a in enumerate(team_ids):
            for hero_b in team_ids[i + 1:]:
                syn = matchups.get(hero_a, {}).get("with", {}).get(hero_b)
                if syn is None:
                    syn = matchups.get(hero_b, {}).get("with", {}).get(hero_a)
                if syn is not None:
                    total += syn
        return total

    @staticmethod
    def _relation_map(rows: list[dict]) -> dict[int, float]:
        relations: dict[int, float] = {}

        for row in rows:
            other_id = row.get("heroId2")

            if other_id is None:
                continue

            relations[other_id] = float(row.get("synergy") or 0.0)

        return relations

    @staticmethod
    def _sum_relation(
        relation_rows: dict[int, float],
        other_ids: list[int],
    ) -> float:
        return sum(relation_rows.get(other_id, 0.0) for other_id in other_ids)

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
