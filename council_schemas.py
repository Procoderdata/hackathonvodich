from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MissionFilters:
    showConfirmed: bool = True
    showHabitable: bool = True
    radiusMin: float = 0.0
    radiusMax: float = 30.0
    periodMin: float = 0.0
    periodMax: float = 5000.0


@dataclass
class ChallengeState:
    active: bool = False
    objective: str = ""
    progress: int = 0


@dataclass
class MissionContext:
    mode: str = "discovery"
    player_goal: str = "explore promising targets"
    selected_planet_id: str | None = None
    selected_piz_id: str | None = None
    filters: MissionFilters = field(default_factory=MissionFilters)
    challenge_state: ChallengeState = field(default_factory=ChallengeState)
    recent_actions: list[str] = field(default_factory=list)

    @staticmethod
    def from_payload(payload: dict[str, Any] | None) -> "MissionContext":
        payload = payload or {}
        filters_payload = payload.get("filters") or {}
        challenge_payload = payload.get("challenge_state") or {}

        return MissionContext(
            mode=str(payload.get("mode", "discovery")).lower(),
            player_goal=str(payload.get("player_goal", "explore promising targets")),
            selected_planet_id=payload.get("selected_planet_id"),
            selected_piz_id=payload.get("selected_piz_id"),
            filters=MissionFilters(
                showConfirmed=bool(filters_payload.get("showConfirmed", True)),
                showHabitable=bool(filters_payload.get("showHabitable", True)),
                radiusMin=float(filters_payload.get("radiusMin", 0.0)),
                radiusMax=float(filters_payload.get("radiusMax", 30.0)),
                periodMin=float(filters_payload.get("periodMin", 0.0)),
                periodMax=float(filters_payload.get("periodMax", 5000.0)),
            ),
            challenge_state=ChallengeState(
                active=bool(challenge_payload.get("active", False)),
                objective=str(challenge_payload.get("objective", "")),
                progress=int(challenge_payload.get("progress", 0)),
            ),
            recent_actions=[str(item) for item in (payload.get("recent_actions") or [])],
        )


@dataclass
class CouncilVote:
    agent: str
    stance: str
    confidence: float
    message: str
    evidence_fields: list[str]


@dataclass
class CouncilResponse:
    mission_status: str
    headline: str
    primary_recommendation: dict[str, Any]
    council_votes: list[CouncilVote]
    player_options: list[str]
    discovery_log_entry: str
    evidence_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["council_votes"] = [asdict(vote) for vote in self.council_votes]
        return payload
