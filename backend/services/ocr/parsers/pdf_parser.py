"""Parser OCR de PDF para estrutura base (pré-integração)."""

from __future__ import annotations

from typing import Any


def parse_pdf_to_schedule_rows(file_content: bytes) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Retorna estrutura vazia por padrão.

    Esta implementação é propositalmente conservadora para preparar a base OCR
    sem alterar o comportamento atual do sistema.
    """

    if not file_content:
        return [], [{"code": "OCR_EMPTY_FILE", "message": "Arquivo PDF vazio."}]

    # Placeholder seguro: o pipeline real será conectado em fase futura.
    return [], []
