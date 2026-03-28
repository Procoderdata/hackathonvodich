from council_orchestrator import generate_council_response


def _planet(**kwargs):
    base = {
        "id": "Kepler-442 b",
        "category": "habitable_candidate",
        "habitable": True,
        "radius": 1.3,
        "temp": 285,
        "insolation": 0.95,
        "period": 112.4,
        "distance_pc": 120.0,
        "orbit": {"eccentricity": 0.08},
    }
    base.update(kwargs)
    return base


def test_generate_council_response_candidate_found():
    objects = [_planet(), _planet(id="TOI-700 d", period=37.0, temp=270)]
    payload = {
        "mode": "discovery",
        "player_goal": "find potentially habitable worlds",
        "filters": {"showConfirmed": True, "showHabitable": True, "radiusMin": 0.5, "radiusMax": 3.0},
        "recent_actions": ["grid_scan"],
    }

    response = generate_council_response(objects, payload)

    assert response["mission_status"] in {"candidate_found", "candidate_with_risk"}
    assert response["primary_recommendation"]["target_id"]
    assert len(response["council_votes"]) == 3
    assert "evidence_summary" in response


def test_generate_council_response_insufficient_evidence():
    objects = [_planet(radius=10.0, period=6000.0, category="confirmed_planet")]
    payload = {
        "filters": {
            "showConfirmed": False,
            "showHabitable": True,
            "radiusMin": 0.5,
            "radiusMax": 2.0,
            "periodMin": 1,
            "periodMax": 500,
        }
    }

    response = generate_council_response(objects, payload)

    assert response["mission_status"] == "insufficient_evidence"
    assert response["primary_recommendation"]["action"] == "widen_filters"
