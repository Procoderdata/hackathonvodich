from __future__ import annotations


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def safe_float(value, default=0.0):
    try:
        if value is not None:
            return float(value)
    except Exception:
        pass
    return float(default)


def compute_habitability_score(planet: dict) -> float:
    """Deterministic baseline score in range [0, 1]."""
    radius = safe_float(planet.get("radius"), 1.0)
    temp = safe_float(planet.get("temp"), 300.0)
    insol = safe_float(planet.get("insolation"), 1.0)
    eccentricity = clamp(safe_float(planet.get("orbit", {}).get("eccentricity"), 0.0), 0.0, 0.95)
    distance_pc = max(0.0, safe_float(planet.get("distance_pc"), 0.0))

    radius_score = max(0.0, 1.0 - (abs(radius - 1.1) / 2.4))
    temp_score = max(0.0, 1.0 - (abs(temp - 288.0) / 220.0))
    insol_score = max(0.0, 1.0 - (abs(insol - 1.0) / 2.6))
    eccentricity_penalty = eccentricity * 0.35
    distance_penalty = min(0.28, distance_pc / 2200.0)

    raw = (0.37 * radius_score) + (0.32 * temp_score) + (0.31 * insol_score)
    return clamp(raw - eccentricity_penalty - distance_penalty, 0.0, 1.0)


def rank_targets_for_context(objects: list[dict], filters) -> list[dict]:
    """Apply context filters and return top-ranked targets."""
    show_confirmed = bool(getattr(filters, "showConfirmed", True))
    show_habitable = bool(getattr(filters, "showHabitable", True))
    radius_min = safe_float(getattr(filters, "radiusMin", 0.0), 0.0)
    radius_max = safe_float(getattr(filters, "radiusMax", 30.0), 30.0)
    period_min = safe_float(getattr(filters, "periodMin", 0.0), 0.0)
    period_max = safe_float(getattr(filters, "periodMax", 5000.0), 5000.0)

    ranked = []
    for item in objects:
        if not show_confirmed and item.get("category") == "confirmed_planet":
            continue
        if not show_habitable and bool(item.get("habitable", False)):
            continue

        radius = safe_float(item.get("radius"), 0.0)
        period = safe_float(item.get("period"), 0.0)
        if radius < radius_min or radius > radius_max:
            continue
        if period < period_min or period > period_max:
            continue

        score = compute_habitability_score(item)
        ranked.append({**item, "score": score})

    ranked.sort(key=lambda planet: (planet["score"], bool(planet.get("habitable", False))), reverse=True)
    return ranked[:25]


def derive_risk_flags(primary: dict) -> list[str]:
    eccentricity = safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0)
    temp = safe_float(primary.get("temp"), 300.0)
    insol = safe_float(primary.get("insolation"), 1.0)
    distance_pc = safe_float(primary.get("distance_pc"), 0.0)
    score = safe_float(primary.get("score"), 0.0)

    flags: list[str] = []
    if eccentricity > 0.22:
        flags.append("elevated_orbital_eccentricity")
    if not (240.0 <= temp <= 340.0):
        flags.append("temperature_outside_reference_band")
    if not (0.45 <= insol <= 1.8):
        flags.append("insolation_outside_reference_band")
    if distance_pc > 1200.0:
        flags.append("very_distant_target")
    if score < 0.33:
        flags.append("low_baseline_habitability_score")
    return flags


def build_evidence_packet(primary: dict, ranked: list[dict], top_k: int = 3) -> dict:
    top_candidates = []
    for item in ranked[: max(1, top_k)]:
        top_candidates.append(
            {
                "id": item.get("id"),
                "score": round(safe_float(item.get("score"), 0.0), 4),
                "radius_earth": round(safe_float(item.get("radius"), 0.0), 3),
                "temp_k": round(safe_float(item.get("temp"), 0.0), 2),
                "insolation": round(safe_float(item.get("insolation"), 0.0), 3),
                "eccentricity": round(safe_float(item.get("orbit", {}).get("eccentricity"), 0.0), 4),
                "period_days": round(safe_float(item.get("period"), 0.0), 2),
                "distance_pc": round(safe_float(item.get("distance_pc"), 0.0), 2),
                "habitable": bool(item.get("habitable", False)),
            }
        )

    return {
        "primary_target": {
            "id": primary.get("id"),
            "score": round(safe_float(primary.get("score"), 0.0), 4),
            "radius_earth": round(safe_float(primary.get("radius"), 0.0), 3),
            "temp_k": round(safe_float(primary.get("temp"), 0.0), 2),
            "insolation": round(safe_float(primary.get("insolation"), 0.0), 3),
            "eccentricity": round(safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0), 4),
            "period_days": round(safe_float(primary.get("period"), 0.0), 2),
            "distance_pc": round(safe_float(primary.get("distance_pc"), 0.0), 2),
            "habitable": bool(primary.get("habitable", False)),
        },
        "risk_flags": derive_risk_flags(primary),
        "top_candidates": top_candidates,
    }


def build_council_votes(primary: dict, mode: str) -> list[dict]:
    score = safe_float(primary.get("score"), 0.0)
    eccentricity = safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0)
    temp = safe_float(primary.get("temp"), 300.0)
    insol = safe_float(primary.get("insolation"), 1.0)
    period = safe_float(primary.get("period"), 0.0)
    risk_flags = derive_risk_flags(primary)

    navigator_conf = clamp(0.45 + (score * 0.5), 0.1, 0.99)
    astro_conf = clamp(0.4 + (score * 0.55), 0.1, 0.99)
    climate_conf = clamp(0.42 + (eccentricity * 0.4) + (abs(insol - 1.0) * 0.06), 0.1, 0.99)
    archivist_conf = clamp(0.55 + (score * 0.25), 0.1, 0.99)

    action_phrase = "targeted follow-up" if mode == "discovery" else "deep verification"
    navigator_stance = "support" if score >= 0.3 else "caution"
    astro_stance = "support" if (0.75 <= safe_float(primary.get("radius"), 0.0) <= 2.3 and 220 <= temp <= 340) else "caution"

    climate_stance = "support"
    if eccentricity > 0.38 or temp < 200 or temp > 390:
        climate_stance = "oppose"
    elif eccentricity > 0.22 or not (240 <= temp <= 340):
        climate_stance = "caution"

    archivist_stance = "support" if climate_stance == "support" and len(risk_flags) <= 1 else "caution"
    risk_phrase = ", ".join(risk_flags[:3]) if risk_flags else "no major risk flags"

    votes = [
        {
            "agent": "Navigator",
            "stance": navigator_stance,
            "confidence": round(navigator_conf, 2),
            "message": (
                f"Recommend {action_phrase} on {primary.get('id', 'the selected target')} "
                "because this target maximizes current exploration value."
            ),
            "evidence_fields": ["pl_orbper", "pl_orbsmax", "sy_dist"],
        },
        {
            "agent": "Astrobiologist",
            "stance": astro_stance,
            "confidence": round(astro_conf, 2),
            "message": (
                "Habitability triad (radius, temperature, insolation) "
                "is within exploratory viability bounds for a follow-up pass."
            ),
            "evidence_fields": ["pl_rade", "pl_eqt", "pl_insol"],
        },
        {
            "agent": "Climate",
            "stance": climate_stance,
            "confidence": round(climate_conf, 2),
            "message": (
                f"Orbital eccentricity={eccentricity:.2f}, period={period:.1f}d suggests uncertainty bands."
                if climate_stance in {"caution", "oppose"}
                else "Orbital stability appears acceptable for current simulation assumptions."
            ),
            "evidence_fields": ["pl_orbeccen", "pl_orbper", "pl_orbincl"],
        },
        {
            "agent": "Archivist",
            "stance": archivist_stance,
            "confidence": round(archivist_conf, 2),
            "message": (
                f"Council split recorded for mission log: {risk_phrase}. "
                "Recommend preserving both support and caution arguments for next turn."
            ),
            "evidence_fields": ["pl_name", "pl_rade", "pl_eqt", "pl_insol", "pl_orbeccen", "pl_orbper"],
        },
    ]

    # Keep explicit scientific debate visible in every turn.
    if all(vote["stance"] == "support" for vote in votes):
        for vote in votes:
            if vote["agent"] == "Climate":
                vote["stance"] = "caution"
                vote["message"] = (
                    f"{vote['message']} "
                    "Caution retained: atmospheric composition remains uncertain in current dataset."
                )
                break

    return votes
