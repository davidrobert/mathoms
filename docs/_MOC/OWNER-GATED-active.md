---
type: moc
title: OWNER-GATED-active — Fila de itens travados no owner
aliases: ["OWNER-GATED", "owner-gated", "owner-queue"]
last_review: "2026-07-09"
---

# OWNER-GATED-active — Fila de itens travados no owner

> **Editorial — índice de coordenação, não fonte de verdade.** O status
> canônico de cada linha vive na doc-fonte (última coluna); **reconfirme lá
> antes de agir**. Agrupado por **modo de ação** para permitir batching:
> uma sessão por seção, não itens intercalados. Quando a fila drenar,
> arquivar em `docs/archive/OWNER-GATED-YYYY-MM-DD.md` e remover as linhas
> do [00-INDEX](00-INDEX.md).
>
> Origem: curadoria 2026-07-09 pós-fechamento em rajada de 11 sprints — o
> gargalo do board deixou de ser capacidade de agente e passou a ser a fila
> do owner, espalhada em ~6 planos. Priorização revisada por
> `product-manager`; forma por `information-architect`.

## Sinergias (ler antes de agendar)

- **Uma sessão de dogfood fecha a seção 2 inteira:** reclassificar →
  rotular imóveis → re-gerar parecer (2 re-runs) alimenta ao mesmo tempo o
  KR2 da A28, o gate de saída do dogfood ([[PLAN-report-trust]]), a janela
  da [[A26.l4]] (flip A26→A27) e os gates empíricos do
  [[PLAN-suggestion-lifecycle]].
- **Uma sessão de infra fecha a maior parte da seção 3:** as credenciais
  Coolify/R2 servem simultaneamente A20 L4, LAUNCH_TRUST G2/G3, o staging
  Postgres do Go F2 e o backup mirror da [[A34.l2]].
- **G0 ([[A34.l1]]) é decisão isolada** — não misturar com as sessões
  acima; tem brief próprio e inclui escolha irreversível.

## 1. Decisão estratégica

| Item | O que falta | Prep pronto? | O que destrava | Tempo est. | Doc-fonte |
|---|---|---|---|---|---|
| Gate G0 do repo público | Decidir 6 ADRs: [[ADR-313]] licença · [[ADR-314]] escopo IP · [[ADR-315]] rewrite+FREEZE · [[ADR-316]] metadados/in-place×repo-novo · [[ADR-317]] mailmap · [[ADR-318]] idioma | ✅ [brief pré-mortem](../plan/PUBLIC_RELEASE/w0-decision-brief.md) | Toda a execução W1+ da A34 ([[PLAN-public-release]]) | ~1-2h | [[A34.l1]] |
| Escopo de IP competitivo | Por questão: plano competitivo mover×redigir · prompts split×genericizar · pricing faixas×remover | depende de G0 | Saneamento W1 de IP | — | [[A34.l12]] |
| Débito A12 PR11 | Snapshot DB provando zero rows v1 → autorizar drop do schema v1 + ativar `rule_alocacao_fora_alvo` | lane descreve o passo-a-passo | Cleanup final da migração alocação v1→v2 | ~15min | [[A12.alocacao-v2]] |
| Go/no-go do drop destrutivo do override (M2) | Sign-off com evidência (4 pré-condições nomeadas na lane; janela da [[A26.l4]] é uma delas) | runbook Fase E + drafts mergeados (#873) | Fase E da [[ADR-282]]; convergência final natural_key v2 | — | [[A26.l5]] |
| 1º `make go-parity` Tier-1 (prova ao vivo da [[A40.l24]]) | Rodar `make go-parity WS=<uuid>` e confirmar: marcador `LLM-FREE: ANTHROPIC_API_KEY scrubbed` nos **dois** braços, 0 row nova em `llm_call_log`, e o extrato da Caixa com o **mesmo** tamanho nos dois braços | ✅ gate corrigido e mergeado (`9b7d330e`, #1157); prova de mutação em `tests/test_go_parity_llm_free_gate.py` | Desbloqueia o gate técnico da F2 (nada mais avança sem este run, por declaração do [[TRACK-f2-cutover]]) | ~40min (3 runs/braço) | [[A40.l24]] |
| Flip do cutover Go (F2) | Autorizar flip global `MATHOMS_PIPELINE_SERVICE_URL` em prod, após gate humano | gate técnico em curso; asserção de 0-LLM do Tier-1 corrigida pela [[A40.l24]] — falta a prova ao vivo (linha acima) | Início do soak ≥2 semanas → F3 decommission | — | [[PLAN-go-shell]] |
| Flip `prune_mode=delete` | Ler relatório dry-run (6.049 rows / ~110,8 MB) e dar ack | ✅ dry-run rodando | Poda real de artifacts | ~10min | [[ADR-228]] |
| LGPD G2/G3 — triagem legal | Triagem/validação legal de export + deleção | código entregue | Gates LGPD da [[ADR-228]] | — | [[ADR-228]] |
| Pricing/narrativa (Fase 4 competitiva) | Decisões CEO-diretas de pricing, narrativa e canal | draft do plano | Fase 4.B (landing copy) | — | [[PLAN-competitive-pierre]] |
| (P2, opcional) Nomes de fixture | Decidir se normaliza primeiros nomes sintéticos repo-wide (~100 arquivos) | lane pronta | Zero nome de família no repo público | decisão: ~5min | [[A34.l25]] |

## 2. Sessão de dogfood (uma sessão fecha tudo)

| Item | O que falta | Prep pronto? | O que destrava | Tempo est. | Doc-fonte |
|---|---|---|---|---|---|
| `G-owner-reclassify` | Rodada de reclassificação dos maiores ofensores de `nao_identificado` (~23% → <5%) via Learning Loop | ✅ UI + loop entregues | Medição do KR2 da A28; diagnóstico de perfil comportamental confiável | ~30-45min | [[A28.l5]] |
| `G-owner-label` | Rotular ~7-8 imóveis "classificação pendente" em Configurações | ✅ CTAs na UI | Re-medição da concentração imobiliária (risco Crítico do parecer) | ~10min | [[A28.l7]] |
| Gate de saída do dogfood | 2 re-runs completos consecutivos (E0→E6 + parecer) com zero das 5 classes de defeito | ✅ pipeline pronto | "Posso abrir o beta?" vira sim/não | 2 runs | [[PLAN-report-trust]] |
| Janela da l4 (override v2) | ≥1 reprocesso E4 pós-#878 (medição 2026-07-09: **0 snapshots** ainda) e janela ≥1 sprint verde | ✅ instrumentação + fix mergeados | Flip A26→`done` + A27→`current`→`done` (fecha [[PLAN-data-lineage]]); gate da [[A26.l5]] | ocorre junto com os re-runs | [[A26.l4]] |
| Gates de sugestão (F1/F2/KR5) | 2 runs reais: `thesis_key` estável ≥90%, match de valor ≥98%, utilidade não-regride | ✅ F1-F4 shipped | `done` do [[PLAN-suggestion-lifecycle]] | ocorre junto com os re-runs | [[PLAN-suggestion-lifecycle]] |
| Gate humano do Go F2 | Rodar protocolo `SMOKE_TEST_HUMAN` sobre run full em staging | aguarda staging Postgres (§3) | Flip do cutover Go (§1) | ~30min | [[PLAN-go-shell]] |
| Amarração de drift (contínua) | A cada bump de prompt/model: re-medição no harness sintético antes de manter strict | ✅ harness pronto | Manutenção segura do modo strict de citação | recorrente | [[A26.l2]] |

## 3. Provisionamento de infra / credenciais

| Item | O que falta | Prep pronto? | O que destrava | Tempo est. | Doc-fonte |
|---|---|---|---|---|---|
| Backup mirror off-site + tag | `git clone --mirror` off-site + tag `pre-public-flip-backup` + prova de restaurabilidade | runbook na lane | Pré-condição de G0; rede de segurança do rewrite W3 | ~30min | [[A34.l2]] |
| ~~Rotação Fernet~~ ✅ | Feita e verificada em 2026-07-31: `failed=0 rotated=0 skipped=12150 · kid=05d68234`; janela ainda aberta (fechar após ≥1 ciclo limpo) | — | Pré-condição de G0 **satisfeita** | — | [[A34.l3]] |
| GHAS + Fernet secret + CODEOWNERS | Ativar GHAS, criar secret `MATHOMS_FERNET_KEY`, CODEOWNERS em workflows | lane pronta | Gate G5 do flip | ~20min | [[A34.l15]] |
| Triagem de metadados + ticket Support | Tratar ~15 itens T1 dos 855; ticket ao GitHub Support (cache de PRs) | depende de G0 ([[ADR-316]]) | Gate G4-min | — | [[A34.l21]] |
| Operações do flip (FREEZE→bypass→flip) | FREEZE de merges, deletar 85 branches `agent/*`, bypass do Ruleset, `--visibility public` + verificação G8 | runbooks nas lanes | O flip em si | sessão dedicada | [[A34.l19]] · [[A34.l20]] · [[A34.l22]] |
| A20 L4 — GHCR push | 3 confirmações: `packages:write`+quota · PAT Coolify em secrets · webhook por SHA-tag | ✅ código pronto | A20 L5 (Trivy) + L9 (smoke) + fechamento A20 + G3 da [[ADR-228]] | ~30min | [[MOC-sprint-a20]] |
| E-mail Resend | Aprovação região EU + API key + SPF/DKIM/DMARC no DNS | código em `main` | Gate G1 da [[ADR-228]] (e-mail real) | ~30min | [[PLAN-launch-trust]] |
| Off-site R2 (backup DB) | Bucket R2 (eu) + credenciais + passphrase GPG em vault humano + drill em staging | ✅ drill em CI cobre o mecanismo | Gate G2 da [[ADR-228]]; flippa [[ADR-174]] → Decidido; serve também o mirror da [[A34.l2]] | ~30min (~US$3/mês) | [[ADR-174]] |
| Sentry SaaS | Signup região EU + DSN em backend/frontend/Celery | código instrumentado | Gate G4 da [[ADR-228]]; pré-req do status page | ~20min | [[PLAN-launch-trust]] |
| Status page + alertas | Signups Instatus + UptimeRobot + burn-rate rules + drill de incidente | depende do Sentry | Gate G5 da [[ADR-228]] | ~30min | [[PLAN-launch-trust]] |
| Staging Postgres p/ Go F2 | Provisionar staging Postgres-backed + `ANTHROPIC_API_KEY` no env do serviço Go | ✅ harness `go_parity_gate.py` pronto | Gate técnico F2 → gate humano → flip | — | [[PLAN-go-shell]] |
| PITR/backup do Postgres (Coolify) | Confirmar PITR + `pg_dump` pré-drop com retenção 30d | runbook §5 | Pré-condição operacional da [[A26.l5]] | — | [[A26.l5]] |

## 4. Gasto / aprovação de orçamento

| Item | O que falta | Prep pronto? | O que destrava | Custo | Doc-fonte |
|---|---|---|---|---|---|
| Re-eval golden do parecer | Autorizar 1 rodada **apenas se** o hint da lane alterar redação | ✅ harness pronto | Validação final dos guardrails pós-LLM | ~US$12 | [[A28.l11]] |
| Custo LLM do Tier-2 (Go F2) | Orçar/autorizar run full com narrativas no gate técnico | make target pronto | Tier-2 do gate → gate humano | a medir (< eval do parecer) | [[PLAN-go-shell]] |
| Nightly LLM-real do parecer | Autorizar budget de provider (eval 24×5 IC95 por noite) | harness existe | Taxa real do KR7 + detecção de drift de provider | recorrente | [[PLAN-launch-trust]] |
| Recon do concorrente (Fase 1) | Pagar assinatura (R$120) + fornecer credenciais; time-box 3 dias | track pronto | Dossiê factual → Fase 2 (MCP) | R$120 | [[PLAN-competitive-pierre]] |

## Residual (baixa prioridade, registrado para não sumir)

- **F1-O5 dedup de veículo cross-year** — Defer P2; vira `EntityDedupPolicy`
  quando priorizado ([[PLAN-launch-trust]] §Cut line).
- **Re-extração automática em bump de `PROMPT_VERSION`** — ops-triggered por
  decisão; automática ficou fora de escopo ([[A32.l5]]).
