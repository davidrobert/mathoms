---
id: ADR-369
type: adr
title: "Rótulo e alvo do cone de IF: percentil vira cenário nomeado (4.0) e o prazo declarado pela família substitui o alvo do próprio modelo (5.0)"
status: Decidido
phase: "A40.l28"
date: "2026-08-07"
amended_at: ["2026-08-07"]
relates_to:
  - "[[ADR-361]]"
  - "[[ADR-360]]"
  - "[[ADR-237]]"
  - "[[ADR-217]]"
  - "[[ADR-212]]"
  - "[[ADR-173]]"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - area/financial-planning
  - phase/a40
---

# ADR-369 — Rótulo e alvo do cone de IF

> **Emenda 2026-08-07 — flip `Proposto` → `Decidido (A40.l28)`.** Os dois bumps
> estão em `main`: `ce9405a2` (#1268, 4.0) e `d72ef569` (#1269, 5.0), na mesma
> janela de merge para a frota pagar uma re-geração de parecer só. A condição do
> flip era a evidência renderizada da S7, anexada aos dois PRs sobre fixture
> sintética PII-zero (precedente [[ADR-365]]).
>
> **Três afirmações desta ADR que a execução corrigiu**, registradas aqui porque
> quem reler o texto acima merece saber onde ele errou:
>
> 1. **O D3 dizia que o compat previne a falha silenciosa; e previne — mas o
>    §Co-design da lane dizia `KeyError`.** Medido: os guards do narrador usam
>    `.get()`, então artefato stale não derruba o stage; cai na frase
>    determinística, a mais otimista do relatório. A conclusão (compat
>    obrigatório) não muda; a gravidade, sim.
> 2. **O custo de contexto foi subestimado nas duas medições.** 4.0 inflou +106
>    chars (estimado +97) e 5.0 levou o bloco a **633** (estimado ~484). O pior
>    caso não é nenhum dos cinco estados conhecidos do cone: é cone suprimido
>    **com** prazo vencido, os dois motivos longos coabitando o payload.
> 3. **`ano_meta_declarado`, o nome natural para o alvo, era armadilha.**
>    `"meta"` é token monetário: a chave viraria folha do catálogo com hint
>    `brl` e o ano 2041 sairia como "R$ 2.041,00" — o acidente que a [[ADR-361]]
>    §Consequências manda não replicar. Ficou `ano_alvo_declarado`.
>
> **O gatilho de remoção do compat (D3) segue aberto e é medível:**
> `python3 dev/count_mc_version_legado.py` — rodado contra o DB local em
> 2026-08-07, **1 de 1 artefato alcançável ainda é 3.0**.

## Contexto

Dois defeitos do bloco `if_monte_carlo` sobreviveram à [[ADR-361]], registrados no
§Deferimento dela como itens 1 e 2, e ambos exigem mexer no contrato publicado.

**1. O percentil aponta para lados opostos dentro do mesmo payload.**
`p10_ano_if` é o percentil 10 do **tempo** — o décimo mais rápido, portanto o
cenário **favorável**. `caminho_p10` é o percentil 10 do **patrimônio** — o
décimo mais pobre, portanto o **adverso**. Mesmo sufixo, orientação invertida,
mesmo bloco. A legenda do gráfico já diz "P10 — cenário adverso" enquanto o campo
de ano ao lado significa o contrário, e o narrador determinístico teve de
documentar a armadilha em comentário
(`projecao_if_narrator.py::_faixa_cenarios`) para não vazá-la na copy.

**2. A probabilidade publicada mede o modelo contra si mesmo.**
`e5_analyzer_adapter` chama `run_monte_carlo_if(..., idade_meta_if=
if_projection.idade_titular_if)` — a idade-meta é a **saída do projetor
determinístico**, não um alvo declarado. Como `horizonte_meta =
idade_meta_if − idade_titular_atual` é exatamente o prazo determinístico, o
produto publica P(o Monte Carlo bate a data que o card determinístico logo acima
imprimiu). E como `mu_log = log(1+r) − ½σ²`, a mediana simulada fica
**estruturalmente** atrás do determinístico: oito planos radicalmente distintos
(PV de R$ 300 k a R$ 5 M, meta de R$ 2 M a R$ 20 M, aporte de R$ 2 k a R$ 30 k)
mediram 31,1%–45,9% — 14,8 pp de amplitude. É praticamente constante de modelo,
não métrica do cliente, e é apresentada como chance de o titular alcançar a meta.

O co-design da [[A40.l28]] (2026-08-07) refutou a premissa de que o item 2 exige
campo novo: `horizonte_anos` é `required` no `goal.if.schema.json` **v1, que é o
que roda em produção**, o wizard já o pergunta com `canAdvance` exigindo resposta
(`plano/meta-if/wizard/page.tsx`), e o campo é **descartado no boundary** —
`_serialize_if_goal` copia cinco campos de `inputs` e não copia esse. O produto
já tem os dois lados da tesoura, **prazo declarado** (compromisso) e **prazo
realista** (capacidade, resolvido por `IFProjector._solve_prazo` a partir do
aporte real), e nunca os comparou.

## Decisão

Dois bumps de `mc_version` em PRs separados, nesta ordem, com **uma** ADR porque
a segunda decisão só é legível contra a primeira (o rename estabelece o
vocabulário que a mudança semântica usa). O comentário em `if_monte_carlo.py`
exige ADR sucessora para qualquer bump — esta é a sucessora dos dois.

**D1 — `mc_version` 3.0 → 4.0 é rename-only.** O schema e esta ADR declaram
textualmente: **4.0 = 3.0 com chaves renomeadas; valores idênticos e comparáveis
a 3.0.** A declaração é obrigatória porque o precedente corta nos dois sentidos —
a descrição atual do schema afirma que o mesmo `p50_ano_if` **não** é comparável
entre 2.0 e 3.0, então o arqueólogo que vê 3.0→4.0 sem ressalva assume que o
número mudou. Renomeiam-se os **três** anos e as três flags de censura
(`ano_if_cenario_favoravel` / `_central` / `_adverso`, cada um com o
`_censurado` irmão), porque deixar `p50_ano_if` no meio da família recria a
confusão dentro dela. **`caminho_p10/p50/p90` não são renomeados** — ali `p10` é
o patrimônio mais baixo, isto é, adverso, que é exatamente o que a legenda já
diz; renomear recriaria o defeito do outro lado.

No mesmo lote entram `horizonte_anos` → `horizonte_simulado_anos` e
`prob_if_ate_horizonte` → `prob_if_ate_horizonte_simulado`. Sem isso o D2 cria
uma colisão tripla: `horizonte` passaria a significar janela de simulação (40
anos), sucesso nessa janela, e prazo declarado pela família — a mesma classe de
defeito que o D1 existe para matar.

**D2 — `mc_version` 4.0 → 5.0 troca a semântica da probabilidade.** De
"P(bater a data que o próprio modelo imprimiu)" para "P(cumprir o prazo que a
família declarou)". O alvo é derivado de `horizonte_anos`, ancorado em **ano
absoluto** via `Goal.effective_from`: `ano_alvo_declarado = effective_from.year +
horizonte_anos`. "15 anos" declarado em 2026 e relido em 2030 tem de continuar
significando 2041, não 2045.

Por isso `prob_if_ate_idade_meta` é **renomeada, não reaproveitada**
(`prob_if_ate_prazo_declarado`), e `idade_meta_usada` é substituída por
`prazo_declarado_anos` + `ano_alvo_declarado` + `declarado_em`. Manter a chave
antiga a deixaria sobrevivendo com semântica invertida — de modelo-contra-si para
compromisso-contra-capacidade — e o consumidor que compara payloads por chave não
lê `mc_version`. A remoção é o sinal.

Três estados de ausência, cada um com motivo próprio no payload:
`Goal.is_template = true` (semeado no onboarding, ninguém declarou nada);
prazo declarado já vencido (`ano_alvo_declarado` no passado), onde `prob = 0` seria
aritmeticamente correto e inútil, pelo mesmo raciocínio do D8 da [[ADR-361]]; e
prazo maior que a janela simulada (`horizonte_anos` aceita até 50, a janela é
40), que **clampa com flag** — estender a janela mudaria a base da censura da
[[ADR-361]] e o tamanho das séries `caminho_*`.

**D3 — Compat de leitura chaveado por `mc_version`, em um único site.** O único
read-site de produção das chaves do cone é `scripts/generate_narratives.py`, que
monta o dicionário `M` do narrador. Ele passa a ramificar: `mc_version` ausente,
`"2.0"` ou `"3.0"` lê as chaves antigas e as monta sob os **nomes novos**; a
partir de `"4.0"` lê as novas. O narrador conhece só os nomes novos.

O compat não é cosmético. Sem ele, um artefato 3.0 relido por um
`generate_narratives` 4.0 devolveria `p50_ano_if` ausente, `mc_p50_censurado`
falso, e cairia no ramo `_projecao_deterministica` — que é a frase **mais
otimista do relatório** e sem incerteza declarada. Ou seja: reintroduziria
exatamente o defeito que o D9 da [[ADR-361]] existe para fechar, e o
reintroduziria em silêncio, movendo a mentira do número para a prosa, onde o
`golden_diff` não audita. (O §Co-design da [[A40.l28]] previa `KeyError`
derrubando o stage; a leitura do código mostra que os guards do narrador usam
`.get()`, então a falha é **silenciosa e pior**, não ruidosa. A conclusão —
compat obrigatório — não muda; o motivo, sim.)

**Gatilho de remoção do compat é mensurável, não datado:** zero artefatos
`analyze_finances` alcançáveis (latest-per-workspace mais os fallbacks de
[[ADR-241]]/[[ADR-291]]) com `mc_version < "4.0"`. Janela de calendário sem
contador é dívida eterna com data de validade decorativa; o script que conta
entra junto com o PR do D1.

**D4 — Sem backfill de artefato.** `pipeline_artifacts` é o registro do que de
fato rodou — substrato de lineage e da [[ADR-212]] — e reescrevê-lo falsifica
relatório já entregue ao cliente. Segue a mesma linha da [[ADR-360]] e da
[[ADR-361]]: `mc_version` é a defesa, não o `UPDATE`.

## Alternativas rejeitadas

**A) Dual-write (publicar chaves velhas e novas por uma janela).** Rejeitada por
custo de frota: o cache do parecer é `sha256(json.dumps(e5_data))`, então
**qualquer** mudança no payload E5 invalida 100% dos caches e cobra uma
re-geração de parecer por workspace no próximo run. Dual-write moveria o hash
duas vezes — uma para adicionar as chaves novas, outra para remover as velhas —
cobrando a frota duas vezes para evitar um ramo de compat de leitura de seis
linhas. Pelo mesmo argumento, os PRs do D1 e do D2 devem mergear na mesma janela,
para a frota pagar uma re-geração só, e a folga no hard-stop de budget da
[[ADR-173]] é conferida antes do primeiro merge.

**B) Default 65 para a idade-meta.** Rejeitada: 65 é âncora de elegibilidade a
benefício público (reforma previdenciária de 2019), conceito ortogonal a "meu
patrimônio sustenta meu custo de vida" — cravá-lo importa a premissa
previdenciária para dentro da métrica que existe justamente para não depender
dela. Empiricamente também erra: para o perfil de titular 40–50 anos colaria a
probabilidade no teto (~85–95%), trocando uma constante de modelo em 40% por
outra em 90%. E "idade-meta de IF" não é conceito de nenhuma das metodologias de
referência do produto (ver `config/agents/`) nem de `config/methodology.md`.

**C) Campo `idade_meta_if` novo em `goals.independencia_financeira`** — a forma
que o §Escopo original da [[A40.l28]] propunha. Rejeitada: criaria **dois alvos
temporais que precisam concordar**, e quando divergissem o relatório escolheria
um enquanto o card exibe o outro. É a classe de defeito que esta ADR existe para
matar, replicada um nível acima. O alvo da família é em anos; as idades por
membro (`IFProjection.idade_titular_if` / `idade_conjuge_if`) são exibição
derivada.

**D) Editar `goal.if.v2.schema.json`.** Rejeitada: o v2 declara de si que é
candidato de roadmap ([[ADR-140]]), não em produção. Editá-lo insinua adoção e
reabre uma decisão que ninguém tomou. O `horizonte_anos` que resolve o problema
já é `required` no v1.

## Consequências

- **Uma re-geração de parecer por workspace**, cobrada uma vez se os dois PRs
  mergearem na mesma janela. Confirmar folga no hard-stop da [[ADR-173]] antes.
- **Nome mais longo é custo permanente de contexto do parecer.** O bloco
  `$.if_monte_carlo` tem `max_chars` calibrado pela [[ADR-361]] e
  `eviction_priority` alto; o rename infla o prefixo escalar e obriga remedição
  (não estimativa) nos dois piores casos, o que bumpa a `version` do manifest —
  que entra na chave de cache via `manifest_version`.
- **`prob_if_ate_idade_meta` e `idade_meta_usada` saem do catálogo de citação.**
  `"meta"` é token monetário em `_MONEY_KEY_TOKENS`, então as duas chaves são
  folhas citáveis hoje e só escapam de virar "R$ 0,31" porque `ancora_format_hint`
  as intercepta — o comentário do módulo usa literalmente `prob_if_ate_idade_meta`
  como exemplo. As chaves novas não contêm token monetário, então deixam de ser
  folhas; o comentário fica stale e é atualizado no mesmo PR, e o snapshot de
  ancorabilidade da [[A40.l30]] muda por consequência.
- **A mudança de semântica entra na nota one-shot de recalibração** pendente no
  dono ([[ADR-360]] §Nota one-shot). Deslocar o alvo sem a nota faz "IF em 2040 →
  2041" ler como "meu plano piorou".
- Payloads históricos continuam legíveis pelo D3, e continuam **falsos sob a
  semântica nova** — é o que `mc_version` carimba.

## Critério de aceite

- Schema e ADR declaram "4.0 = 3.0 com chaves renomeadas, valores idênticos".
- Nenhuma chave de contrato usa `p10`/`p90` como rótulo de ano; nenhuma chave
  `horizonte`/`prazo` sem qualificador `simulado`/`declarado`.
- `prob_if_ate_idade_meta` e `p10_ano_if` só aparecem no site de compat e no
  teste dele.
- Compat provado por artefato `mc_version: "3.0"` produzindo a mesma frase, e por
  mutação: remover o ramo de compat avermelha esse teste.
- Call-site do stage travado por **AST** — a expressão do prazo passado ao Monte
  Carlo não referencia `if_projection`/`idade_titular_if`. Asserção sobre o valor
  deixaria um refactor reintroduzir a derivação com o teste verde.
- Grade de **folga** (`prazo_declarado − prazo_determinístico`) ∈
  {−5, −2, 0, +3, +7, +12} com PV/meta/aporte fixos em ≥2 perfis:
  probabilidade monótona não-decrescente em folga, amplitude > 40 pp entre −5 e
  +12, e `folga = 0 ⇒ prob ∈ [0,30; 0,50]` pinado — documenta o atraso estrutural
  do log-normal como propriedade conhecida em vez de acidente. Seed fixa por
  perfil: seed derivada do input quebraria a monotonia entre pontos da grade
  ([[ADR-360]] §Alternativa A).
- Os três estados de ausência emitem `null` + motivo, e prazo vencido **não**
  emite `prob = 0`.
- Verificação renderizada da S7 anexada ao PR, sobre fixture sintética.

## Referências

- `pipeline/domain/services/if_monte_carlo.py` — dataclass, `monte_carlo_to_dict`.
- `pipeline/domain/services/e5_analyzer_adapter.py` — call-site do Monte Carlo.
- `backend/app/services/pipeline/pipeline_adapter.py::_serialize_if_goal`,
  `pipeline/domain/goals_bundle.py::IFGoalSection` — o boundary que descarta
  `horizonte_anos`.
- `scripts/generate_narratives.py`, `pipeline/domain/services/narrativas/projecao_if_narrator.py`.
- `config/schemas/e5_analysis.schema.json`, `config/schemas/goal.if.schema.json`.
- `config/prompts/parecer_planejador.yaml` — `max_chars` do bloco.
- Origem: [[ADR-361]] §Deferimento datado, itens 1 e 2; co-design em [[A40.l28]].
