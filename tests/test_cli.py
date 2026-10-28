from datetime import date

import billfold as pg
from billfold.cli import main


def test_ler_boleto_e_pix(capsys):
    b = pg.gerar_boleto("037", "77.50", date(2026, 11, 30), "4" * 25)
    assert main(["ler", b.linha_formatada]) == 0
    out = capsys.readouterr().out
    assert "Banpará" in out and "R$ 77,50" in out and "30/11/2026" in out
    assert main(["ler", "123"]) == 1
    assert "inválido" in capsys.readouterr().err


def test_gerar_pix(capsys):
    assert main(["pix", "--chave", "ana@exemplo.com", "--nome", "Ana", "--cidade", "Belem", "--valor", "10"]) == 0
    payload = capsys.readouterr().out.strip()
    assert pg.pix_valido(payload)


def test_fator(capsys):
    assert main(["fator", "2025-02-22"]) == 0
    assert capsys.readouterr().out.strip() == "1000"
