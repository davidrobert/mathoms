# Fixture sintética dogfood (A23.l2 · guard-rail G-a/G-f)

Família **fictícia, PII-zero** (Alex/Bia, sem CPF real) que exercita os cenários de
dedup caros end-to-end (E1.5c → E3 → E4 → E5), servindo de substrato para o
snapshot do view-model e os invariantes de conservação. Determinística (run 2×
byte-idêntico), money como decimal/float padrão do contrato E2.

## Cenários exercitados

| ADR | Cenário | Como a fixture exercita | Genuíno? |
|---|---|---|---|
| **ADR-271** | Investimento cross-year | `baseline-1.5.json`: CDB `bancoficticio` em 2023 (50k) + 2024 (80k) → `investimentos_dedup` funde em **uma série** `valores_31_12={2023,2024}`. | ✅ código real (E1.5c) |
| **ADR-255** | Tx colapsada por dedup cross-file | `extrato-a` + `extrato-b` do mesmo banco/conta com a tx `PIX RECEBIDO ALUGUEL` sobreposta → E3 reconcilia com `transacoes_duplicadas_removidas=1`. | ✅ código real (E3) |
| **ADR-246** | Imóvel co-declarado em comunhão | `baseline-1.5.json`: imóvel único (`codigo_rfb=11`) representando o **outcome pós-dedup** (não somado, maior valor). | ⚠️ outcome bacado — `dedup_imoveis_consolidados` chaveia por `property_id` (resolver DB), fora do substrato in-memory. Dedup 246 genuíno: teste unitário `imoveis_dedup` + dogfood F3 com resolver DB (G-f). |
| **ADR-241** | Caso incremental (B8) | A fixture é estruturalmente apta a um 2º run incremental. | ⏭️ **diferido** — golden de transição incremental completo dimensionado separado (data-engineer), follow-up da lane. |
| **ADR-280** | Campos em de-leak F2 (A24.l1) | Extratos carregam `tipo_lancamento` por transação + `numero_conta`/`numero_conta_norm` (norm consistente com `normalize_account_number` — invariante de produção via `finalize_e2_result`) para o blast radius de strip ter sinal (F2-DB8; fixtures sem os campos = falso conforto). | ✅ prova one-shot: strip → E3 byte-idêntico, zero `value_delta` monetário (controle base×base isola ruído `consolidation_date`/Monte Carlo) |

## Por que não há CPF

Identidade de membro por CPF (ADR-267) seria o vetor mais fiel, mas CPF — mesmo
sintético — dispara o gate anti-PII e não agrega ao que o snapshot testa. Os
membros são resolvidos por nome canônico (`alex`/`bia`), suficiente para os
cenários acima.
