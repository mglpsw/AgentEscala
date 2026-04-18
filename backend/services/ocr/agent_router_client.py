"""Cliente OCR remoto via Agent Router.

Camada fina para desacoplar o contrato HTTP da lógica de importação.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, Optional

import httpx


class OcrAgentRouterError(ValueError):
    """Erro funcional do OCR remoto."""


def _extract_text_from_payload(payload: Dict[str, Any]) -> str:
    if isinstance(payload.get("raw_text"), str):
        return payload["raw_text"]
    if isinstance(payload.get("text"), str):
        return payload["text"]
    if isinstance(payload.get("content"), str):
        return payload["content"]

    lines = payload.get("lines")
    if isinstance(lines, list):
        return "\n".join(str(line) for line in lines if line is not None)

    data = payload.get("data")
    if isinstance(data, dict):
        return _extract_text_from_payload(data)

    result = payload.get("result")
    if isinstance(result, dict):
        return _extract_text_from_payload(result)

    return ""


def extract_text_via_agent_router(
    *,
    file_content: bytes,
    filename: str,
    base_url: str,
    timeout_seconds: float,
    verify_ssl: bool,
    endpoint_candidates: tuple[str, ...] = ("/ocr/extract", "/api/ocr/extract", "/extract"),
) -> Dict[str, Any]:
    """Extrai texto via API OCR remota.

    Retorna:
      {"raw_text": str, "source": str, "latency_seconds": float}
    """
    normalized_base = (base_url or "").rstrip("/")
    if not normalized_base:
        raise OcrAgentRouterError("OCR remoto indisponível: base URL não configurada.")

    last_error: Optional[Exception] = None
    for endpoint in endpoint_candidates:
        target_url = f"{normalized_base}{endpoint}"
        started_at = perf_counter()
        try:
            with httpx.Client(timeout=timeout_seconds, verify=verify_ssl) as client:
                response = client.post(
                    target_url,
                    files={"file": (filename, file_content, "application/octet-stream")},
                )
            response.raise_for_status()
            payload = response.json()
            payload_dict = payload if isinstance(payload, dict) else {}
            raw_text = _extract_text_from_payload(payload_dict).strip()
            if not raw_text:
                raise OcrAgentRouterError("OCR remoto retornou payload sem texto reconhecível.")

            return {
                "raw_text": raw_text,
                "source": target_url,
                "latency_seconds": perf_counter() - started_at,
            }
        except Exception as exc:  # pragma: no cover - integração externa
            last_error = exc

    raise OcrAgentRouterError(f"OCR remoto indisponível em {normalized_base}: {last_error}")
