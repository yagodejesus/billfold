from decimal import Decimal

import pytest

import billfold as pg

# Exemplo publicado no Manual do BR Code do Banco Central.
EXEMPLO_BCB = (
    "00020126580014br.gov.bcb.pix0136123e4567-e12b-12d1-a456-426655440000"
    "5204000053039865802BR5913Fulano de Tal6008BRASILIA62070503***63041D3D"
)


def test_exemplo_oficial_do_banco_central():
    p = pg.ler_pix(EXEMPLO_BCB)
    assert p.chave == "123e4567-e12b-12d1-a456-426655440000" and p.tipo_chave == "aleatoria"
    assert (p.nome, p.cidade, p.valor, p.txid) == ("Fulano de Tal", "BRASILIA", None, None)


def test_crc_errado_e_detectado():
    with pytest.raises(pg.PixInvalido, match="CRC"):
        pg.ler_pix(EXEMPLO_BCB[:-1] + "E")
    assert not pg.pix_valido(EXEMPLO_BCB.replace("Fulano", "Fulana"))


def test_gerar_e_ler():
    s = pg.gerar_pix("ana@exemplo.com", "Ana Lúcia Conceição", "Bragança", valor="25,9", txid="PED42", descricao="Açaí")
    p = pg.ler(s)
    assert isinstance(p, pg.Pix)
    assert p.chave == "ana@exemplo.com" and p.tipo_chave == "email"
    assert p.nome == "Ana Lucia Conceicao" and p.cidade == "Braganca"
    assert p.valor == Decimal("25.90") and p.txid == "PED42" and p.descricao == "Acai"


def test_limites_de_nome_e_cidade():
    p = pg.ler_pix(pg.gerar_pix("ana@exemplo.com", "N" * 40, "Cidade Com Nome Comprido", 1))
    assert len(p.nome) == 25 and len(p.cidade) <= 15


@pytest.mark.parametrize(
    "chave,esperada,tipo",
    [
        ("529.982.247-25", "52998224725", "cpf"),
        ("11.222.333/0001-81", "11222333000181", "cnpj"),
        ("12.ABC.345/01DE-35", "12ABC34501DE35", "cnpj"),
        ("(91) 98765-4321", "+5591987654321", "telefone"),
        ("+55 91 98765-4321", "+5591987654321", "telefone"),
        ("Ana@Exemplo.com", "ana@exemplo.com", "email"),
        ("123E4567-E12B-12D1-A456-426655440000", "123e4567-e12b-12d1-a456-426655440000", "aleatoria"),
    ],
)
def test_chaves(chave, esperada, tipo):
    assert pg.normalizar_chave(chave) == esperada
    assert pg.tipo_chave(chave) == tipo


def test_chave_invalida():
    with pytest.raises(pg.ChaveInvalida):
        pg.normalizar_chave("123")
    with pytest.raises(pg.ChaveInvalida):
        pg.normalizar_chave("+1 555 1234")


def test_validacoes_de_entrada():
    with pytest.raises(ValueError):
        pg.gerar_pix("ana@exemplo.com", "Ana", "Belem", valor=0)
    with pytest.raises(ValueError):
        pg.gerar_pix("ana@exemplo.com", "Ana", "Belem", txid="com espaço")


def test_pix_dinamico_e_uso_unico():
    s = pg.gerar_pix_dinamico("https://pix.meupsp.com.br/qr/v2/abc123", "Loja", "Belem", valor=10)
    p = pg.ler_pix(s)
    assert p.dinamico and p.url == "pix.meupsp.com.br/qr/v2/abc123" and p.uso_unico
    assert p.chave is None


def test_qr_code(tmp_path):
    pytest.importorskip("segno")
    from billfold.qr import qr_svg, salvar_qr

    s = pg.gerar_pix("ana@exemplo.com", "Ana", "Belem", 5)
    assert qr_svg(s).startswith("<svg")
    assert salvar_qr(s, tmp_path / "pix.png").stat().st_size > 100
