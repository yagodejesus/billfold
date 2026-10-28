"""Pix copia e cola (BR Code): leitura, validação e geração."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .modulos import cnpj_valido, cpf_valido, crc16

__all__ = [
    "Pix",
    "PixInvalido",
    "ChaveInvalida",
    "ler_pix",
    "pix_valido",
    "gerar_pix",
    "gerar_pix_dinamico",
    "normalizar_chave",
    "tipo_chave",
]

GUI = "br.gov.bcb.pix"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_TXID = re.compile(r"[A-Za-z0-9]{1,25}")


class PixInvalido(ValueError):
    """BR Code malformado ou com CRC errado."""


class ChaveInvalida(ValueError):
    """A chave Pix não é CPF, CNPJ, e-mail, telefone ou chave aleatória válidos."""


@dataclass(frozen=True)
class Pix:
    payload: str
    chave: str | None
    tipo_chave: str | None
    nome: str
    cidade: str
    valor: Decimal | None
    txid: str | None
    descricao: str | None = None
    url: str | None = None
    cep: str | None = None
    uso_unico: bool = False
    campos: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def dinamico(self) -> bool:
        return self.url is not None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["valor"] = str(self.valor) if self.valor is not None else None
        d["dinamico"] = self.dinamico
        d.pop("campos")
        return d


# ------------------------------------------------------------------------------ chaves
def normalizar_chave(chave: str) -> str:
    """Deixa a chave no formato que vai no BR Code (telefone como +55DDDNUMERO, e-mail minúsculo…)."""
    c = chave.strip()
    if _UUID.fullmatch(c):
        return c.lower()
    if "@" in c:
        if not _EMAIL.fullmatch(c) or len(c) > 77:
            raise ChaveInvalida(f"e-mail inválido: {chave}")
        return c.lower()
    alnum = re.sub(r"[.\-/\s]", "", c).upper()
    if len(alnum) == 14 and not alnum.isdigit() and cnpj_valido(alnum):
        return alnum
    d = re.sub(r"\D", "", c)
    if c.startswith("+"):
        if d.startswith("55") and len(d) in (12, 13):
            return "+" + d
        raise ChaveInvalida(f"telefone inválido (use +55DDDNUMERO): {chave}")
    parece_telefone = bool(re.search(r"[()]", c)) or bool(re.fullmatch(r"\d{2}\s?9?\d{4}-\d{4}", c))
    if len(d) == 11 and cpf_valido(d) and not parece_telefone:
        return d
    if len(d) == 14 and cnpj_valido(d):
        return d
    if len(d) in (10, 11) and d[0] != "0":
        return "+55" + d
    if len(d) in (12, 13) and d.startswith("55"):
        return "+" + d
    raise ChaveInvalida(f"não reconheço a chave Pix: {chave}")


def tipo_chave(chave: str) -> str:
    """``"cpf"``, ``"cnpj"``, ``"email"``, ``"telefone"`` ou ``"aleatoria"``."""
    c = normalizar_chave(chave)
    if _UUID.fullmatch(c):
        return "aleatoria"
    if "@" in c:
        return "email"
    if c.startswith("+"):
        return "telefone"
    return "cpf" if len(c) == 11 else "cnpj"


# ----------------------------------------------------------------------------- leitura
def _tlv(texto: str) -> list[tuple[str, str]]:
    campos, i = [], 0
    while i < len(texto):
        tag, tamanho = texto[i : i + 2], texto[i + 2 : i + 4]
        if not (tag.isdigit() and tamanho.isdigit()):
            raise PixInvalido(f"campo malformado na posição {i}")
        n = int(tamanho)
        valor = texto[i + 4 : i + 4 + n]
        if len(valor) != n:
            raise PixInvalido(f"campo {tag} declara {n} caracteres, mas o texto acabou")
        campos.append((tag, valor))
        i += 4 + n
    return campos


def ler_pix(texto: str, validar_crc: bool = True) -> Pix:
    """Lê um Pix copia e cola. Levanta :class:`PixInvalido` com o motivo se algo estiver errado."""
    payload = texto.strip()
    if not payload.startswith("000201"):
        raise PixInvalido("não começa com 000201 (Payload Format Indicator)")
    if validar_crc:
        if len(payload) < 8 or payload[-8:-4] != "6304":
            raise PixInvalido("CRC ausente (o código deve terminar com 6304XXXX)")
        esperado = crc16(payload[:-4])
        if payload[-4:].upper() != esperado:
            raise PixInvalido(
                f"CRC não confere: {payload[-4:]} (esperado {esperado}) — o código foi alterado ou cortado"
            )
    campos = dict(_tlv(payload))
    conta = None
    for tag in [f"{n:02d}" for n in range(26, 52)]:
        if tag in campos:
            sub = dict(_tlv(campos[tag]))
            if sub.get("00", "").lower() == GUI:
                conta = sub
                break
    if conta is None:
        raise PixInvalido("não há conta Pix (GUI br.gov.bcb.pix) no código")
    if campos.get("53", "986") != "986":
        raise PixInvalido("moeda diferente de Real (986)")
    adicionais = dict(_tlv(campos["62"])) if "62" in campos else {}
    chave = conta.get("01")
    txid = adicionais.get("05")
    return Pix(
        payload=payload,
        chave=chave,
        tipo_chave=tipo_chave(chave) if chave else None,
        nome=campos.get("59", ""),
        cidade=campos.get("60", ""),
        valor=Decimal(campos["54"]) if "54" in campos else None,
        txid=None if txid in (None, "***") else txid,
        descricao=conta.get("02"),
        url=conta.get("25"),
        cep=campos.get("61"),
        uso_unico=campos.get("01") == "12",
        campos=campos,
    )


def pix_valido(texto: str) -> bool:
    try:
        ler_pix(texto)
        return True
    except (PixInvalido, ChaveInvalida):
        return False


# ----------------------------------------------------------------------------- geração
def _f(tag: str, valor: str) -> str:
    if len(valor) > 99:
        raise ValueError(f"campo {tag} passa de 99 caracteres")
    return f"{tag}{len(valor):02d}{valor}"


def _ascii(texto: str, limite: int) -> str:
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    s = " ".join(re.sub(r"[^A-Za-z0-9 .,\-/&]", " ", s).split())
    if not s:
        raise ValueError("texto vazio depois de remover caracteres especiais")
    return s[:limite].rstrip()


def _valor(valor: Decimal | float | str | None) -> str | None:
    if valor in (None, ""):
        return None
    v = Decimal(str(valor).replace(",", ".")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    if v <= 0:
        raise ValueError("o valor precisa ser maior que zero")
    if len(str(v)) > 13:
        raise ValueError("valor grande demais")
    return str(v)


def _montar(conta: str, nome: str, cidade: str, valor, txid: str, uso_unico: bool, cep: str | None) -> str:
    corpo = _f("00", "01")
    if uso_unico:
        corpo += _f("01", "12")
    corpo += _f("26", conta) + _f("52", "0000") + _f("53", "986")
    v = _valor(valor)
    if v:
        corpo += _f("54", v)
    corpo += _f("58", "BR") + _f("59", _ascii(nome, 25)) + _f("60", _ascii(cidade, 15))
    if cep:
        corpo += _f("61", re.sub(r"\D", "", cep))
    corpo += _f("62", _f("05", txid)) + "6304"
    return corpo + crc16(corpo)


def gerar_pix(
    chave: str,
    nome: str,
    cidade: str,
    valor: Decimal | float | str | None = None,
    txid: str | None = None,
    descricao: str | None = None,
    uso_unico: bool = False,
    cep: str | None = None,
) -> str:
    """Gera um Pix copia e cola estático.

    Nome (até 25) e cidade (até 15) perdem acentos e são cortados, como pede o padrão.
    ``txid`` tem até 25 letras/números; sem ele, usa ``***``.
    """
    if txid is not None and not _TXID.fullmatch(txid):
        raise ValueError("txid deve ter de 1 a 25 letras ou números, sem espaços")
    conta = _f("00", GUI) + _f("01", normalizar_chave(chave))
    if descricao:
        conta += _f("02", _ascii(descricao, 99 - len(conta) - 4))
    return _montar(conta, nome, cidade, valor, txid or "***", uso_unico, cep)


def gerar_pix_dinamico(
    url: str, nome: str, cidade: str, valor: Decimal | float | str | None = None, uso_unico: bool = True
) -> str:
    """Gera um Pix copia e cola dinâmico, que aponta para a URL do payload (fornecida pelo PSP)."""
    local = re.sub(r"^https?://", "", url.strip())
    conta = _f("00", GUI) + _f("25", local)
    return _montar(conta, nome, cidade, valor, "***", uso_unico, None)
