# Runbook — Auditoria full (100%) do vault de documentação

> **ADR:** [[ADR-302]] (skill audit-vault) + emenda 2026-07-03 (amostra
> rotativa e modo `--full`).
> **Owner:** dono do vault — quem dispara `/audit-vault`.
> **Rollback:** N/A — a auditoria é read-only; correções saem em PRs
> próprios (revert normal de Git, um por fase).
> **Custo de referência:** ~17k tokens de julgamento por arquivo (empírico
> run r5). Universo completo do vault vivo = **409 arquivos ≈ 7M tokens**.

---

## 1. O que é (e quando rodar)

A auditoria **recorrente** (`/audit-vault`, sem flags) julga só uma amostra
rotativa: cada arquivo tem classe permanente (`sha1(path) % stride`) e o
número do run rotaciona a classe-alvo — 100% de `reference`/`plan`/`sprint`
é coberto a cada **5 runs**, e o long tail (`adr`/`claude`/`prompt`) a cada
**20 runs**. Esse é o modo default e barato.

O modo **`--full`** desliga a amostra e julga **todos** os arquivos do
escopo. É **modo de evento** — rode apenas quando:

1. **Baseline inicial** — o vault nunca passou por um sweep completo e você
   quer zerar o estoque de drift de uma vez (a rotação vira manutenção, não
   descoberta).
2. **Pós-refactor estrutural** — evento tipo DOC_REORG (ADR-182) que mexeu
   na forma de muitos docs de uma vez.
3. **Gate dogfood → beta** — o sweep amplo previsto em [[ADR-302]]
   §Gatilho, com KR "% reference sem DOC-BLOCK".

**Anti-gatilho:** nunca como cadência recorrente. Re-julgar ~400 arquivos
majoritariamente inalterados a cada auditoria é o desperdício que a
arquitetura de candidatos (gate ∪ diff ∪ amostra) existe para evitar.

## 2. Pré-requisitos

- `main` atualizado (`git fetch origin && git pull --ff-only` no clone que
  vai rodar) — a skill e o coletor rodam do próprio repo.
- **Uma sessão nova de agente por fase** — contexto limpo; o julgamento de
  ~50 arquivos + triagem consome a janela de uma sessão.
- Nenhum env especial: os gates e o coletor são `python3` puro.

## 3. Visão geral — 3 fases, um gate de decisão entre elas

Rodar tudo de uma vez produziria 200-400 findings — intriável. O sweep é
**faseado por bucket**, do maior risco para o menor, e cada fase termina com
sua própria triagem (<30min) e seu próprio PR:

| Fase | Escopo | Arquivos | Custo estimado | Quando |
|---|---|---|---|---|
| 1 | `reference` | 54 | ~1M tokens | primeiro — é o que agentes leem para decidir |
| 2 | `plan` + `sprint` + `claude` + `prompt` + `root` | ~58 | ~1M tokens | após triar a Fase 1 |
| 3 | `adr` | 297 | ~5M tokens | **condicional** — ver §6 |

O gate entre fases é deliberado: a taxa de findings da fase anterior é o
argumento empírico para (ou contra) pagar a próxima.

> **Nota sobre sintaxe:** tudo que vem após `/audit-vault` é **instrução em
> texto livre interpretada pelo agente** que executa a skill — não flags
> parseadas por um CLI. `--scope`/`--full` são convenções (documentadas no
> SKILL.md) que o agente traduz para o CLI real, `collect_candidates.py`;
> instruções adicionais em português ("sub-lote 2/5", "consolide numa seção")
> funcionam normalmente.

### 3.1 Modo one-shot — um comando para auditar tudo

Se você já decidiu pagar o sweep inteiro (~7M tokens) e não quer disparar
fase a fase, um único comando executa a sequência completa:

```
/audit-vault --scope all --full
```

Contrato (definido no SKILL.md §Parâmetros): a sessão **faseia
internamente** na mesma ordem deste runbook — Fase 1 → Fase 2 → Fase 3 em
sub-lotes — e fecha **1 PR docs-only + 1 subseção rN no AUDITS-active por
fase antes de iniciar a seguinte**. Invocação única ≠ entrega única: a
triagem continua chegando em pacotes de <30min, e cada fase mergeada é um
checkpoint (interrupção por contexto/créditos retoma da fase seguinte, não
do zero).

**Trade-off aceito ao usar one-shot:** o gate de decisão pré-Fase 3 (§6)
deixa de ser uma parada e vira registro informativo — ao invocar, você já
autorizou os ~5M tokens dos ADRs mesmo que as fases 1-2 venham limpas. Se
quiser manter o controle de custo, use o modo faseado (§4-6).

### 3.2 E as correções? — níveis de automação (`--fix`)

Por default, a auditoria **corrige sozinha só os DOC-BLOCK** (mergeados no
PR de cada fase). DOC-DRIFT viram *proposta* de batch (lane P2 no
AUDITS-active) e DOC-POLISH ficam em wontfix — porque parte dos DRIFT exige
decisão sua, não edição mecânica (ex.: ADR `Proposto` estagnada depende de
saber se o evento externo ocorreu; spec fora do funil é priorização de
produto).

Para auditar **e** corrigir tudo que não depende de você, adicione `--fix`:

```
/audit-vault --scope all --full --fix
```

| Severidade | default | com `--fix` |
|---|---|---|
| DOC-BLOCK | corrigido no PR da fase | idem |
| DOC-DRIFT | proposto como batch (você decide) | **executado** em PR docs-only próprio por fase |
| DOC-POLISH | listado, wontfix | idem (fora do `--fix`) |
| Item que exige decisão do owner | `procede-aberto` | `procede-aberto` — **nunca** auto-resolvido; a pergunta fica explícita na tabela rN |

Salvaguarda do `--fix` (contrato no SKILL.md §Parâmetros): nenhum DRIFT é
editado sem **citação dupla** (trecho do doc + trecho da fonte-de-verdade)
— o mesmo verify exigido de DOC-BLOCK — para a taxa de falso-positivo não
virar edição errada em doc canônico.

## 4. Fase 1 — `reference` (54 arquivos)

Em uma **sessão nova**, execute:

```
/audit-vault --scope reference --full
```

O que a skill faz por baixo (você não precisa rodar nada disso à mão):

```bash
# Camada 1 — gates determinísticos (fail-fast)
python3 dev/validate_frontmatter.py && python3 dev/check_doc_links.py && \
python3 dev/check_adr_anchors.py && python3 dev/check_doc_filename_id.py && \
python3 dev/validate_adr_format.py && python3 dev/build_doc_index.py --check

# Camada 2 — coleta com sweep 100% do bucket
python3 .claude/skills/audit-vault/references/collect_candidates.py \
  --scope reference --full --out _scratch/audit-candidates.json
```

Depois: julgamento delegado aos especialistas (camada 3), verify de
DOC-BLOCK com citação dupla (camada 4) e síntese (camada 5) — relatório
bruto em `_scratch/` + seção `rN` nova em
[`docs/_MOC/AUDITS-active.md`](../../_MOC/AUDITS-active.md) citando a
cobertura (`buckets{universe,sampled,stride}` do JSON).

**O que esperar:** em vault nunca varrido, estime 0,3-1 finding/arquivo.
DOC-BLOCK são corrigidos pela própria sessão (PR docs-only imediato);
DOC-DRIFT viram **um** batch (lane P2); DOC-POLISH ficam listados
(wontfix até pré-beta).

## 5. Fase 2 — buckets operacionais (~58 arquivos)

Em outra sessão nova, após triar a Fase 1:

```
/audit-vault --full nos escopos plan, sprint, claude, prompt e root,
consolidando numa única seção rN
```

(O coletor aceita um `--scope` por vez — o agente o roda 5×, uma por
escopo, e consolida julgamento e triagem. Alternativa sem ambiguidade:
5 invocações separadas `/audit-vault --scope <X> --full`, ao custo de
repetir gates/síntese em cada uma.)

São 5 escopos pequenos (29 + 12 + 12 + 4 + 1); cabem numa sessão só e numa
única seção do AUDITS-active. `sprint` cobre apenas a sprint `current`
(fechadas ficam fora por design — auditar histórico congelado gera
falso-drift).

## 6. Fase 3 — `adr` (297 arquivos) — condicional

**Decida antes de rodar**, com o dado das fases 1-2 (no modo one-shot,
§3.1, este gate é informativo — a fase roda automaticamente e a taxa é
registrada na subseção rN):

- **Taxa alta** (≥ ~0,3 finding DOC-BLOCK+DRIFT por arquivo) → o long tail
  provavelmente está sujo; os ~5M tokens se justificam.
- **Taxa baixa** → deixe a rotação recorrente (K=20) cobrir os ADRs ao
  longo dos próximos runs e reserve o sweep para o gate pré-beta.

Se rodar: **sub-lotes de ~60-75 ADRs por sessão** (4-5 sessões), começando
pelos `status: Proposto`/`Roadmap` — é onde staleness induz decisão errada
(um `Proposto` esquecido parece pendência viva). Instrução por sessão:

```
/audit-vault --scope adr --full, julgando apenas o sub-lote N/5
(Proposto/Roadmap primeiro, depois Decidido por id)
```

(1ª sessão com `sub-lote 1/5`, 2ª com `sub-lote 2/5`, e assim por diante.)

## 7. Pós-sweep

- Cada fase fecha com: DOC-BLOCK mergeados, batch DRIFT proposto, seção
  `rN` no AUDITS-active com a cobertura declarada.
- A auditoria **recorrente volta ao normal** no run seguinte
  (`--run N+1`): com o baseline zerado, a rotação passa a *manter* frescor
  em vez de descobrir estoque antigo.
- Não há estado a restaurar (read-only). Se um PR de fix se provar errado,
  revert Git padrão.

## 8. Referências

- [[ADR-302]] — regra canônica da skill + emenda da amostra rotativa.
- [`.claude/skills/audit-vault/SKILL.md`](../../../.claude/skills/audit-vault/SKILL.md)
  — procedimento das 5 camadas e parâmetros.
- [`docs/_MOC/AUDITS-active.md`](../../_MOC/AUDITS-active.md) — rastreamento
  e disposição de findings (convenção de triagem no topo).
