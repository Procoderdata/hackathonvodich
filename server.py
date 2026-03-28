from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
from council_orchestrator import generate_council_response

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TOI_FILE = DATA_DIR / "TOI_2025.10.02_08.11.35.csv"
ORBITAL_FILE = DATA_DIR / "orbital_elements.csv"
ORBITAL_META_FILE = DATA_DIR / "orbital_elements.meta.json"
FRONTEND_DIST_DIR = BASE_DIR / "orrery_component" / "frontend" / "dist"

# Matches frontend baseline date: 2025-03-21 17:49:01 UTC
SIM_EPOCH_JD = (1742579341000 / 86400000.0) + 2440587.5


def safe_float(value, default=0.0):
    """Convert values to float with a fallback."""
    try:
        if pd.notna(value):
            return float(value)
    except Exception:
        pass
    return float(default)


def clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def stable_hash_int(text: str) -> int:
    digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
    return int(digest[:10], 16)


def normalize_epoch_jd(value):
    """
    Normalize an epoch-like value into Julian Day when possible.
    Accepts JD, MJD, and reduced-JD style values.
    Returns None when value is missing or outside realistic range.
    """
    if pd.isna(value):
        return None

    epoch = safe_float(value, 0.0)
    if epoch <= 0:
        return None

    # MJD (roughly 40000-100000) -> JD.
    if 40000 <= epoch <= 100000:
        epoch += 2400000.5
    # Reduced JD style (roughly 1000-200000) -> JD.
    elif 1000 <= epoch <= 200000:
        epoch += 2450000.0

    if not (2000000 <= epoch <= 3000000):
        return None
    return epoch


def normalize_angle_radians(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def solve_kepler_equation(mean_anomaly, eccentricity):
    """Solve M = E - e * sin(E) by Newton-Raphson."""
    m = normalize_angle_radians(mean_anomaly)
    e = clamp(float(eccentricity), 0.0, 0.98)

    if e < 0.8:
        ecc_anomaly = m
    else:
        ecc_anomaly = math.pi

    for _ in range(20):
        f = ecc_anomaly - (e * math.sin(ecc_anomaly)) - m
        fp = 1.0 - (e * math.cos(ecc_anomaly))
        if abs(fp) < 1e-9:
            break
        delta = f / fp
        ecc_anomaly -= delta
        if abs(delta) < 1e-10:
            break

    return ecc_anomaly


def propagate_orbit_position(orbit: dict, julian_day: float):
    """Propagate a Kepler orbit to Cartesian scene coordinates."""
    a = max(0.1, safe_float(orbit.get("semi_major"), 10.0))
    e = clamp(safe_float(orbit.get("eccentricity"), 0.0), 0.0, 0.98)
    i = math.radians(safe_float(orbit.get("inclination_deg"), 0.0))
    omega = math.radians(safe_float(orbit.get("arg_peri_deg"), 0.0))
    node = math.radians(safe_float(orbit.get("node_deg"), 0.0))
    period_days = max(0.1, safe_float(orbit.get("period_days"), 10.0))
    t_peri_jd = safe_float(orbit.get("t_peri_jd"), SIM_EPOCH_JD)

    mean_motion = (2.0 * math.pi) / period_days
    mean_anomaly = mean_motion * (julian_day - t_peri_jd)

    ecc_anomaly = solve_kepler_equation(mean_anomaly, e)
    cos_e = math.cos(ecc_anomaly)
    sin_e = math.sin(ecc_anomaly)

    radius = a * (1.0 - (e * cos_e))

    true_anomaly = 2.0 * math.atan2(
        math.sqrt(1.0 + e) * math.sin(ecc_anomaly / 2.0),
        math.sqrt(max(1e-9, 1.0 - e)) * math.cos(ecc_anomaly / 2.0),
    )

    # Position in orbital plane.
    x_orb = radius * math.cos(true_anomaly)
    z_orb = radius * math.sin(true_anomaly)

    # Rotate by argument of periapsis.
    x1 = (x_orb * math.cos(omega)) - (z_orb * math.sin(omega))
    z1 = (x_orb * math.sin(omega)) + (z_orb * math.cos(omega))

    # Inclination tilt (x axis).
    y2 = z1 * math.sin(i)
    z2 = z1 * math.cos(i)

    # Longitude of ascending node (y axis).
    x3 = (x1 * math.cos(node)) + (z2 * math.sin(node))
    z3 = (-x1 * math.sin(node)) + (z2 * math.cos(node))

    return [x3, y2, z3]


@lru_cache(maxsize=1)
def load_toi_data():
    if not TOI_FILE.exists():
        raise FileNotFoundError(f"Missing TOI file: {TOI_FILE}")
    return pd.read_csv(TOI_FILE, comment="#")


@lru_cache(maxsize=1)
def load_orbital_dataframe():
    if not ORBITAL_FILE.exists():
        raise FileNotFoundError(
            "Missing orbital dataset data/orbital_elements.csv. "
            "Run scripts/refresh_orbital_catalog.py first."
        )

    df = pd.read_csv(ORBITAL_FILE)
    if df.empty:
        raise RuntimeError("Orbital dataset is empty")

    required = {"pl_name", "pl_orbper", "pl_orbsmax"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise RuntimeError(f"Orbital dataset missing columns: {', '.join(missing)}")

    return df


@lru_cache(maxsize=1)
def load_orbital_meta():
    if not ORBITAL_META_FILE.exists():
        return {}

    try:
        return json.loads(ORBITAL_META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def is_habitable(row):
    temp = safe_float(row.get("pl_eqt"), 0)
    radius = safe_float(row.get("pl_rade"), 0)
    insol = safe_float(row.get("pl_insol"), 0)
    return 220 < temp < 330 and 0.7 < radius < 2.2 and 0.3 < insol < 2.2


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


def rank_targets_for_context(objects: list[dict], filters: dict | None) -> list[dict]:
    """Apply context filters and return top-ranked targets."""
    filters = filters or {}
    show_confirmed = bool(filters.get("showConfirmed", True))
    show_habitable = bool(filters.get("showHabitable", True))
    radius_min = safe_float(filters.get("radiusMin"), 0.0)
    radius_max = safe_float(filters.get("radiusMax"), 30.0)
    period_min = safe_float(filters.get("periodMin"), 0.0)
    period_max = safe_float(filters.get("periodMax"), 5000.0)

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


@lru_cache(maxsize=1)
def build_orbital_objects():
    """Build orbital catalog from full orbital elements dataset."""
    df = load_orbital_dataframe().copy()

    for col in [
        "pl_orbper",
        "pl_orbsmax",
        "pl_orbeccen",
        "pl_orbincl",
        "pl_orblper",
        "pl_orbtper",
        "pl_tranmid",
        "pl_rade",
        "pl_bmasse",
        "pl_eqt",
        "pl_insol",
        "sy_dist",
        "ra",
        "dec",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["pl_orbper"].notna() & df["pl_orbsmax"].notna()].copy()

    # Keep a stable and performant set for the browser.
    df.sort_values(by=["pl_orbper", "pl_orbsmax"], ascending=[True, True], inplace=True)
    df = df.head(900)

    objects = []
    for _, row in df.iterrows():
        period_days = max(0.1, safe_float(row.get("pl_orbper"), 10.0))
        semi_major_au = max(0.01, safe_float(row.get("pl_orbsmax"), 0.5))
        eccentricity = clamp(safe_float(row.get("pl_orbeccen"), 0.0), 0.0, 0.95)
        inclination_deg = clamp(safe_float(row.get("pl_orbincl"), 0.0), -85.0, 85.0)
        arg_peri_deg = safe_float(row.get("pl_orblper"), 0.0) % 360

        planet_id = str(row.get("pl_name", "Unknown-Planet"))
        host_name = str(row.get("hostname", "Unknown Star"))

        # pscomppars typically does not provide ascending node. Use deterministic orientation
        # based on sky coordinates and planet id to avoid identical overlap.
        ra_deg = safe_float(row.get("ra"), 0.0)
        node_offset = stable_hash_int(planet_id) % 360
        node_deg = (ra_deg + node_offset) % 360

        # Real epoch only: prefer time of periastron, fallback to transit midpoint.
        t_peri_jd = normalize_epoch_jd(row.get("pl_orbtper"))
        epoch_source = "pl_orbtper"
        if t_peri_jd is None:
            t_peri_jd = normalize_epoch_jd(row.get("pl_tranmid"))
            epoch_source = "pl_tranmid"
        if t_peri_jd is None:
            continue

        radius_earth = clamp(safe_float(row.get("pl_rade"), 1.0), 0.3, 24.0)
        radius_visual = clamp(0.2 + (radius_earth ** 0.62) * 0.11, 0.22, 2.9)

        temp_k = safe_float(row.get("pl_eqt"), 300.0)
        insol = safe_float(row.get("pl_insol"), 1.0)

        # Scene scaling from AU for shared orrery visualization.
        semi_major_scene = clamp(semi_major_au * 34.0, 4.5, 330.0)
        habitable = is_habitable(row)

        objects.append(
            {
                "id": planet_id,
                "star": host_name,
                "category": "habitable_candidate" if habitable else "confirmed_planet",
                "habitable": habitable,
                "size": radius_visual,
                "radius": radius_earth,
                "mass": max(0.1, safe_float(row.get("pl_bmasse"), radius_earth)),
                "period": period_days,
                "temp": temp_k,
                "insolation": insol,
                "distance_pc": safe_float(row.get("sy_dist"), 0.0),
                "orbit": {
                    "semi_major": semi_major_scene,
                    "semi_major_au": semi_major_au,
                    "eccentricity": eccentricity,
                    "inclination_deg": inclination_deg,
                    "arg_peri_deg": arg_peri_deg,
                    "node_deg": node_deg,
                    "period_days": period_days,
                    "t_peri_jd": t_peri_jd,
                    "epoch_source": epoch_source,
                },
            }
        )

    if not objects:
        raise RuntimeError("No orbital objects with valid real epoch found in dataset")

    return objects


@app.route("/")
def index():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return send_file(index_file)
    return jsonify(
        {
            "error": "Frontend build not found",
            "hint": "Run: cd orrery_component/frontend && npm run build",
        }
    ), 500


@app.route("/api/piz-zones")
def get_piz_zones():
    """Get Priority Investigation Zones from TOI data."""
    try:
        toi_df = load_toi_data()
    except Exception as exc:
        return jsonify({"error": f"Failed to load TOI data: {exc}"}), 500

    zones = []
    sample_toi = toi_df.head(24)

    for idx, row in sample_toi.iterrows():
        zone = {
            "id": f"PIZ-{row.get('toi', idx):05.2f}",
            "position": [
                (safe_float(row.get("ra"), 0) % 360 - 180) / 7.5,
                safe_float(row.get("dec"), 0) / 7.5,
                (idx % 8 - 3.5) * 9,
            ],
            "targets": int(max(1, safe_float(row.get("toi"), 1))),
            "priority": "HIGH" if row.get("tfopwg_disp") == "CP" else "MEDIUM",
            "confidence": min(97, max(62, 68 + (idx % 28))),
        }
        zones.append(zone)

    return jsonify(zones)


@app.route("/api/orbital-objects")
def get_orbital_objects():
    """Return catalog with full orbital elements for client-side Kepler propagation."""
    try:
        objects = build_orbital_objects()
    except Exception as exc:
        return jsonify({"error": f"Failed to load orbital catalog: {exc}"}), 500

    if not objects:
        return jsonify({"error": "Orbital catalog is empty"}), 500

    meta = load_orbital_meta()
    habitable_count = sum(1 for obj in objects if obj["habitable"])

    return jsonify(
        {
            "objects": objects,
            "meta": {
                "source": meta.get("source", "NASA Exoplanet Archive TAP / pscomppars"),
                "rows": len(objects),
                "habitable_candidates": habitable_count,
                "refreshed_at_utc": meta.get("refreshed_at_utc", "unknown"),
                "epoch_reference_jd": SIM_EPOCH_JD,
                "epoch_policy": "real_only(pl_orbtper|pl_tranmid)",
                "solver": "kepler_newton",
            },
        }
    )


@app.route("/api/orbital-meta")
def get_orbital_meta():
    """Return lightweight orbital catalog metadata only."""
    try:
        objects = build_orbital_objects()
    except Exception as exc:
        return jsonify({"error": f"Failed to load orbital catalog: {exc}"}), 500

    meta = load_orbital_meta()
    habitable_count = sum(1 for obj in objects if obj["habitable"])
    return jsonify(
        {
            "source": meta.get("source", "NASA Exoplanet Archive TAP / pscomppars"),
            "rows": len(objects),
            "habitable_candidates": habitable_count,
            "refreshed_at_utc": meta.get("refreshed_at_utc", "unknown"),
            "solver": "kepler_newton",
            "epoch_reference_jd": SIM_EPOCH_JD,
            "epoch_policy": "real_only(pl_orbtper|pl_tranmid)",
        }
    )


@app.route("/api/planets")
def get_planets():
    """Legacy endpoint: includes Kepler-propagated position at baseline epoch."""
    try:
        objects = build_orbital_objects()
    except Exception as exc:
        return jsonify({"error": f"Failed to load orbital catalog: {exc}"}), 500

    planets = []
    for idx, data in enumerate(objects[:120]):
        position = propagate_orbit_position(data["orbit"], SIM_EPOCH_JD)
        planets.append(
            {
                "id": data["id"],
                "position": position,
                "size": data["size"],
                "habitable": data["habitable"],
                "mass": data["mass"],
                "radius": data["radius"],
                "period": data["period"],
                "temp": data["temp"],
                "insolation": data["insolation"],
                "category": data["category"],
                "orbit": data["orbit"],
                "index": idx,
            }
        )

    return jsonify(planets)


@app.route("/api/planet/<path:planet_id>")
def get_planet_details(planet_id):
    """Get detailed information about a specific planet."""
    try:
        df = load_orbital_dataframe()
    except Exception as exc:
        return jsonify({"error": f"Failed to load orbital catalog: {exc}"}), 500

    exact = df[df["pl_name"] == planet_id]
    if exact.empty:
        return jsonify({"error": "Planet not found"}), 404

    row = exact.iloc[0]

    radius = safe_float(row.get("pl_rade"), 1.0)
    mass = safe_float(row.get("pl_bmasse"), radius)
    period = safe_float(row.get("pl_orbper"), 10.0)
    temp = safe_float(row.get("pl_eqt"), 300.0)
    insol = safe_float(row.get("pl_insol"), 1.0)
    semi_major = safe_float(row.get("pl_orbsmax"), 0.5)
    eccentricity = clamp(safe_float(row.get("pl_orbeccen"), 0.0), 0.0, 0.95)
    inclination = safe_float(row.get("pl_orbincl"), 0.0)

    details = {
        "id": str(row.get("pl_name", planet_id)),
        "star": str(row.get("hostname", "Unknown Star")),
        "mass": f"{mass:.2f} Earth masses",
        "radius": f"{radius:.2f} Earth radii",
        "period": f"{period:.2f} days",
        "temp": f"{int(temp)}K",
        "insolation": f"{insol:.2f} S⊕",
        "semi_major": f"{semi_major:.3f} AU",
        "eccentricity": f"{eccentricity:.3f}",
        "inclination": f"{inclination:.2f}°",
        "habitable": 220 < temp < 330 and 0.7 < radius < 2.2 and 0.3 < insol < 2.2,
        "distance": f"{safe_float(row.get('sy_dist'), 0.0):.1f} pc",
        "discovery_facility": str(row.get("disc_facility", "Unknown")),
    }

    return jsonify(details)


@app.route("/api/council/respond", methods=["POST"])
def council_respond():
    """
    Deterministic multi-agent style council response.
    Produces structured recommendations without inventing scientific fields.
    """
    payload = request.get_json(silent=True) or {}
    mode = str(payload.get("mode", "discovery")).lower()
    player_goal = str(payload.get("player_goal", "explore promising targets"))
    selected_planet_id = payload.get("selected_planet_id")
    filters = payload.get("filters") or {}
    challenge_state = payload.get("challenge_state") or {}
    recent_actions = payload.get("recent_actions") or []

    try:
        objects = build_orbital_objects()
    except Exception as exc:
        return jsonify({"error": f"Failed to load orbital catalog: {exc}"}), 500

    return jsonify(generate_council_response(objects, payload))
    ranked = rank_targets_for_context(objects, filters)
    if not ranked:
        return jsonify(
            {
                "mission_status": "insufficient_evidence",
                "headline": "Council cannot rank targets under current filters",
                "primary_recommendation": {
                    "action": "widen_filters",
                    "target_id": None,
                    "reason": "Current radius/period constraints removed all candidates",
                },
                "council_votes": [],
                "player_options": ["Widen radius band", "Increase period max", "Enable confirmed planets"],
                "discovery_log_entry": "No candidates available under active constraints.",
            }
        )

    primary = None
    if selected_planet_id:
        primary = next((planet for planet in ranked if planet.get("id") == selected_planet_id), None)
    if primary is None:
        primary = ranked[0]

    votes = build_council_votes(primary, mode)
    caution_votes = [vote for vote in votes if vote["stance"] == "caution"]
    mission_status = "candidate_found" if not caution_votes else "candidate_with_risk"
    recommendation_action = "targeted_scan" if mode in {"discovery", "sandbox"} else "deep_verification"
    active_challenge = bool(challenge_state.get("active", False))

    options = [
        "Run targeted scan",
        "Compare nearest analogs",
        "Open full data dossier",
    ]
    if active_challenge:
        options[0] = "Submit to challenge evaluator"

    headline = f"Council ưu tiên {primary.get('id', 'unknown target')} cho bước kế tiếp"
    if caution_votes:
        headline += " (kèm cảnh báo khí hậu/quỹ đạo)"

    return jsonify(
        {
            "mission_status": mission_status,
            "headline": headline,
            "primary_recommendation": {
                "action": recommendation_action,
                "target_id": primary.get("id"),
                "reason": (
                    f"Scored {primary.get('score', 0):.2f} on baseline habitability under goal '{player_goal}'."
                ),
            },
            "council_votes": votes,
            "player_options": options,
            "discovery_log_entry": (
                f"{primary.get('id')} promoted after council triage. Recent actions: {', '.join(recent_actions[-3:]) or 'n/a'}."
            ),
            "evidence_summary": {
                "radius_earth": round(safe_float(primary.get("radius"), 0.0), 3),
                "temp_k": round(safe_float(primary.get("temp"), 0.0), 2),
                "insolation": round(safe_float(primary.get("insolation"), 0.0), 3),
                "eccentricity": round(safe_float(primary.get("orbit", {}).get("eccentricity"), 0.0), 4),
                "period_days": round(safe_float(primary.get("period"), 0.0), 2),
            },
        }
    )


@app.route("/<path:path>")
def serve_frontend_assets(path):
    """
    Serve built SPA assets from dist and fallback to index.html for client-side routes.
    API paths are excluded and handled by explicit API routes.
    """
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404

    candidate = FRONTEND_DIST_DIR / path
    if candidate.exists() and candidate.is_file():
        return send_from_directory(FRONTEND_DIST_DIR, path)

    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return send_file(index_file)

    return jsonify(
        {
            "error": "Frontend build not found",
            "hint": "Run: cd orrery_component/frontend && npm run build",
        }
    ), 500


if __name__ == "__main__":
    print("Starting Exoplanet Data Server...")
    print("Loading cached datasets...")

    try:
        toi = load_toi_data()
        print(f"Loaded {len(toi)} TOI entries")
    except Exception as exc:
        print(f"TOI load error: {exc}")

    try:
        orbital_objects = build_orbital_objects()
        print(f"Prepared {len(orbital_objects)} orbital objects from {ORBITAL_FILE.name}")
    except Exception as exc:
        print(f"Orbital catalog load error: {exc}")

    print("Server running on http://localhost:5000")
    app.run(debug=True, port=5000)
