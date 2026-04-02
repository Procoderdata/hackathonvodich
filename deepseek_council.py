from __future__ import annotations

import json
import os
from typing import Any

import requests


ROLE_ORDER = ["Navigator", "Astrobiologist", "Climate", "Archivist"]
VALID_STANCES = {"support", "caution", "oppose"}
ROLE_KEY_ENV = {
    "Navigator": "DEEPSEEK_API_KEY_NAVIGATOR",
    "Astrobiologist": "DEEPSEEK_API_KEY_ASTROBIOLOGIST",
    "Climate": "DEEPSEEK_API_KEY_CLIMATE",
    "Archivist": "DEEPSEEK_API_KEY_ARCHIVIST",
}


def _resolve_role_keys() -> dict[str, str]:
    role_keys: dict[str, str] = {}

    # Convenience: comma-separated in role order.
    csv_keys = os.getenv("DEEPSEEK_API_KEYS", "")
    if csv_keys.strip():
        parts = [part.strip() for part in csv_keys.split(",") if part.strip()]
        for idx, role in enumerate(ROLE_ORDER):
            if idx < len(parts):
                role_keys[role] = parts[idx]

    # Explicit role env vars override csv values.
    for role, env_name in ROLE_KEY_ENV.items():
        value = os.getenv(env_name, "").strip()
        if value:
            role_keys[role] = value

    # Single-key fallback for all roles.
    fallback_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if fallback_key:
        for role in ROLE_ORDER:
            role_keys.setdefault(role, fallback_key)

    return role_keys


def deepseek_enabled() -> bool:
    return any(bool(value) for value in _resolve_role_keys().values())


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _safe_confidence(value: Any, fallback: float) -> float:
    try:
        return round(_clamp(float(value), 0.05, 0.99), 2)
    except (TypeError, ValueError):
        return round(_clamp(float(fallback), 0.05, 0.99), 2)


def _extract_json_object(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return text[start : end + 1]


def _text_or_default(value: Any, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "none":
        return default
    return text


def _normalize_vote(role: str, raw_vote: dict | None, fallback_vote: dict) -> dict:
    raw_vote = raw_vote or {}

    stance = str(raw_vote.get("stance", fallback_vote.get("stance", "caution"))).strip().lower()
    if stance not in VALID_STANCES:
        stance = str(fallback_vote.get("stance", "caution"))

    message = str(raw_vote.get("message", fallback_vote.get("message", ""))).strip()
    if not message:
        message = str(fallback_vote.get("message", "No rationale provided."))

    evidence_fields = raw_vote.get("evidence_fields")
    if not isinstance(evidence_fields, list):
        evidence_fields = fallback_vote.get("evidence_fields", [])
    evidence_fields = [str(field) for field in evidence_fields if str(field).strip()][:8]
    if not evidence_fields:
        evidence_fields = [str(field) for field in fallback_vote.get("evidence_fields", [])][:8]

    return {
        "agent": role,
        "stance": stance,
        "confidence": _safe_confidence(raw_vote.get("confidence"), fallback_vote.get("confidence", 0.6)),
        "message": message,
        "evidence_fields": evidence_fields,
    }


def _normalize_player_options(raw_options: Any, fallback: list[str]) -> list[str]:
    if not isinstance(raw_options, list):
        return list(fallback)

    options = [str(item).strip() for item in raw_options if str(item).strip()]
    if len(options) < 3:
        return list(fallback)
    return options[:3]


def _default_recommendation(raw_recommendation: Any, fallback: dict, target_id: str | None) -> dict:
    if not isinstance(raw_recommendation, dict):
        return dict(fallback)

    action = _text_or_default(raw_recommendation.get("action"), str(fallback.get("action", "targeted_scan")))
    reason = _text_or_default(raw_recommendation.get("reason"), str(fallback.get("reason", "")))

    selected_target = raw_recommendation.get("target_id")
    if selected_target is None:
        selected_target = fallback.get("target_id", target_id)

    return {
        "action": action,
        "target_id": str(selected_target) if selected_target is not None else target_id,
        "reason": reason,
    }


def _call_deepseek(api_key: str, messages: list[dict[str, str]], temperature: float = 0.2) -> dict | None:
    url = os.getenv("DEEPSEEK_API_BASE_URL", "https://api.deepseek.com/chat/completions")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    timeout_seconds = float(os.getenv("DEEPSEEK_TIMEOUT_SEC", "22"))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
        return json.loads(_extract_json_object(content))
    except Exception:
        return None


def _build_role_messages(
    role: str,
    mission_context: dict[str, Any],
    evidence_packet: dict[str, Any],
    fallback_vote: dict[str, Any],
    debate_context: list[dict[str, Any]],
    fallback: dict[str, Any],
) -> list[dict[str, str]]:
    role_directives = {
        "Navigator": (
            "You optimize target selection and next action. "
            "Bias toward actionable mission progression, not generic explanation."
        ),
        "Astrobiologist": (
            "You assess habitability potential and biological plausibility. "
            "Ground arguments in temperature, radius, insolation and uncertainty."
        ),
        "Climate": (
            "You are the skeptical reviewer. "
            "Actively challenge optimistic assumptions with orbital and climate risks."
        ),
        "Archivist": (
            "You preserve explainability and narrative continuity. "
            "Summarize disagreement clearly and keep recommendations auditable."
        ),
    }

    contract: dict[str, Any] = {
        "agent": role,
        "stance": "support|caution|oppose",
        "confidence": "0.05..0.99",
        "message": "short scientific rationale",
        "evidence_fields": ["dataset_field_names"],
    }
    if role == "Navigator":
        contract["recommended_action"] = "optional action string"
        contract["recommended_target_id"] = "optional target id"
        contract["recommended_reason"] = "optional concise reason"
    if role == "Archivist":
        contract["headline"] = "optional mission headline"
        contract["discovery_log_entry"] = "optional mission log line"
        contract["player_options"] = ["optional option 1", "optional option 2", "optional option 3"]

    system_prompt = (
        f"You are {role} in the ATLAS Science Council.\n"
        f"{role_directives.get(role, '')}\n"
        "Strict rules:\n"
        "1) Use only grounded evidence provided.\n"
        "2) Never invent missing scientific measurements.\n"
        "3) Return a single valid JSON object only (no markdown)."
    )

    user_payload = {
        "task": f"Produce one council vote for role={role}",
        "contract": contract,
        "mission_context": mission_context,
        "grounded_evidence_packet": evidence_packet,
        "debate_context_so_far": debate_context,
        "fallback_vote": fallback_vote,
        "fallback_baseline": fallback,
        "output_requirements": {
            "role": role,
            "language": "Vietnamese-friendly concise technical style",
        },
    }

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]


def generate_deepseek_council_payload(
    mission_context: dict[str, Any],
    evidence_packet: dict[str, Any],
    fallback: dict[str, Any],
) -> dict | None:
    role_keys = _resolve_role_keys()
    if not any(role_keys.values()):
        return None

    fallback_votes = {
        str(vote.get("agent")): vote for vote in fallback.get("council_votes", []) if isinstance(vote, dict)
    }
    role_outputs: dict[str, dict] = {}
    debate_context: list[dict[str, Any]] = []

    for role in ROLE_ORDER:
        fallback_vote = fallback_votes.get(role) or {
            "agent": role,
            "stance": "caution",
            "confidence": 0.55,
            "message": "Fallback vote generated due to model mismatch.",
            "evidence_fields": [],
        }

        role_key = role_keys.get(role, "")
        if not role_key:
            continue

        parsed = _call_deepseek(
            api_key=role_key,
            messages=_build_role_messages(
                role=role,
                mission_context=mission_context,
                evidence_packet=evidence_packet,
                fallback_vote=fallback_vote,
                debate_context=debate_context,
                fallback=fallback,
            ),
            temperature=0.2 if role != "Climate" else 0.15,
        )

        if isinstance(parsed, dict):
            role_outputs[role] = parsed
            debate_context.append(
                {
                    "agent": role,
                    "stance": parsed.get("stance", fallback_vote.get("stance", "caution")),
                    "message": parsed.get("message", fallback_vote.get("message", "")),
                }
            )

    normalized_votes = []
    for role in ROLE_ORDER:
        fallback_vote = fallback_votes.get(role) or {
            "agent": role,
            "stance": "caution",
            "confidence": 0.55,
            "message": "Fallback vote generated due to model mismatch.",
            "evidence_fields": [],
        }
        normalized_votes.append(_normalize_vote(role, role_outputs.get(role), fallback_vote))

    # Keep explicit disagreement if all roles support.
    if all(vote["stance"] == "support" for vote in normalized_votes):
        for vote in normalized_votes:
            if vote["agent"] == "Climate":
                vote["stance"] = "caution"
                vote["message"] = (
                    f"{vote['message']} Caution retained: uncertainty remains in atmospheric and orbital assumptions."
                )
                break

    # Ensure mission recommendation fields are not empty.
    navigator_output = role_outputs.get("Navigator", {})
    archivist_output = role_outputs.get("Archivist", {})

    recommendation = _default_recommendation(
        {
            "action": navigator_output.get("recommended_action"),
            "target_id": navigator_output.get("recommended_target_id"),
            "reason": navigator_output.get("recommended_reason"),
        },
        fallback.get("primary_recommendation", {}),
        fallback.get("primary_recommendation", {}).get("target_id"),
    )

    return {
        "headline": _text_or_default(archivist_output.get("headline"), str(fallback.get("headline", ""))),
        "primary_recommendation": recommendation,
        "council_votes": normalized_votes,
        "player_options": _normalize_player_options(
            archivist_output.get("player_options"), fallback.get("player_options", [])
        ),
        "discovery_log_entry": _text_or_default(
            archivist_output.get("discovery_log_entry"),
            str(fallback.get("discovery_log_entry", "")),
        ),
    }
