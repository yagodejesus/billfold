"""Boletos bancários e documentos de arrecadação (contas de consumo, tributos, multas)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from .bancos import BANCOS, SEGMENTOS
from .modulos import mod10, mod11_arrecadacao, mod11_bancario

__all__ = [
    "Boleto",
    "BoletoInvalido",
    "ler_boleto",
    "boleto_valido",
    "gerar_boleto",
    "gerar_arrecadacao",
    "data_do_fator",
    "fator_da_data",
    "BASE_ANTIGA",
    "BASE_NOVA",
]

BASE_ANTIGA = date(1997, 10, 7)
#: Em 22/02/2025 o fator de vencimento chegou a 9999 e voltou para 1000 — nova data-base.
BASE_NOVA = date(2022, 5, 29)


class BoletoInvalido(ValueError):
    """Código de barras ou linha digitável inválido (o texto explica o motivo)."""


@dataclass(frozen=True)
class Boleto:
    tipo: str  # "bancario" ou "arrecadacao"
    codigo_barras: str
    linha_digitavel: str
    valor: Decimal | None
    vencimento: date | None = None
    banco: str | None = None
    nome_banco: str | None = None
    fator_vencimento: int | None = None
    segmento: int | None = None
    nome_segmento: str | None = None
    empresa: str | None = None
    valor_e_referencia: bool = False
    campo_livre: str = ""

    @property
    def linha_formatada(self) -> str:
        l = self.linha_digitavel
        if self.tipo == "bancario":
            return f"{l[:5]}.{l[5:10]} {l[10:15]}.{l[15:21]} {l[21:26]}.{l[26:32]} {l[32]} {l[33:]}"
        return " ".join(f"{l[i : i + 11]}-{l[i + 11]}" for i in range(0, 48, 12))

    def vencido(self, hoje: date | None = None) -> bool:
        return self.vencimento is not None and self.vencimento < (hoje or date.today())

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["valor"] = str(self.valor) if self.valor is not None else None
        d["vencimento"] = self.vencimento.isoformat() if self.vencimento else None
        d["linha_formatada"] = self.linha_formatada
        return d


# ------------------------------------------------------------------ fator de vencimento
def data_do_fator(fator: int, referencia: date | None = None) -> date | None:
    """Converte o fator de vencimento em data.

    Desde 22/02/2025 o fator reiniciou em 1000, então cada fator corresponde a duas datas
    (base 07/10/1997 e base 29/05/2022). Escolhe a mais próxima de ``referencia`` (hoje).
    ``0`` significa boleto sem vencimento.
    """
    if fator == 0:
        return None
    if not 1000 <= fator <= 9999:
        raise BoletoInvalido(f"fator de vencimento inválido: {fator:04d}")
    ref = referencia or date.today()
    opcoes = (BASE_ANTIGA + timedelta(days=fator), BASE_NOVA + timedelta(days=fator))
    return min(opcoes, key=lambda d: abs((d - ref).days))


def fator_da_data(vencimento: date) -> int:
    """Fator de vencimento (4 dígitos) de uma data a partir de 03/07/2000."""
    dias = (vencimento - BASE_ANTIGA).days
    if dias < 1000:
        raise ValueError("datas anteriores a 03/07/2000 não têm fator de vencimento")
    return dias if dias <= 9999 else (vencimento - BASE_NOVA).days


# ----------------------------------------------------------------------------- leitura
def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def _linha_bancaria_para_barras(l: str) -> str:
    campos = [(l[0:9], l[9], 1), (l[10:20], l[20], 2), (l[21:31], l[31], 3)]
    for numero, dv, i in campos:
        if mod10(numero) != int(dv):
            raise BoletoInvalido(f"dígito verificador do campo {i} da linha digitável não confere")
    return l[0:4] + l[32] + l[33:47] + l[4:9] + l[10:20] + l[21:31]


def _barras_bancario_para_linha(b: str) -> str:
    livre = b[19:44]
    c1 = b[0:4] + livre[0:5]
    c2 = livre[5:15]
    c3 = livre[15:25]
    return f"{c1}{mod10(c1)}{c2}{mod10(c2)}{c3}{mod10(c3)}{b[4]}{b[5:19]}"


def _modulo_arrecadacao(b: str):
    if b[2] in "67":
        return mod10
    if b[2] in "89":
        return mod11_arrecadacao
    raise BoletoInvalido(f"identificador de valor inválido na 3ª posição: {b[2]}")


def _linha_arrecadacao_para_barras(l: str) -> str:
    modulo = _modulo_arrecadacao(l)
    blocos = [l[i : i + 12] for i in range(0, 48, 12)]
    for i, bloco in enumerate(blocos, 1):
        if modulo(bloco[:11]) != int(bloco[11]):
            raise BoletoInvalido(f"dígito verificador do bloco {i} da linha digitável não confere")
    return "".join(b[:11] for b in blocos)


def _barras_arrecadacao_para_linha(b: str) -> str:
    modulo = _modulo_arrecadacao(b)
    return "".join(b[i : i + 11] + str(modulo(b[i : i + 11])) for i in range(0, 44, 11))


def _bancario(barras: str, linha: str, referencia: date | None) -> Boleto:
    if barras[3] != "9":
        raise BoletoInvalido("código de moeda diferente de 9 (Real)")
    if mod11_bancario(barras[:4] + barras[5:]) != int(barras[4]):
        raise BoletoInvalido("dígito verificador geral do código de barras não confere")
    fator = int(barras[5:9])
    valor = (Decimal(int(barras[9:19])) / 100).quantize(Decimal("0.01"))
    return Boleto(
        tipo="bancario",
        codigo_barras=barras,
        linha_digitavel=linha,
        valor=valor if valor else None,
        vencimento=data_do_fator(fator, referencia),
        banco=barras[:3],
        nome_banco=BANCOS.get(barras[:3]),
        fator_vencimento=fator,
        campo_livre=barras[19:],
    )


def _arrecadacao(barras: str, linha: str) -> Boleto:
    modulo = _modulo_arrecadacao(barras)
    if modulo(barras[:3] + barras[4:]) != int(barras[3]):
        raise BoletoInvalido("dígito verificador geral do código de barras não confere")
    segmento = int(barras[1])
    empresa = barras[15:23] if segmento == 6 else barras[15:19]
    return Boleto(
        tipo="arrecadacao",
        codigo_barras=barras,
        linha_digitavel=linha,
        valor=(Decimal(int(barras[4:15])) / 100).quantize(Decimal("0.01")),
        segmento=segmento,
        nome_segmento=SEGMENTOS.get(segmento),
        empresa=empresa,
        valor_e_referencia=barras[2] in "79",
        campo_livre=barras[19:] if segmento != 6 else barras[23:],
    )


def ler_boleto(texto: str, referencia: date | None = None) -> Boleto:
    """Lê uma linha digitável (47 ou 48 dígitos) ou um código de barras (44 dígitos).

    Pontos, espaços e hífens são ignorados. Levanta :class:`BoletoInvalido` com o motivo.
    """
    d = _digitos(texto)
    if len(d) == 44:
        if d[0] == "8":
            return _arrecadacao(d, _barras_arrecadacao_para_linha(d))
        return _bancario(d, _barras_bancario_para_linha(d), referencia)
    if len(d) == 47:
        return _bancario(_linha_bancaria_para_barras(d), d, referencia)
    if len(d) == 48:
        if d[0] != "8":
            raise BoletoInvalido("linha de 48 dígitos deve começar com 8 (arrecadação)")
        return _arrecadacao(_linha_arrecadacao_para_barras(d), d)
    raise BoletoInvalido(f"esperava 44, 47 ou 48 dígitos, recebi {len(d)}")


def boleto_valido(texto: str) -> bool:
    try:
        ler_boleto(texto)
        return True
    except BoletoInvalido:
        return False


# ----------------------------------------------------------------------------- geração
def gerar_boleto(banco: str, valor: Decimal | float | str, vencimento: date | None, campo_livre: str) -> Boleto:
    """Monta um boleto bancário válido (útil para testes e para quem emite boletos).

    O ``campo_livre`` (25 dígitos) segue o layout de cada banco e não é validado aqui.
    """
    banco = _digitos(banco).zfill(3)
    livre = _digitos(campo_livre)
    if len(livre) != 25:
        raise ValueError("o campo livre precisa ter 25 dígitos")
    centavos = int((Decimal(str(valor)) * 100).quantize(Decimal(1)))
    fator = fator_da_data(vencimento) if vencimento else 0
    sem_dv = f"{banco}9{fator:04d}{centavos:010d}{livre}"
    barras = sem_dv[:4] + str(mod11_bancario(sem_dv)) + sem_dv[4:]
    return ler_boleto(barras, referencia=vencimento)


def gerar_arrecadacao(
    segmento: int, valor: Decimal | float | str, empresa: str, campo_livre: str, modulo: int = 10
) -> Boleto:
    """Monta um código de arrecadação válido (valor efetivo, módulo 10 ou 11)."""
    centavos = int((Decimal(str(valor)) * 100).quantize(Decimal(1)))
    ident = "6" if modulo == 10 else "8"
    tamanho_empresa = 8 if segmento == 6 else 4
    corpo = _digitos(empresa).zfill(tamanho_empresa) + _digitos(campo_livre)
    if len(corpo) != 29:
        raise ValueError(f"empresa + campo livre precisam somar 29 dígitos (tem {len(corpo)})")
    sem_dv = f"8{segmento}{ident}{centavos:011d}{corpo}"
    func = mod10 if modulo == 10 else mod11_arrecadacao
    barras = sem_dv[:3] + str(func(sem_dv)) + sem_dv[3:]
    return ler_boleto(barras)
