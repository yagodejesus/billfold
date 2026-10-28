"""Linha de comando: ``billfold --help``."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import __version__, ler
from .boleto import Boleto, BoletoInvalido, data_do_fator, fator_da_data
from .pix import ChaveInvalida, Pix, PixInvalido, gerar_pix


def _br(valor) -> str:
    if valor is None:
        return "não informado"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mostrar(obj: Boleto | Pix) -> None:
    if isinstance(obj, Pix):
        print(f"Pix {'dinâmico' if obj.dinamico else 'estático'}{' (uso único)' if obj.uso_unico else ''}")
        print(f"  recebedor  {obj.nome} — {obj.cidade}")
        if obj.chave:
            print(f"  chave      {obj.chave} ({obj.tipo_chave})")
        if obj.url:
            print(f"  url        {obj.url}")
        print(f"  valor      {_br(obj.valor)}")
        if obj.txid:
            print(f"  txid       {obj.txid}")
        if obj.descricao:
            print(f"  descrição  {obj.descricao}")
        return
    if obj.tipo == "bancario":
        print(f"Boleto bancário — {obj.nome_banco or 'banco ' + str(obj.banco)} ({obj.banco})")
        venc = obj.vencimento.strftime("%d/%m/%Y") if obj.vencimento else "sem vencimento"
        print(f"  vencimento {venc}{'  ⚠ vencido' if obj.vencido() else ''}")
    else:
        print(f"Arrecadação — {obj.nome_segmento} (empresa/órgão {obj.empresa})")
    print(f"  valor      {_br(obj.valor)}{' (valor de referência)' if obj.valor_e_referencia else ''}")
    print(f"  linha      {obj.linha_formatada}")
    print(f"  barras     {obj.codigo_barras}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="billfold", description="Boletos e Pix: ler, validar e gerar.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    lr = sub.add_parser("ler", help="lê um boleto (linha digitável/código de barras) ou um Pix copia e cola")
    lr.add_argument("codigo", nargs="+")
    lr.add_argument("--json", action="store_true")

    px = sub.add_parser("pix", help="gera um Pix copia e cola")
    px.add_argument("--chave", required=True)
    px.add_argument("--nome", required=True)
    px.add_argument("--cidade", required=True)
    px.add_argument("--valor")
    px.add_argument("--txid")
    px.add_argument("--descricao")
    px.add_argument("--unico", action="store_true", help="QR de uso único")
    px.add_argument("--qr", help="salva o QR Code (.png/.svg) ou '-' para mostrar no terminal")

    fa = sub.add_parser("fator", help="converte data ↔ fator de vencimento")
    fa.add_argument("valor", help="AAAA-MM-DD ou um fator de 4 dígitos")

    a = p.parse_args(argv)
    try:
        if a.comando == "ler":
            obj = ler(" ".join(a.codigo))
            if a.json:
                print(json.dumps(obj.to_dict(), ensure_ascii=False, indent=2))
            else:
                _mostrar(obj)
            return 0
        if a.comando == "pix":
            payload = gerar_pix(a.chave, a.nome, a.cidade, a.valor, a.txid, a.descricao, a.unico)
            print(payload)
            if a.qr:
                from .qr import qr_terminal, salvar_qr

                qr_terminal(payload) if a.qr == "-" else salvar_qr(payload, a.qr)
            return 0
        if a.valor.isdigit():
            d = data_do_fator(int(a.valor))
            print(d.strftime("%d/%m/%Y") if d else "sem vencimento")
        else:
            print(f"{fator_da_data(date.fromisoformat(a.valor)):04d}")
        return 0
    except (BoletoInvalido, PixInvalido, ChaveInvalida, ValueError) as e:
        print(f"inválido: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
