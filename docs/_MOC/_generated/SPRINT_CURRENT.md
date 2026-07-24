> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A39

Volta para [`00-INDEX`](../00-INDEX.md).

Nenhuma lane prontidão atual.

## Todas as lanes da sprint (para inspeção)

### planned (2)

- [[A39.l10]] — Piso de materialidade: roteamento a needs_review sobre o caminho não-certificado (ADR-344, transitório) · priority P2 · branch `a39-l10-piso-materialidade`
- [[A39.l11]] — Determinismo da classificação LLM: temperature=0 na via compartilhada + golden sintético + telemetria · priority P2 · branch `a39-l11-classificacao-llm-determinismo`

### shipped (10)

- [[A39.l1]] — Harness como instrumento de medição: emitir campos de veredito + conservação em cents + congelar baseline · priority P1 · branch `a39-l1-harness-instrumento-baseline`
- [[A39.l12]] — Resíduo não-coberto: verificar escalação honesta do Binance CSV + investigar extração de preview .xlsx (rico) · priority P2 · branch `a39-l12-binance-rico-residuo`
- [[A39.l2]] — C6 Bank CSV: declarar conservacao_verificavel (semântica de saldo já correta) → escala perda silenciosa · priority P0 · branch `a39-l2-c6-csv-optin-verificabilidade`
- [[A39.l3]] — Fatura closure: parsers emitem total_lancamentos_conferivel (gate #1036 pronto) + flip WARN→HARD · priority P0 · branch `a39-l3-fatura-optin-parsers`
- [[A39.l4]] — C6 Bank PDF: corrigir semântica de saldo_inicial (ajuste do 1º dia) e então declarar verificabilidade · priority P1 · branch `a39-l4-c6-pdf-saldo-semantica`
- [[A39.l5]] — Bradesco: diagnosticar saldo R$1/R$1 (raiz não confirmada) + teste de independência antes de flipar · priority P1 · branch `a39-l5-bradesco-saldo-diagnostico`
- [[A39.l6]] — Checksum de CDB observável: traço checksum_ok/skipped_no_total + WARN posições-sem-total; estender Santander xlsx · priority P1 · branch `a39-l6-cdb-checksum-observavel`
- [[A39.l7]] — Sweep de verificabilidade: itau_xls + santander_xls declaram conservacao_verificavel (wise/rico cortados) · priority P1 · branch `a39-l7-verificabilidade-sweep`
- [[A39.l8]] — Fatura Itaú Visa: TypeRule determinístico + parser (via words) + checksum ADR-343 (cobre 3 não-coberto) · priority P1 · branch `a39-l8-fatura-itau-visa`
- [[A39.l9]] — Posição de renda variável: TypeRule + parser + identidade ticker+proprietário + null-não-soma (cobre 2 não-coberto) · priority P1 · branch `a39-l9-posicao-renda-variavel`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
