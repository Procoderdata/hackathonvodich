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


def build_council_votes(primary: dict, mode: str) -> list[dict]:
    score = safe_float(primary.get("score"), 0.0)
    eccentricity = safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0)
    temp = safe_float(primary.get("temp"), 300.0)
    insol = safe_float(primary.get("insolation"), 1.0)
    period = safe_float(primary.get("period"), 0.0)

    navigator_conf = clamp(0.45 + (score * 0.5), 0.1, 0.99)
    astro_conf = clamp(0.4 + (score * 0.55), 0.1, 0.99)
    climate_conf = clamp(0.42 + (eccentricity * 0.4) + (abs(insol - 1.0) * 0.06), 0.1, 0.99)

    action_phrase = "targeted follow-up" if mode == "discovery" else "deep verification"
    climate_stance = "caution" if eccentricity > 0.22 or not (240 <= temp <= 340) else "support"

    return [
        {
            "agent": "Navigator",
            "stance": "support",
            "confidence": round(navigator_conf, 2),
            "message": f"Recommend {action_phrase} on {primary.get('id', 'the selected target')} based on ranking gain.",
            "evidence_fields": ["pl_orbper", "pl_orbsmax", "sy_dist"],
        },
        {
            "agent": "Astrobiologist",
            "stance": "support",
            "confidence": round(astro_conf, 2),
            "message": "Radius-temperature-insolation triad is within exploratory viability bounds.",
            "evidence_fields": ["pl_rade", "pl_eqt", "pl_insol"],
        },
        {
            "agent": "Climate",
            "stance": climate_stance,
            "confidence": round(climate_conf, 2),
            "message": (
                f"Orbital eccentricity={eccentricity:.2f}, period={period:.1f}d suggests uncertainty bands."
                if climate_stance == "caution"
                else "Orbital stability appears acceptable for current simulation assumptions."
            ),
            "evidence_fields": ["pl_orbeccen", "pl_orbper", "pl_orbincl"],
        },
    ]
