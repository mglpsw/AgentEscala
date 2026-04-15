def test_terminal_action_requires_auth(client):
    response = client.post(
        "/api/v1/terminal/action",
        json={"action": "check_disk"},
    )
    assert response.status_code == 401


def test_terminal_action_requires_admin(client, agent_headers):
    response = client.post(
        "/api/v1/terminal/action",
        headers=agent_headers,
        json={"action": "check_disk"},
    )
    assert response.status_code == 403


def test_terminal_action_check_disk_dry_run(client, admin_headers):
    response = client.post(
        "/api/v1/terminal/action",
        headers=admin_headers,
        json={
            "action": "check_disk",
            "dry_run": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "check_disk"
    assert data["success"] is True
    assert data["stdout"] == "[DRY-RUN]"


def test_terminal_action_git_status_dry_run(client, admin_headers):
    response = client.post(
        "/api/v1/terminal/action",
        headers=admin_headers,
        json={
            "action": "git_status",
            "dry_run": True,
        },
    )
    assert response.status_code == 200


def test_terminal_action_unknown_action_returns_error(client, admin_headers):
    response = client.post(
        "/api/v1/terminal/action",
        headers=admin_headers,
        json={
            "action": "destroy_world",
            "dry_run": True,
        },
    )
    assert response.status_code == 400
