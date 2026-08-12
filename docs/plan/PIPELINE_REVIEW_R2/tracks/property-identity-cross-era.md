---
id: TRACK-property-identity-cross-era
type: track
title: "Track — identidade de imóvel atravessa eras: write-path fechado, passivo colapsado por sweep"
plan: PLAN-pipeline-review-r2
status: ready
created_at: "2026-08-11"
agent_role: senior-cto
tags:
  - type/track
  - area/persistence
  - area/pipeline
  - status/ready
  - priority/p0
---

# Track — `property-identity-cross-era`

> Executa a **Onda D / RV2-13** do [[PLAN-pipeline-review-r2]]. Decisões em
> [[ADR-385]] (write-path) e [[ADR-386]] (escopo e sweep); emendas datadas em
> [[ADR-215]], [[ADR-225]], [[ADR-324]] e supersedure parcial da [[ADR-334]].

## Origem

O dono reportou imóveis repetidos no bloco "Residência principal e imóveis" da
tela de Configurações. A investigação encontrou 11 identidades vivas para 6
imóveis reais no workspace de dogfood, com um override do usuário preso numa row
que os runs correntes não resolvem mais — o relatório exibia esse imóvel como
linha de valor zero enquanto o imóvel real constava como "classificação pendente".

O mesmo achado já estava registrado três vezes, sem dono: RV2-13 aqui, RV3-18 em
[[REPORT-REVIEWS-active]] e RV4-10 em [[PIPELINE-REVIEWS-active]].

## Entregue

| # | Mudança | Onde |
|---|---|---|
| 1 | Backfill lê baseline decriptado, aborta grupo sem âncora e detalha o dry-run | `dev/backfill_property_supersession.py` |
| 2 | Cascade atravessa a supersessão; 4º nível por amostra bruta; gate de eras | `backend/app/services/db_property_identity_resolver.py`, `supersession_chain.py` |
| 3 | `SupersessionScope` + escopo observado + detector de zumbi | `pipeline/domain/types/property_supersession.py`, `db_property_supersession_writer.py` |
| 4 | Passe same-canonical no dedup, com guard de complemento | `pipeline/domain/services/imoveis_dedup.py` |
| 5 | Motivo de exclusão para nu-propriedade; aluguel rateado se declara estimativa; alerta de premissa do toggle de IF | `real_estate_metrics*.py`, `real_estate_adapter.py` |
| 6 | 2ª residência principal devolve 409 em vez de 500 | `backend/app/api/properties.py` |
| 7 | Dedup por hard-delete recusa apagar vencedora de supersessão | `dev/dedup_property_identity.py` |

## Passo de ops pendente (owner-gated)

O sweep sobre o workspace de dogfood **não** roda junto com o merge. Ordem
obrigatória, porque um worker com código antigo em voo reverteria tudo:

1. Merge do escopo explícito em `main` e worker recarregado.
2. Pipeline ocioso para o workspace.
3. `python3 dev/backfill_property_supersession.py <workspace_id>` — dry-run, lido
   por humano: conferir vencedor eleito por grupo e ausência de grupo abortado.
4. Repetir com `--apply`.
5. Re-rodar E1.5c → E5 e comparar o diff de `real_estate` e `patrimonio`.

Reversão declarada: `--clear <property_id>`.

## Deferido

- **Rename `descricao_sample` → `descricao_fonte`** (dono: quem tocar identidade
  a seguir). A coluna guarda a descrição íntegra e virou chave de identidade
  ([[ADR-385]] §5); o nome mente. Renomear junto com a mudança de semântica
  destruiria a capacidade de bisect, então fica para migration própria.
- **Invariante `imoveis ∩ excluded == ∅`** ([[ADR-334]] §3, não supersedida):
  segue vigente e não aplicada, rastreada como RV4-10.
