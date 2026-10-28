from datetime import date
from decimal import Decimal

import pytest

import billfold as pg
from billfold.modulos import mod10, mod11_bancario


def test_modulos():
    assert mod10("341911111") == 1
    assert mod11_bancario("0" * 43) == 1  # restos 0/10/11 viram 1


def test_fator_de_vencimento_antes_e_depois_do_reinicio_de_2025():
    assert pg.data_do_fator(1000, date(2000, 8, 1)) == date(2000, 7, 3)
    assert pg.data_do_fator(9999, date(2025, 1, 1)) == date(2025, 2, 21)
    assert pg.data_do_fator(1000, date(2025, 3, 1)) == date(2025, 2, 22)
    assert pg.fator_da_data(date(2025, 2, 21)) == 9999
    assert pg.fator_da_data(date(2025, 2, 22)) == 1000
    assert pg.data_do_fator(0) is None
    with pytest.raises(pg.BoletoInvalido):
        pg.data_do_fator(999)
    with pytest.raises(ValueError):
        pg.fator_da_data(date(1999, 1, 1))


def test_gerar_e_ler_boleto_bancario():
    b = pg.gerar_boleto("341", "1234.56", date(2026, 12, 31), "1234567890" * 2 + "12345")
    assert b.tipo == "bancario" and b.nome_banco == "Itaú Unibanco"
    assert b.valor == Decimal("1234.56") and b.vencimento == date(2026, 12, 31)
    assert len(b.linha_digitavel) == 47 and len(b.codigo_barras) == 44
    lido = pg.ler_boleto(b.linha_formatada, referencia=date(2026, 12, 1))
    assert lido == b
    assert pg.ler_boleto(b.codigo_barras, referencia=date(2026, 12, 1)) == b


def test_boleto_sem_valor_e_sem_vencimento():
    b = pg.gerar_boleto("001", 0, None, "0" * 25)
    assert b.valor is None and b.vencimento is None


@pytest.mark.parametrize("posicao", [3, 15, 25, 32, 40])
def test_qualquer_digito_trocado_e_detectado(posicao):
    linha = pg.gerar_boleto("237", "99.90", date(2027, 1, 15), "9" * 25).linha_digitavel
    trocado = linha[:posicao] + str((int(linha[posicao]) + 1) % 10) + linha[posicao + 1 :]
    assert pg.boleto_valido(linha)
    assert not pg.boleto_valido(trocado)


def test_mensagens_de_erro_claras():
    linha = pg.gerar_boleto("104", "10", date(2026, 6, 1), "5" * 25).linha_digitavel
    with pytest.raises(pg.BoletoInvalido, match="campo 2"):
        pg.ler_boleto(linha[:12] + str((int(linha[12]) + 1) % 10) + linha[13:])
    with pytest.raises(pg.BoletoInvalido, match="44, 47 ou 48"):
        pg.ler_boleto("123")


@pytest.mark.parametrize("modulo", [10, 11])
def test_arrecadacao(modulo):
    a = pg.gerar_arrecadacao(3, "89.90", "0123", "1234567890123456789012345", modulo=modulo)
    assert a.tipo == "arrecadacao" and a.nome_segmento == "Energia elétrica e gás"
    assert a.valor == Decimal("89.90") and a.empresa == "0123"
    assert len(a.linha_digitavel) == 48
    assert pg.ler_boleto(a.linha_formatada) == a
    errado = a.linha_digitavel[:5] + str((int(a.linha_digitavel[5]) + 1) % 10) + a.linha_digitavel[6:]
    assert not pg.boleto_valido(errado)


def test_arrecadacao_com_cnpj():
    a = pg.gerar_arrecadacao(6, "150", "11222333", "123456789012345678901")
    assert a.empresa == "11222333"


def test_to_dict_e_vencido():
    b = pg.gerar_boleto("341", "50", date(2026, 1, 10), "1" * 25)
    d = b.to_dict()
    assert d["valor"] == "50.00" and d["vencimento"] == "2026-01-10"
    assert b.vencido(date(2026, 2, 1)) and not b.vencido(date(2026, 1, 1))
