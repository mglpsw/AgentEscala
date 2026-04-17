from backend.config.settings import settings


def test_api_info_exposes_ocr_block_with_timeout(client):
    response = client.get("/api/v1/info")

    assert response.status_code == 200
    payload = response.json()
    assert "ocr" in payload
    assert payload["ocr"]["api_enabled"] in {True, False}
    assert isinstance(payload["ocr"]["api_timeout_seconds"], (float, int))
    assert payload["ocr"]["api_timeout_seconds"] == settings.OCR_API_TIMEOUT_SECONDS


def test_api_info_reflects_ocr_enabled_toggle(client, monkeypatch):
    monkeypatch.setattr(settings, "OCR_API_ENABLED", True)
    enabled_response = client.get("/api/v1/info")
    assert enabled_response.status_code == 200
    assert enabled_response.json()["ocr"]["api_enabled"] is True

    monkeypatch.setattr(settings, "OCR_API_ENABLED", False)
    disabled_response = client.get("/api/v1/info")
    assert disabled_response.status_code == 200
    assert disabled_response.json()["ocr"]["api_enabled"] is False


def test_api_info_does_not_expose_secret_key(client):
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    payload = response.text.lower()

    assert "secret_key" not in payload
    assert "hashed_password" not in payload
