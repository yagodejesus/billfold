"""Dígitos verificadores (módulo 10 e 11), CRC16 e validação de CPF/CNPJ."""

from __future__ import annotations

import re

__all__ = ["mod10", "mod11_bancario", "mod11_arrecadacao", "crc16", "cpf_valido", "cnpj_valido"]


def mod10(numero: str) -> int:
    """Módulo 10 da FEBRABAN (pesos 2,1,2,1… da direita para a esquerda)."""
    soma, peso = 0, 2
    for d in reversed(numero):
        p = int(d) * peso
        soma += p // 10 + p % 10
        peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10


def _soma_mod11(numero: str) -> int:
    soma, peso = 0, 2
    for d in reversed(numero):
        soma += int(d) * peso
        peso = 2 if peso == 9 else peso + 1
    return soma % 11


def mod11_bancario(numero: str) -> int:
    """DV geral do código de barras de boletos bancários (0, 10 e 11 viram 1)."""
    dv = 11 - _soma_mod11(numero)
    return 1 if dv in (0, 10, 11) else dv


def mod11_arrecadacao(numero: str) -> int:
    """Módulo 11 dos documentos de arrecadação (contas de consumo e tributos)."""
    resto = _soma_mod11(numero)
    return 0 if resto in (0, 1) else 11 - resto


def crc16(dados: str) -> str:
    """CRC16-CCITT-FALSE (polinômio 0x1021, inicial 0xFFFF), como exige o BR Code do Pix."""
    crc = 0xFFFF
    for byte in dados.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _dv(valores: list[int], pesos: list[int]) -> int:
    resto = sum(v * p for v, p in zip(valores, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def cpf_valido(cpf: str) -> bool:
    d = re.sub(r"\D", "", cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    n = [int(c) for c in d]
    return n[9] == _dv(n[:9], list(range(10, 1, -1))) and n[10] == _dv(n[:10], list(range(11, 1, -1)))


def cnpj_valido(cnpj: str) -> bool:
    """CNPJ numérico ou alfanumérico (julho/2026)."""
    v = re.sub(r"[.\-/\s]", "", cnpj).upper()
    if not re.fullmatch(r"[0-9A-Z]{12}[0-9]{2}", v) or v == v[0] * 14:
        return False
    vals = [ord(c) - 48 for c in v]
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    dv1 = _dv(vals[:12], p1)
    dv2 = _dv(vals[:12] + [dv1], [6, *p1])
    return vals[12] == dv1 and vals[13] == dv2
