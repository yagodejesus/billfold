<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img src="assets/logo.svg" alt="billfold" width="420">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/yagodejesus/billfold/actions/workflows/ci.yml"><img src="https://github.com/yagodejesus/billfold/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/billfold/"><img src="https://img.shields.io/pypi/v/billfold.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/billfold/"><img src="https://img.shields.io/pypi/pyversions/billfold.svg" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT"></a>
</p>

**Boletos e Pix sem dor de cabeça: leia, valide e gere linhas digitáveis, códigos de barras e Pix copia e cola.**

> 🇺🇸 *Parse, validate and generate Brazilian payment codes: boleto barcodes and "linha digitável" (bank slips and utility bills) and Pix "copia e cola" (EMV BR Code), including the 2025 due-date factor rollover. Zero dependencies.*

```python
import billfold

b = billfold.ler("03791.23458 67890.123457 67890.123457 2 16460000125000")   # qualquer formato, com ou sem pontos
b.nome_banco, b.valor, b.vencimento        # ('Banpará', Decimal('1250.00'), date(2026, 11, 30))

pix = billfold.gerar_pix("(91) 98765-4321", "Açaí da Dona Maria", "Bragança", valor="25,90", txid="PEDIDO42")
# '00020126360014br.gov.bcb.pix0114+5591987654321520400005303986540525.905802BR5918Acai da Dona Maria...'
billfold.ler(pix).valor                          # Decimal('25.90')
```

## Por que esta biblioteca

- **O fator de vencimento de 2025.** Em 22/02/2025 o fator de vencimento dos boletos chegou a 9999 e voltou para 1000. Código que soma o fator a 07/10/1997 passou a mostrar vencimentos em **2000**. Aqui o fator é resolvido pelas duas datas-base e a mais próxima é escolhida — testado nas duas pontas da virada.
- **Erros que dizem o que está errado.** "dígito verificador do campo 2 da linha digitável não confere" em vez de "inválido". Bom para mostrar ao usuário que digitou.
- **Pix testado contra o exemplo oficial do Banco Central** (CRC16 incluído).
- **Tudo em um lugar:** boleto bancário (47 dígitos), arrecadação/convênio — contas de luz, água, telefone, tributos e multas (48 dígitos, módulo 10 e 11) — código de barras (44) e Pix estático e dinâmico.
- **Zero dependências**, Python 3.10+, valores em `Decimal`, tipado. QR Code opcional com `billfold[qr]`.

## Instalação

```bash
pip install billfold
pip install "billfold[qr]"   # para gerar a imagem do QR Code
```

## Boletos

```python
b = billfold.ler_boleto("8383 0000000-4 89900123123-5 45678901234-1 56789012345-7")
b.tipo            # 'arrecadacao'
b.nome_segmento   # 'Energia elétrica e gás'
b.valor           # Decimal('89.90')

billfold.boleto_valido(texto_digitado)          # True/False, sem exceção
b.linha_formatada                         # '03791.23458 67890.123457 ...'
b.codigo_barras                           # os 44 dígitos (para gerar o código de barras)
b.vencido()                               # compara com hoje
b.to_dict()                               # pronto para JSON
```

| Campo | Bancário | Arrecadação |
|---|---|---|
| `valor` | `Decimal` ou `None` (valor em aberto) | `Decimal` (`valor_e_referencia=True` quando é referência) |
| `vencimento`, `fator_vencimento` | data resolvida e o fator bruto | — |
| `banco`, `nome_banco` | código COMPE e nome | — |
| `segmento`, `nome_segmento`, `empresa` | — | segmento FEBRABAN e código da empresa (ou CNPJ) |

Também dá para **gerar** boletos válidos — útil em testes automatizados e para quem emite cobranças:

```python
from datetime import date
billfold.gerar_boleto("341", "1234.56", date(2026, 12, 31), campo_livre="1234567890123456789012345")
billfold.gerar_arrecadacao(segmento=3, valor="89.90", empresa="0123", campo_livre="...", modulo=11)
billfold.fator_da_data(date(2025, 2, 22))       # 1000
billfold.data_do_fator(1000)                    # date(2025, 2, 22)
```

## Pix

```python
p = billfold.ler_pix(codigo_copia_e_cola)       # valida o CRC e a estrutura
p.chave, p.tipo_chave, p.nome, p.cidade, p.valor, p.txid, p.descricao, p.dinamico

billfold.gerar_pix(chave, nome, cidade, valor=None, txid=None, descricao=None, uso_unico=False)
billfold.gerar_pix_dinamico("https://pix.seupsp.com.br/qr/v2/abc", "Loja", "Belem", valor=10)

billfold.tipo_chave("(91) 98765-4321")          # 'telefone'
billfold.normalizar_chave("(91) 98765-4321")    # '+5591987654321'
```

As chaves são normalizadas e validadas: CPF e CNPJ (inclusive o **CNPJ alfanumérico**), e-mail, telefone (`+55DDDNÚMERO`) e chave aleatória. Nome e cidade perdem acentos e são cortados em 25 e 15 caracteres, como pede o padrão.

QR Code (com `billfold[qr]`):

```python
from billfold.qr import salvar_qr, qr_svg
salvar_qr(pix, "pix.png")                 # ou .svg / .pdf
svg = qr_svg(pix)                         # para embutir numa página
```

## Linha de comando

```bash
billfold ler "03791.23458 67890.123457 67890.123457 2 16460000125000"
# Boleto bancário — Banpará (037)
#   vencimento 30/11/2026
#   valor      R$ 1.250,00
#   ...

billfold ler "00020126580014br.gov.bcb.pix..." --json
billfold pix --chave ana@exemplo.com --nome "Ana" --cidade "Belem" --valor 10 --qr pix.png
billfold pix --chave ana@exemplo.com --nome "Ana" --cidade "Belem" --qr -     # QR no terminal
billfold fator 2025-02-22                                                     # 1000
```

## Limitações

- O **campo livre** dos boletos (nosso número, agência, conta…) tem layout próprio de cada banco e não é decodificado.
- Pix dinâmico: a biblioteca lê e gera o BR Code, mas não busca o payload JSON na URL do PSP.
- Validar a estrutura não garante que o boleto ou a cobrança existam — isso só o banco confirma.

## Desenvolvimento

```bash
git clone https://github.com/yagodejesus/billfold && cd billfold
pip install -e ".[dev]"
pytest && ruff check .
```

## Licença

MIT © Yago de Jesus Martins
