"""A39.l8 — classificação determinística da fatura de cartão Itaú (não Pão de
Açúcar): marcadores independentes cobrem os 2 sub-layouts (com espaços e o
sub-layout sem-espaços `Totaldestafatura`). Antes: conf 0.0 (não-coberto → E2-llm)."""

from __future__ import annotations

from backend.app.services.documents.content_classifier import classify_text

_ITAU_FATURA_ESPACADA = """Resumo da fatura em R$
Total da fatura anterior 100,00
Lançamentos atuais 250,00
= Total desta fatura 350,00
Vencimento: 06/05/2026
Limite total de crédito: 5000,00
Cartão 4771.XXXX.XXXX.5739
08/06 COMPRA TESTE 50,00
"""

# Sub-layout sem-espaços (A38.l9): pdfplumber cola as palavras.
_ITAU_FATURA_SEM_ESPACOS = """ResumodafaturaemR$
Totaldafaturaanterior 100,00
Lançamentosatuais 250,00
=Totaldestafatura 350,00
Vencimento:06/05/2026
Limitetotaldecrédito:5000,00
"""


def test_itau_fatura_espacada_classifica_como_fatura() -> None:
    cc = classify_text(_ITAU_FATURA_ESPACADA)
    assert cc.doc_type == "fatura"
    assert cc.confidence >= 0.8


def test_itau_fatura_sem_espacos_classifica_como_fatura() -> None:
    cc = classify_text(_ITAU_FATURA_SEM_ESPACOS)
    assert cc.doc_type == "fatura"
    assert cc.confidence >= 0.8
