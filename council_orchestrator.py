from __future__ import annotations

from council_schemas import CouncilResponse, CouncilVote, MissionContext
from council_tools import build_council_votes, build_evidence_packet, rank_targets_for_context, safe_float
from deepseek_council import deepseek_enabled, generate_deepseek_council_payload


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

    recommendation_action = "targeted_scan" if context.mode in {"discovery", "sandbox"} else "deep_verification"
    options = ["Run targeted scan", "Compare nearest analogs", "Open full data dossier"]
    if context.challenge_state.active:
        options[0] = "Submit to challenge evaluator"

    evidence_packet = build_evidence_packet(primary, ranked, top_k=3)
    baseline_headline = f"Council ưu tiên {primary.get('id', 'unknown target')} cho bước kế tiếp"
    baseline_discovery_log = (
        f"{primary.get('id')} promoted after council triage. "
        f"Recent actions: {', '.join(context.recent_actions[-3:]) or 'n/a'}."
    )
    baseline_response_payload = {
        "headline": baseline_headline,
        "primary_recommendation": {
            "action": recommendation_action,
            "target_id": primary.get("id"),
            "reason": f"Scored {primary.get('score', 0):.2f} on baseline habitability under goal '{context.player_goal}'.",
        },
        "council_votes": build_council_votes(primary, context.mode),
        "player_options": options,
        "discovery_log_entry": baseline_discovery_log,
    }

    selected_payload = baseline_response_payload
    if deepseek_enabled():
        llm_payload = generate_deepseek_council_payload(
            mission_context={
                "mode": context.mode,
                "player_goal": context.player_goal,
                "selected_planet_id": context.selected_planet_id,
                "selected_piz_id": context.selected_piz_id,
                "filters": {
                    "showConfirmed": context.filters.showConfirmed,
                    "showHabitable": context.filters.showHabitable,
                    "radiusMin": context.filters.radiusMin,
                    "radiusMax": context.filters.radiusMax,
                    "periodMin": context.filters.periodMin,
                    "periodMax": context.filters.periodMax,
                },
                "challenge_state": {
                    "active": context.challenge_state.active,
                    "objective": context.challenge_state.objective,
                    "progress": context.challenge_state.progress,
                },
                "recent_actions": context.recent_actions[-8:],
            },
            evidence_packet=evidence_packet,
            fallback=baseline_response_payload,
        )
        if llm_payload:
            selected_payload = llm_payload

    votes = [CouncilVote(**vote) for vote in selected_payload.get("council_votes", [])]
    caution_votes = [vote for vote in votes if vote.stance in {"caution", "oppose"}]
    mission_status = "candidate_found" if not caution_votes else "candidate_with_risk"

    response = CouncilResponse(
        mission_status=mission_status,
        headline=selected_payload.get("headline", baseline_headline),
        primary_recommendation=selected_payload.get("primary_recommendation", baseline_response_payload["primary_recommendation"]),
        council_votes=votes,
        player_options=selected_payload.get("player_options", options),
        discovery_log_entry=selected_payload.get("discovery_log_entry", baseline_discovery_log),
        evidence_summary={
            "radius_earth": round(safe_float(primary.get("radius"), 0.0), 3),
            "temp_k": round(safe_float(primary.get("temp"), 0.0), 2),
            "insolation": round(safe_float(primary.get("insolation"), 0.0), 3),
            "eccentricity": round(safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0), 4),
            "period_days": round(safe_float(primary.get("period"), 0.0), 2),
            "baseline_score": round(safe_float(primary.get("score"), 0.0), 4),
            "risk_flags": evidence_packet.get("risk_flags", []),
            "candidate_count": len(ranked),
        },
    )

    return response.to_dict()
