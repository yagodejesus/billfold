# Changelog

## 0.1.0 — 2026-10-27

- Boletos bancários (47 dígitos) e de arrecadação (48 dígitos, módulo 10 e 11): leitura, validação com erro detalhado e geração.
- Fator de vencimento com as duas datas-base (reinício de 22/02/2025).
- Pix copia e cola estático e dinâmico: leitura com CRC16, geração, normalização de chaves (inclusive CNPJ alfanumérico).
- QR Code opcional (`billfold[qr]`) e CLI `billfold`.
