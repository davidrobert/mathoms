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

## Sweep — aplicado em 2026-08-12, pós-merge de `a920541f`

Ordem obrigatória (worker com código antigo em voo reverteria a supersessão):
merge do escopo explícito → worker recarregado → pipeline ocioso → dry-run lido
por humano → `--apply` → re-rodar E1.5c/E5.

**Resultado medido:** 5 supersessões, 2 overrides migrados, 0 reativações, 0
grupos abortados. O workspace passou de 11 identidades vivas para 6 — uma por
imóvel real — e os 6 overrides passaram a apontar para rows vivas (antes, 2
estavam presos em rows que os runs não resolviam mais).

Re-medir com:

```bash
sqlite3 "$DB" "SELECT COUNT(*) FROM property_identity
  WHERE workspace_id='<ws>' AND superseded_at IS NULL"
```

Reversão declarada: `--clear <property_id>`.

### Pendente

- **Re-rodar E1.5c → E5** para o relatório refletir os números novos. O
  override recuperado devolve o imóvel locado ao portfólio de renda, o que
  move `imoveis_geradores`, `investivel_efetivo` (o toggle da IF está ligado) e
  o cap rate líquido — que cai **mais** que proporcionalmente, porque a
  manutenção escala com o denominador. Não publique número projetado: leia
  `real_estate.cap_rate_liquido_pct` de um run real.
- **Diff de `alertas[]` antes/depois.** Com o cap rate corrigido, `spread_critico`
  provavelmente dispara pela primeira vez, e `premissa_if_imoveis` (novo) tende a
  disparar. Alerta novo é mudança visível ao usuário e precisa ser intencional.
- **Regenerar ou invalidar o parecer E6**, que é derivado do E5: parecer velho com
  números novos é contradição na mesma página. A [[ADR-235]] §5 proíbe recomendar
  venda da nu-propriedade como solução de liquidez — instrução que nunca foi
  exercitada, porque o imóvel chegava como `desconhecido`.

## DE-6 / RV6-13 — o eixo atravessa até o mint (2026-08-19, PR #1556)

Segunda visita à mesma superfície, agora pelo §r7. O r7 publicou duas entradas em
`real_estate.excluded_properties[]` cuja descrição começa por "DIVIDA - CREDITO
IMOBILIARIO", com `property_id` mintado, `classification: "desconhecido"` e o CTA
"rotular em Configurações" — rotular põe um **passivo** no patrimônio bruto como
**ativo**. Decisão em [[ADR-398]].

### O que a re-medição contra `main` mostrou

O diagnóstico registrado no §r7 ("a autoridade de `secao` não foi propagada ao
mint") está certo como **classe** e errado como **instância deste run**:

| medida | valor |
| --- | --- |
| cobertura de `secao` no run `33514dc4` | **87/87** (81 `bens_direitos`, 6 `dividas_onus`) |
| dívidas com valor positivo | 6/6 — como o prompt 1.3.0 manda transcrever |
| dívidas com `categoria_hint: "imovel"` | **2** |
| dívidas roteadas para `imoveis_consolidados` no r7 | **0** — a [[ADR-394]] já as manda para `dividas` |
| identidades criadas no r7 | **0** — a [[ADR-392]] estancou a sangria |

As duas entradas "DIVIDA" que o leitor viu são rows de **2026-08-12** e
**2026-08-16**, anteriores à ADR-392. O que as levou à tela não foi o mint: foi a
**leitura**, que projeta toda row viva de `property_identity` sem consultar o
baseline do run.

O buraco de escrita, porém, é real e alcançável — onde `secao` **falta**. O campo
é opcional em `e15_baseline_extract.schema.json` (ADR-261 Tier 3; 766 artefatos
históricos não o carregam e o modo incremental os reagrega). Reproduzido em
fixture sintética: o item entra em `imoveis_consolidados`, **soma ao
`total_bens`** e é mintado. E quando a descrição do financiamento canonicaliza
para o **mesmo endereço** do imóvel financiado, o passivo não ganha identidade
nova — ele **casa com a identidade do próprio imóvel**, e o dedup da [[ADR-246]]
o absorve em seguida. É a classe da §Emenda da [[ADR-392]] reaberta por outra
porta, e não estava no achado.

### Entregue

| # | Mudança | Onde |
|---|---|---|
| 1 | Consolidador carimba `eixo_autoridade` e `secao_disponivel` nos dois produtores | `scripts/consolidate_baseline.py` |
| 2 | Mint recusado quando o hint decidiu o eixo E o fato estava disponível | `pipeline/domain/services/property_identity_enricher.py` |
| 3 | `domain.property_identity_eixo_por_hint` no vocabulário de razões | `pipeline/domain/review_reason.py` + `config/schemas/review_reason.schema.json` |
| 4 | Projeção exige que o baseline do run ou o dono reivindiquem a identidade | `backend/app/services/real_estate_e5_integration.py` |

A precondição do #2 é **escopada** ao grão `(membro, ano)` — o grão de um E1.5a.
Exigir o fato onde a fonte nunca o ofereceu apagaria `property_id` de todo imóvel
do corpus pré-`secao`: medido, 17 testes de dedup/identidade reprovam, e com eles
iriam o dedup, os overrides do dono e a seção de imóveis. Consequência aceita e
nomeada na [[ADR-398]] D2: numa declaração inteiramente legada o mint segue
autorizado, e quem protege o leitor ali é o filtro de leitura (#4), que não
depende de quando a identidade nasceu.

### Blast radius medido (ws-1b9f2cf5, run `33514dc4`)

Com e sem o filtro no mesmo harness, `excluded_properties` é o **único** campo do
payload que muda: **6 → 2**. `imoveis`, `valor_total_imoveis`, `cap_rate`,
`concentracao_pct`, `componentes_calculo`, `spreads` e `alertas` idênticos.
Nenhum `property_id` muda de existência; nenhum dos 6 overrides é afetado
(nenhum aponta para row podada). As 4 rows podadas nunca tiveram valor no
baseline e, sem override, jamais foram `investment`.

As 4 entradas que somem são todas de `classification: "desconhecido"` — a
contagem que o banner de qualidade usa para pedir rótulo cai de **4 para 0**.
Duas delas são os itens de dívida do DE-6; as outras duas são identidades que o
baseline corrente já carrega como imóvel com `property_id` nulo (ADR-392), cujo
CTA apontava para uma row que run nenhum resolve mais — o "override sem efeito
monetário" do RV4-10. **Nenhuma** sai por colapso de dedup: o
`_dedup_excluded_projection` seguia inerte, como o RV4-10 registra.

### Reconciliação das órfãs (RV6-13) — medida, não aplicada

```
sqlite3 "$DB" "SELECT COUNT(*) FROM property_identity
  WHERE workspace_id='<ws>' AND superseded_at IS NULL
    AND (endereco_canonical IS NULL OR endereco_canonical='')"
```

Medido em 2026-08-19: **4 vivas** sem canonical (6 no total; 2 já supersedidas).
Últimas criações em 2026-08-12 e 2026-08-16 — **zero no r7**, o que confirma o
§r7. Duas são os itens de dívida.

Elas são **inalcançáveis** pelo resolver: o match residual da [[ADR-392]] D1 exige
row viva única por `(titular_key, codigo_rfb)`, e há **2 por par** nos dois pares
(`11` e `12`). Nenhum item novo pode reivindicá-las. Somado ao filtro de leitura,
o dano residual é **higiene de tabela**, não comportamento.

Por isso a poda **não** foi executada: é decisão do dono, não correção pendente.
Quando for feita, o instrumento é o mesmo do sweep de 2026-08-12 — supersessão
reversível, nunca hard-delete:

```bash
python3 dev/backfill_property_supersession.py <ws>            # dry-run, ler antes
python3 dev/backfill_property_supersession.py <ws> --apply
```

Reversão declarada: `--clear <property_id>`. Ordem obrigatória inalterada (merge →
worker recarregado → pipeline ocioso → dry-run lido por humano → `--apply`). O
backfill **aborta** grupo sem exatamente 1 âncora no baseline — e nenhuma das 4
órfãs tem âncora, então a expectativa honesta do dry-run é **4 grupos abortados,
0 supersessões**. Podá-las exigiria eleger vencedor por outro critério, que é
exatamente o que a [[ADR-386]] proibiu. Recomendação: **não podar** enquanto
forem inertes.

## Deferido

- **Rename `descricao_sample` → `descricao_fonte`** (dono: quem tocar identidade
  a seguir). A coluna guarda a descrição íntegra e virou chave de identidade
  ([[ADR-385]] §5); o nome mente. Renomear junto com a mudança de semântica
  destruiria a capacidade de bisect, então fica para migration própria.
- **Invariante `imoveis ∩ excluded == ∅`** ([[ADR-334]] §3, não supersedida):
  segue vigente e não aplicada, rastreada como RV4-10.
