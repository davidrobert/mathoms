# ledger-certify — rubrica de veredito

Critérios de julgamento carregados sob demanda (o `SKILL.md` fica só com o
procedimento). Define o que **conservação / integridade / classificação**
significam no grão **transação/posição** (E3 reconcile + E4 categorize) e — o mais
importante — **qual sinal é perda/dupla-contagem silenciosa** (o modo de falha que
a skill existe para caçar). Reusa contratos decididos: [[ADR-090]] (cents),
[[ADR-342]] (anti-silêncio), [[ADR-287]] (natural_key), [[ADR-271]] (dedup).

## Princípio nº 1 — conservação é o PISO, não o teto

"A soma fecha" é condição necessária, **não** suficiente. Os erros de **maior
materialidade** são todos **sum-preserving** e passam por toda a conservação
existente (CV1–CV17 no E5, e as igualdades abaixo):

| Falha sum-preserving | Por que a conservação não vê |
|---|---|
| **Dedup dobrado de patrimônio** (ADR-271/246) | o ativo duplicado é linha legítima de `composicao[]`; `bruto == Σ composicao` continua verdadeiro |
| **Swap intra-lado** (essencial→lazer; aporte→consumo, ADR-333) | `despesa_total` inalterado; o balde certo, o total certo, o dinheiro no lugar errado |
| **Recorrente ↔ one-time** (venda/resgate como recorrente) | `receita_total == recorrente + one_time` fecha por construção |
| **Transferência net-neutral** (ambas as pernas na janela) | `fluxo_liquido == receita − despesa` fecha; brutos inflados igualmente |

**Consequência de design:** a rubrica tem **duas camadas** — (A) conservação por
transição de stage (objetiva, cents tol-zero) e (B) **correção de classificação
por fronteira de decisão** (onde a conservação é cega). Uma rubrica que só herda
conservação dá **falso-verde** exatamente nos piores casos.

## Os 5 vereditos (fail-closed) — por grupo E3 e por balde E4

Cada grupo de reconciliação (E3, por `artifact_key`) e cada balde (E4, das 7
keys) recebe **um** veredito. Só sobe a `conservado` quem tem **checksum que
prova o fechamento**; sem isso, teto `coberto-sem-verificação`.

| # | Veredito | Definição | É falha? |
|---|---|---|---|
| 1 | `conservado` | Count tol-0 fecha **e** valor provável (dedup==0 ou re-derivado) **e** baldes fecham **e** cobertura de categoria 100% **e** nenhuma fronteira cruzada (camada B). | Não |
| 2 | `coberto-sem-verificação-de-valor` | Count fecha mas o **valor** não é provável — dedup>0 e o valor removido **não é declarado** no artefato (só a contagem). Dívida de contrato. | Parcial — reportar |
| 3 | `dedup/transfer-legítimo` | Divergência 100% explicada por `dups_removidas`/`dedup_collapsed`/`transferencias_count` **declarados**. | **Não** — comportamento correto |
| 4 | `perda/dupla-contagem-silenciosa` | Gap de count/valor que nenhuma declaração explica; OU dupla-contagem (posição `tipo\|instituicao\|descricao_norm` viva 2×, ADR-271; imóvel co-declarado somado, ADR-246); OU fronteira de decisão cruzada (camada B). | **Sim — P0** |
| 5 | `não-verificável` | Lineage quebrado: `fontes` não casa E2, `natural_key` null impede join, artefato stale/parcial. | Surface — nunca falso-verde |

### Eixo cross-grupo (4 estados) — fora dos 5 vereditos

Uma **ocorrência cross-grupo** ([[ADR-354]]: a mesma chave provenance-free viva em
≥2 triplas de proveniência) não é grupo E3 nem balde E4, logo **não recebe veredito
de unidade**. Estado próprio, do bloco `## Duplicação cross-grupo` do harness.

**Leia a partição antes de escalar.** O token impresso é **`carrier-shaped`**
(`defect-shaped` não existe no output do harness) e vale por **disjunção**: campo de
proveniência **PARCIAL** (`<campo>:c2` — vazio numa perna, preenchido na outra)
**OU** **QUALQUER divergência de `tipo_conta`** entre as pernas (`tipo_conta:c1`).
Ocorrência com `parciais=''` e `carriers=tipo_conta:c1` é **carrier**, não
coincidência — rebaixá-la a `coincidência-nao-declarada` esconde exatamente o
carrier 1 que a [[A40.l1]] existe para achar. `coincidence-shaped` = **nenhum** dos
dois, incluindo campo vazio nas DUAS pernas: par simétrico, nada a canonicalizar.
Só o primeiro é P0; escalar a segunda classe travaria a lane por sobre-detecção
declarada.

**Residual declarado do predicado de carrier 1** ([[ADR-354]] §Consequências): ele é
**mais largo** que o par variante que motivou a ADR (`extrato` vs `extratoconta`) —
distinguir variante-de-vocabulário de tipo de conta REALMENTE distinto exige o
alias-map versionado da [[A40.l2]]. Consequência: coincidência legítima intra-banco
entre tipos de conta distintos (tarifa de mesmo valor no mesmo dia em conta e
poupança) sai `carrier-shaped`, escala a P0 **e é estruturalmente in-whitelistável**
(o validador rejeita o shape por ser carrier). Sob [[ADR-342]] o instrumento erra
para **sobre-detecção rotulada**, nunca para sub-detecção silenciosa; a triagem por
classe (histograma) é o antídoto, não a whitelist.

| Estado | Quando | Consequência |
|---|---|---|
| `defeito-de-identidade` | ≥1 ocorrência não-explicada **e `carrier-shaped`** (campo parcial **OU** `tipo_conta` divergente — basta um) | **P0 do run**, mapeado a `perda/dupla-contagem-silenciosa` (extensão da linha 4: dupla-contagem sum-preserving) |
| `coincidência-nao-declarada` | ocorrência não-explicada **`coincidence-shaped`** (`carriers=nenhum`: nem campo parcial nem `tipo_conta` divergente) | Sinal de **triagem** — sobre-detecção declarada do instrumento. Registre a classe (histograma) e siga; **não é P0** |
| `coincidência-declarada` | shape de VALOR na whitelist declarada (`EXPLAINED_DIVERGENCE`, vazia por decisão A40.l1) | Linha **separada** — nunca somada ao numerador |
| `não-verificável` | `cobertura=CEGA`: balde ilegível, uma das 3 identidades não fecha, ou <2 triplas no corpus (critério vacuoso) | Bloco **nulo** — um 0 aqui **não** é verde |

O balde E4 pode estar `conservado` **e** haver ocorrência cross-grupo: a duplicação
é *sum-preserving* dentro de cada grupo. É exatamente o falso-verde da camada B.

## Camada A — conservação por transição de stage (cents int, tol-zero)

Fonte: [[ADR-090]] (`Decimal(str(v))`, prefira o campo `amount` decimal-string
sobre o `valor` float). **Por transição, não por tipo de documento** (o tipo é
escopo do parse-certify; aqui o insumo já é transação roteada).

**E2→E3:**
- **Count (HARD):** `Σ_docs n_tx(E2) == Σ_grupos [transacoes_total + transacoes_duplicadas_removidas]`. Toda tx extraída é sobrevivente OU dup declarada.
- **Valor (HARD se dups==0; senão veredito 2):** `Σ_cents(E3) == Σ_cents(E2) − valor_dups`. `valor_dups` **não existe no artefato** → com dedup>0 o valor é `coberto-sem-verificação` a menos que a re-derivação (Passo 2) recompute o dedup.

**E3→E4:**
- **Count (HARD):** `Σ_grupos transacoes_total(E3) == tx_total(_lineage)` e `tx_total == receitas.total_tx + despesas.total_tx + transferencias_count + dedup_collapsed`. Todo classificado tem destino; classifier não dropa em silêncio.
- **Valor de balde (HARD, mirror CV16):** `Σ_cat totais_por_categoria == total_geral` e `Σ_tx cents(dados[cat]) == totais_por_categoria[cat]`.

Cobertura de `natural_key` (% de tx com chave presente pós-E4) é **linha de
primeira classe** — pré-requisito do join sticky-override e da conservação de
valor por-tx. Reporte o número; não bloqueia v1, mas expõe (o gap dos ~92%).

## Camada B — correção de classificação por fronteira de decisão

Rigor **escala com cruzamento de fronteira de decisão, não com granularidade de
categoria**. Rígido no cruzamento, tolerante dentro da fronteira.

| Prioridade | Fronteira cruzada | Exemplos | Por quê |
|---|---|---|---|
| **P0** | **Dedup de patrimônio** | mesma chave viva 2× cross-ano/cross-declarante (ADR-271); imóvel em comunhão somado (ADR-246) | corrompe patrimônio líquido + progresso_if; viés otimista; permanente, compõe |
| **P0** | **Natureza/sinal** | transferência interna → receita/despesa; perna única inflando fluxo | muda o que "dinheiro entrando/saindo" significa |
| **P0** | **Consumo ↔ poupança** (ADR-333) | aporte de investimento como despesa de consumo, e vice-versa | swing direto na taxa de poupança, cego à conservação |
| **P1** | Essencial ↔ discricionário | despesa essencial como lazer → sub-reserva | afeta `reserva_alvo`; priorize a direção otimista |
| **P1** | Recorrente ↔ one-time | venda/resgate/restituição como recorrente | mensaliza renda-fantasma na projeção |
| **P2** | Granularidade **intra**-fronteira | lazer ↔ vestuário ↔ outros-discricionários | rola para a mesma decisão; forçar aqui é Goodhart |

Itens que o próprio sistema marcou `needs_review` **não** são erro silencioso (o
sistema sabe que não sabe) — reporte, não conte como P0.

## Divergências esperadas (benignas — nunca "silenciosa")

- **Drift fresco↔persistido** — o E3/E4 re-derivado difere do gravado porque o
  código mudou pós-último run OU o artefato é de run parcial (ADR-080). É
  **drift**, reporta; não é perda por si só.
- **Stub E2** — E2 `requires_llm_fallback` → E3 vazio é `escalado-honesto`.
- **Dedup/transferência declarados** — veredito 3, comportamento correto.

## O que NÃO copiar dos moldes vizinhos

- **Do parse-certify:** a tabela "5 grupos com `in_scope_v1`" (escopo E0→E2); a
  armadilha "cripto em repouso" (lê artefato do DB, não Fernet de `storage/data/`);
  a conservação "por tipo de documento" (aqui é **por transição de stage**).
- **Do pipeline-review:** "dispara run + confirme verde" e o custo LLM. A
  `ledger-certify` **não** dispara run, **não** toca E5+, **não** usa LLM.

## Cobertura (v1)

- **No escopo v1:** os 7 baldes E4 (`despesas`, `receitas`, `patrimonio`,
  `investimentos`, `seguros`, `pontos_milhas`, `fluxo_mensal_detalhado`) +
  conservação E2→E3→E4 + camada B (fronteiras P0/P1) + sticky-override onde há
  `TransactionOverride` (join por hash/natural_key).
- **Fora do escopo v1 (→ v2):** **acurácia geral** de categorização (precisa de
  golden/oráculo versionado — escopo `prompt-engineer`, overlap com ADR-186). v1
  checa *cobertura* (toda tx categorizada), *conservação* (baldes fecham),
  *fronteira* (camada B) e *sticky-override* — não acurácia semântica ampla.
  `category_template` (ADR-137) valida só `categoria ∈ catálogo`, não "é a
  categoria certa".
