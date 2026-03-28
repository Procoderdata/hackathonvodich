from __future__ import annotations

from council_schemas import CouncilResponse, CouncilVote, MissionContext
from council_tools import build_council_votes, rank_targets_for_context, safe_float


def generate_council_response(objects: list[dict], payload: dict | None) -> dict:
    context = MissionContext.from_payload(payload)
    ranked = rank_targets_for_context(objects, context.filters)

    if not ranked:
        response = CouncilResponse(
            mission_status="insufficient_evidence",
            headline="Council cannot rank targets under current filters",
            primary_recommendation={
                "action": "widen_filters",
                "target_id": None,
                "reason": "Current radius/period constraints removed all candidates",
            },
            council_votes=[],
            player_options=["Widen radius band", "Increase period max", "Enable confirmed planets"],
            discovery_log_entry="No candidates available under active constraints.",
            evidence_summary=None,
        )
        return response.to_dict()

    primary = None
    if context.selected_planet_id:
        primary = next((planet for planet in ranked if planet.get("id") == context.selected_planet_id), None)
    if primary is None:
        primary = ranked[0]

    votes_payload = build_council_votes(primary, context.mode)
    votes = [CouncilVote(**vote) for vote in votes_payload]
    caution_votes = [vote for vote in votes if vote.stance == "caution"]

    mission_status = "candidate_found" if not caution_votes else "candidate_with_risk"
    recommendation_action = "targeted_scan" if context.mode in {"discovery", "sandbox"} else "deep_verification"

    options = ["Run targeted scan", "Compare nearest analogs", "Open full data dossier"]
    if context.challenge_state.active:
        options[0] = "Submit to challenge evaluator"

    headline = f"Council ưu tiên {primary.get('id', 'unknown target')} cho bước kế tiếp"
    if caution_votes:
        headline += " (kèm cảnh báo khí hậu/quỹ đạo)"

    response = CouncilResponse(
        mission_status=mission_status,
        headline=headline,
        primary_recommendation={
            "action": recommendation_action,
            "target_id": primary.get("id"),
            "reason": f"Scored {primary.get('score', 0):.2f} on baseline habitability under goal '{context.player_goal}'.",
        },
        council_votes=votes,
        player_options=options,
        discovery_log_entry=(
            f"{primary.get('id')} promoted after council triage. "
            f"Recent actions: {', '.join(context.recent_actions[-3:]) or 'n/a'}."
        ),
        evidence_summary={
            "radius_earth": round(safe_float(primary.get("radius"), 0.0), 3),
            "temp_k": round(safe_float(primary.get("temp"), 0.0), 2),
            "insolation": round(safe_float(primary.get("insolation"), 0.0), 3),
            "eccentricity": round(safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0), 4),
            "period_days": round(safe_float(primary.get("period"), 0.0), 2),
        },
    )

    return response.to_dict()
