"""QR Codes do Pix (requer o extra ``billfold[qr]``, que instala o ``segno``)."""

from __future__ import annotations

import io
from pathlib import Path

__all__ = ["qr_svg", "salvar_qr", "qr_terminal"]


def _qr(payload: str):
    try:
        import segno
    except ImportError as exc:  # pragma: no cover
        raise ImportError('Para gerar QR Codes instale: pip install "billfold[qr]"') from exc
    return segno.make(payload, error="m", micro=False)


def qr_svg(payload: str, escala: int = 8, cor: str = "#000") -> str:
    buf = io.BytesIO()
    _qr(payload).save(buf, kind="svg", scale=escala, dark=cor, xmldecl=False)
    return buf.getvalue().decode()


def salvar_qr(payload: str, caminho: str | Path, escala: int = 8) -> Path:
    """Salva em .png, .svg, .pdf ou .eps (pela extensão)."""
    caminho = Path(caminho)
    _qr(payload).save(str(caminho), scale=escala)
    return caminho


def qr_terminal(payload: str) -> None:
    _qr(payload).terminal(compact=True)
