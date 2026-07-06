> Auto-gerado por `dev/build_doc_index.py`. Não edite manualmente.
> Para regenerar: `python3 dev/build_doc_index.py --inline`.

# SPRINT_CURRENT — Lanes da sprint corrente — A28

Volta para [`00-INDEX`](../00-INDEX.md).

Nenhuma lane prontidão atual.

## Todas as lanes da sprint (para inspeção)

### shipped (11)

- [[A28.l1]] — reserva de emergência conforme FORMULAS.md: custo essencial + liquidez estrita + meses_alvo por perfil · priority P0 · branch `reserva-formula-canonica`
- [[A28.l10]] — âncoras do parecer formatadas por tipo (não tudo é R$) + curadoria defensiva de pontos fortes/alertas · priority P1 · branch `ancoras-formatter-curadoria`
- [[A28.l11]] — guardrails pós-LLM do parecer: confiança rebaixada sob premissa fallback + filtro 3-vias de campos_faltantes · priority P1 · branch `parecer-guardrails-pos-llm`
- [[A28.l2]] — TRS efetiva com numerador/denominador do mesmo universo + guardrail de sanidade (ADR-191) · priority P0 · branch `trs-universo-consistente`
- [[A28.l3]] — PGBL: regra de ano-base único — uma recomendação por relatório · priority P0 · branch `pgbl-ano-base-unico`
- [[A28.l4]] — base de mensalização única: política de janela temporal por família de métrica + Cerbasi coerente · priority P0 · branch `mensalizacao-base-unica`
- [[A28.l5]] — nao_identificado 23% → <5%: regras via Learning Loop + gate de reclassificação do owner · priority P1 · branch `nao-identificado-learning-loop`
- [[A28.l6]] — proteção patrimonial ativada: apólices extraídas fluem para compute_protecao + pontos_urgentes condicional · priority P1 · branch `protecao-apolices-flow`
- [[A28.l7]] — imóveis excluídos: dedup tático na projeção + gate de rotulagem do owner · priority P1 · branch `imoveis-excluidos-dedup`
- [[A28.l8]] — higiene de ingestão: períodos implausíveis (1899/2100) e banco vazio viram needs_review, não artefato silencioso · priority P2 · branch `higiene-ingestao-periodos`
- [[A28.l9]] — banner agregado de qualidade de dados no relatório + ressalva de fallback no Monte Carlo · priority P1 · branch `report-data-quality-banner`

---
> Regenerar: `python3 dev/build_doc_index.py --inline`
