from datetime import datetime, timedelta

from backend.services.schedule_validation_service import validate_schedule


def test_validate_schedule_detects_overlap_and_limits():
    base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    shifts = [
        {
            "id": 1,
            "agent_id": 10,
            "start_time": base,
            "end_time": base + timedelta(hours=8),
        },
        {
            "id": 2,
            "agent_id": 10,
            "start_time": base + timedelta(hours=4),
            "end_time": base + timedelta(hours=12),
        },
    ]

    errors = validate_schedule(shifts, max_daily_hours=10, max_weekly_hours=20)
    codes = {error["code"] for error in errors}

    assert "OVERLAPPING_SHIFTS" in codes
    assert "DAILY_HOURS_EXCEEDED" in codes


def test_create_shift_rejects_overlap(client, admin_headers, agent_headers):
    shifts_response = client.get("/shifts", headers=agent_headers)
    assert shifts_response.status_code == 200
    existing_shift = shifts_response.json()[0]

    payload = {
        "agent_id": existing_shift["agent_id"],
        "start_time": existing_shift["start_time"],
        "end_time": existing_shift["end_time"],
        "title": "Conflitante",
    }
    response = client.post("/shifts/", headers=admin_headers, json=payload)

    assert response.status_code == 400
    assert "OVERLAPPING_SHIFTS" in response.json()["detail"]


def test_admin_validate_schedule_preview_endpoint(client, admin_headers):
    base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    response = client.post(
        "/admin/schedule/validate",
        headers=admin_headers,
        json={
            "preview": True,
            "shifts": [
                {
                    "shift_id": 100,
                    "agent_id": 77,
                    "start_time": base.isoformat(),
                    "end_time": (base + timedelta(hours=10)).isoformat(),
                },
                {
                    "shift_id": 101,
                    "agent_id": 77,
                    "start_time": (base + timedelta(hours=8)).isoformat(),
                    "end_time": (base + timedelta(hours=16)).isoformat(),
                },
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["preview"] is True
    assert payload["valid"] is False
    assert any(error["code"] == "OVERLAPPING_SHIFTS" for error in payload["errors"])
