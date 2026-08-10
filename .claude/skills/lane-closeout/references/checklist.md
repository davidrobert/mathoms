# lane-closeout — receitas de julgamento

Complemento da camada 3 do [`SKILL.md`](../SKILL.md). Cada receita diz **o que
procurar** e **como provar**. Achado sem prova não sai do rascunho.

## 1. Completude — o que shipou está registrado?

| Verificar | Como |
|---|---|
| Todo PR da lane aparece no `_README` da sprint | `grep "#<N>" docs/sprint/<X>/_README.md`. Lane com 2+ PRs: o `ship_pr` nomeia **um**; os outros vivem no corpo |
| Todo trabalho deferido tem dono vivo | Camada 1 cobre. Se acendeu, o destino é lane **aberta**, plano, ou dono nomeado — nunca uma ADR `Decidido` sozinha (ADR registra, não executa) |
| ADR da lane flipou `Proposto` → `Decidido` | `grep "^status:" docs/adr/<NNN>-*.md`. Lane que implementa ADR e fecha com ela `Proposto` é entrega sem decisão |
| Achado que o PR fechou está marcado fechado | Tabela de achados da sprint/plano: linha `procede-aberto` cujo PR já mergeou é zumbi |
| Escopo que a lane **recusou** está escrito | Recusa não registrada volta como pickup duplicado. O #1341 item 5 é exatamente isso |

## 2. Corretude — os números ainda são verdade depois do merge?

**Re-meça; não releia.** Todo número que o PR pode ter mudado se mede de novo
**agora**. Número citado antes do merge é hipótese, não evidência.

| Verificar | Como |
|---|---|
| Denominador de KR / contagem de achados | Rode a medição original de novo. O #1341 achou "5 → 0" onde eram **2**: dois dos itens não existiam no momento da medição |
| "N de M seções/casos/campos" na prosa | Conte na fonte, não no doc que copiou a contagem |
| Afirmação de ausência ("não há outro consumidor") | Prove sobre a **fonte única**, não sobre uma busca textual |
| Medição feita por cópia à mão | Descarte. Só vale medição que um comando reproduz |

## 3. Consistência — todos contam a mesma história?

| Verificar | Como |
|---|---|
| `status:` bate em lane, `_README` e MOC | Camada 1 pega o contador; o **texto** ao redor é julgamento |
| Critério de aceite escrito == o que o co-design decidiu | Releia o co-design (PR body / ADR / lane) e compare **frase a frase**. O pior achado do #1247 foi um critério **invertido**, que faria o próximo agente implementar o contrário |
| Lane que absorveu escopo de outra | As duas dizem o mesmo? A doadora aponta o destino, a receptora declara a origem (#1340) |
| Contrato mudado deixa rastro em lane alheia | Se o PR mudou schema/enum/assinatura que outra lane cita, aquela lane virou stale |

## 4. Precisão — é o que foi medido ou o que se inferiu?

Cace **verbo de expectativa** sobre coisa não observada: "é esperado", "deve",
"vai passar", "se X falhar, então Y".

| Verificar | Como |
|---|---|
| Afirmação sobre CI/job | O job **rodou**? `gh run view <id>`. Job `skipping` não prova nada — o #1341 se autocorrigiu nisso: a premissa era que o job rodaria, e ele saiu `skipping` |
| "Gate existe / está fechado" | `gh pr view` — gate citado pode estar em **PR aberto**. "Existe" ≠ "mergeado em `main`" |
| Escopo declarado vs. diff | O PR body promete mais do que o diff entrega? O diff vence |
| Prosa que envelhece no rebase | Afirmação sobre estado de `main` ("hoje há 3 leitores") vira falsa sozinha. Prefira o predicado ("o gate hard-falha quando aparecer o próximo") |

## 5. Severidade e disposição

| Código | Quando | Disposição |
|---|---|---|
| `CLOSE-BLOCK` | Trabalho some, ou o doc **afirma falso**. Alguém decide errado lendo isso | Corrige **antes** de arquivar. Veredito `ABERTO` |
| `CLOSE-DRIFT` | Registro incompleto, mas nada falso e nada perdido | Corrige no mesmo PR docs-only, ou declara no §3 com dono. Veredito `FECHADO COM RESSALVA` |
| `CLOSE-POLISH` | Forma, redação, densidade | Lista e segue. Não gera PR |

## 6. Armadilhas medidas

- **Lane vira 2 PRs.** `ship_pr` nomeia um; o resto tem que estar no corpo.
  Qualquer verificação amarrada a "o PR da lane" fica verde-falso aqui.
- **`blocked` fica stale no merge da dependência.** A lane destravou e sumiu do
  pickup, porque ninguém revisita o status da bloqueada. Camada 1 pega.
- **§Deferimento é snapshot datado.** Ao corrigir, **acrescente emenda datada**;
  não reescreva o que a lane afirmou na época — isso apaga a trilha de por que
  a decisão foi tomada.
- **Nunca reserve ID de ADR em prosa.** Citar "ADR-NNN" para segurar o número
  não funciona: o alocador é `ls docs/adr/ | tail` e a menção é invisível aos
  gates. Trabalho deferido vira §Deferimento com dono, não ID reservado.
- **`_generated/` conflita em rebase.** Não resolva à mão: soft-reset e rode
  `python3 dev/build_doc_index.py`.
- **Status `open` significa pegável agora.** O enum não tem `ready`
  (`planned`/`open`/`in_progress`/`blocked`/`shipped`/`cancelled`).
- **Docs-only dispensa `pytest`, não o `pre-commit`.** PII, paths proibidos e
  formato de commit continuam valendo.

## 7. Coberto pela camada 1 — não gaste julgamento aqui

`ship_pr`/`ship_date` ausentes · deferimento órfão em lane fechada · PR
invisível no `_README` · contador `## Lanes (N)` · rota para lane morta ·
`blocked` com dependência já `shipped`.

Se um desses acendeu, é finding pronto: corrija e siga. Se não acendeu, **não
significa que a lane está fechada** — significa que a estrutura está.
