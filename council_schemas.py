from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ALLOWED_MODES = {"sandbox", "challenge", "discovery"}


def _parse_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _normalize_range(min_value: float, max_value: float, lower_bound: float, upper_bound: float) -> tuple[float, float]:
    min_value = max(lower_bound, min(upper_bound, min_value))
    max_value = max(lower_bound, min(upper_bound, max_value))
    if min_value > max_value:
        min_value, max_value = max_value, min_value
    return min_value, max_value


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

        mode = str(payload.get("mode", "discovery")).lower()
        if mode not in ALLOWED_MODES:
            mode = "discovery"

        radius_min, radius_max = _normalize_range(
            _parse_float(filters_payload.get("radiusMin"), 0.0),
            _parse_float(filters_payload.get("radiusMax"), 30.0),
            0.0,
            50.0,
        )
        period_min, period_max = _normalize_range(
            _parse_float(filters_payload.get("periodMin"), 0.0),
            _parse_float(filters_payload.get("periodMax"), 5000.0),
            0.0,
            20000.0,
        )

        raw_actions = payload.get("recent_actions") or []
        if not isinstance(raw_actions, list):
            raw_actions = [raw_actions]
        recent_actions = [str(item) for item in raw_actions[-20:]]

        selected_planet_id = payload.get("selected_planet_id")
        selected_piz_id = payload.get("selected_piz_id")

        return MissionContext(
            mode=mode,
            player_goal=str(payload.get("player_goal", "explore promising targets")),
            selected_planet_id=str(selected_planet_id) if selected_planet_id is not None else None,
            selected_piz_id=str(selected_piz_id) if selected_piz_id is not None else None,
            filters=MissionFilters(
                showConfirmed=_parse_bool(filters_payload.get("showConfirmed", True), True),
                showHabitable=_parse_bool(filters_payload.get("showHabitable", True), True),
                radiusMin=radius_min,
                radiusMax=radius_max,
                periodMin=period_min,
                periodMax=period_max,
            ),
            challenge_state=ChallengeState(
                active=_parse_bool(challenge_payload.get("active", False), False),
                objective=str(challenge_payload.get("objective", "")),
                progress=max(0, _parse_int(challenge_payload.get("progress", 0), 0)),
            ),
            recent_actions=recent_actions,
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
