"""billfold — boletos e Pix sem dor de cabeça: leia, valide e gere linhas digitáveis e Pix copia e cola."""

__version__ = "0.1.0"

from .boleto import (
    Boleto,
    BoletoInvalido,
    boleto_valido,
    data_do_fator,
    fator_da_data,
    gerar_arrecadacao,
    gerar_boleto,
    ler_boleto,
)
from .pix import (
    ChaveInvalida,
    Pix,
    PixInvalido,
    gerar_pix,
    gerar_pix_dinamico,
    ler_pix,
    normalizar_chave,
    pix_valido,
    tipo_chave,
)


def ler(texto: str) -> Boleto | Pix:
    """Identifica e lê qualquer código de pagamento: Pix copia e cola, linha digitável ou código de barras."""
    if texto.strip().startswith("000201"):
        return ler_pix(texto)
    return ler_boleto(texto)


__all__ = [
    "__version__",
    "Boleto",
    "BoletoInvalido",
    "ChaveInvalida",
    "Pix",
    "PixInvalido",
    "boleto_valido",
    "data_do_fator",
    "fator_da_data",
    "gerar_arrecadacao",
    "gerar_boleto",
    "gerar_pix",
    "gerar_pix_dinamico",
    "ler",
    "ler_boleto",
    "ler_pix",
    "normalizar_chave",
    "pix_valido",
    "tipo_chave",
]
