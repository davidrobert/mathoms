---
id: ADR-434
type: adr
title: "O gate de PII mede o publicado, e a cobertura declarada é igual à medida"
status: Decidido
date: "2026-09-01"
phase: A40.l115
tags: [type/adr, status/decidido, area/backend, area/seguranca]
supersedes: []
superseded_by: []
amended_at: []
---

# ADR-434 — O gate de PII mede o publicado, e a cobertura declarada é igual à medida

## Contexto

A rodada unificada **U5** ([[ADR-416]], `RR9-16`) mediu no relatório publicado dois
identificadores: CPF **parcialmente mascarado** (só os 2 dígitos verificadores em claro)
e **agência + conta completas**, na mesma página. A política protegia um identificador e
publicava dois.

O enunciado do achado dizia que **nada** media o output. Medido, é falso pela metade:

- `/reports/{id}/data` **redige desde a [[A40.l6]]** ([[ADR-337]] c4) — `redact_view_model`
  varre toda string do payload servido. Rodado sobre o payload real do U5 (5.562 strings),
  dava **0 hits**;
- `/planner-review` **não redigia nada** — servia `content_json` cru;
- `suggestion_supersede` copia `acao`/`impacto_qualitativo` **verbatim** da prosa do LLM
  para `suggestions`, servida por `/suggestions` — terceiro egresso, que a redação do
  segundo não alcançaria.

O defeito no primeiro canal era **vocabulário**, não ausência de gate: `cartorial_pii_tipos`
cobria CPF/CNPJ crus, matrícula, CEP e endereço — nenhuma das três máscaras de CPF que o
produto emite, nem conta bancária.

E a docstring de `parecer_context_sanitizer` afirmava "Identificadores (CPF/CNPJ) são
redigidos". A frase é verdadeira para a forma **crua** e falsa para a mascarada — e valeu
como **justificativa de ausência de gate**: quem lia o módulo concluía que a cobertura
existia.

## Decisão

**D1 — O gate de output é um só, e o vocabulário dele é declarado.** `view_model_pii`
ganha `CPF_PARCIAL` e `CONTA`. Não se cria gate novo: o existente já tem scanner e gêmeo
de escrita e já roda no read-path. `TIPOS_COBERTOS` é a fonte única; a linha
`Tipos cobertos:` da docstring é **contrato comparado por teste**, não prosa.

**D2 — Cobertura declarada = cobertura medida, por igualdade de conjunto nas duas
direções.** Uma testemunha por tipo atravessa o detector **e** o redator. Tipo declarado
sem testemunha reprova; testemunha fora do vocabulário reprova; docstring que anuncia o
que o código não emite reprova. Um teste que comparasse `TIPOS_COBERTOS` consigo mesmo
sobreviveria à mutação da própria constante — seria o modo de falha desta ADR num arquivo
diferente.

**D3 — Os três egressos passam pela mesma definição de PII.** Leitura em
`/reports/{id}/data` e `/planner-review`; **escrita** em `suggestions`, porque a row é
imutável pós-insert ([[ADR-153]]) e redigir na leitura faria a linha persistida divergir
da servida. No parecer a redação é do **dict**, antes do tier filter: cobre `descricao`,
`evidencia` e todo campo futuro **por construção**, porque o walker chaveia no valor.

**D4 — Publica-se o que desambigua, oculta-se o que credencia.** Conta preserva os **4
últimos dígitos** (convenção de todo app bancário brasileiro); agência sai **inteira**.
Agência não desambigua — contas do mesmo banco a compartilham — e é a metade transacional
do par que um TED/boleto consome. Remover o número **inteiro** foi medido e rejeitado: as
4 linhas do `posicao_31_12` ficariam `'Conta Corrente'`, `'RDB/CDB'`, `'CDB'` — o nome da
instituição não está no rótulo (só existe como `cnpj_emissor`), e a linha perde identidade.

**D5 — O motivo de ano-base incompleto publica nome, não CPF.** A identidade continua
sendo o CPF (nome varia com a transcrição do PDF e fundiria membros); o que a mensagem
**exibe** passa a ser o nome. É mais útil ao dono, que não decora o CPF do cônjuge, e o
`parecer_context_sanitizer` já troca nome por **papel** antes do egresso — o provider
passa a ver "Cônjuge" onde via 2 dígitos de CPF.

**D6 — Sem backfill.** `report_publication.compute_immutable_hash` hasheia o snapshot E5;
reescrever `pipeline_artifacts` invalidaria o `immutable_hash` de todo mês publicado e
quebraria goldens e lineage. Redação na leitura, corte no produtor — o padrão da
[[ADR-337]]. **`immutable_hash` atesta o artefato, não os bytes servidos**; promessa de
produto que diga "verifique o hash" fica falsa.

## Consequências

- Sobre o payload real do U5, o gate passa de **0** para **7** hits — os 7 ofensores
  medidos independentemente, em 5.562 strings, **zero falso-positivo**.
- **O rótulo de conta vem em duas forças** porque este gate passou a rodar sobre PROSA,
  não só sobre rótulo de linha. `conta` é palavra hiperfrequente em pt-BR: a primeira
  versão redigia `conta: R$ 1.500` como `R$ •.500` e `levar em conta 2026` como `•026`.
  Corromper valor monetário ([[ADR-090]]) é pior que o vazamento que o gate evita. Rótulo
  fraco (`conta`/`poupança`) exige **forma de conta** — dígito verificador —, que dinheiro
  e ano não têm; rótulo forte (`ag`/`c/c`/`cc`) basta por si.
- Força do rótulo e natureza do dado são **eixos ortogonais**: `cc` é rótulo forte e é
  conta — preserva cauda, não zera.
- **Severidade corrigida vs. o registro.** Conta+agência completas é **Alto**. CPF
  parcial no *display* **não é achado**: a [[ADR-259]] §4 já sanciona `***.***.789-00`,
  com 5 dígitos em claro — `***.***.***-DD` é mais conservador que a política vigente. O
  que restava era o **egresso ao provider**, que a [[ADR-259]] §2 não sanciona (a regra lá
  é `cpf_present: bool`); isso é **Médio** e o remédio é D5.
- Residual declarado: E5 antigo re-consumido pelo parecer segue levando a nota **anterior**
  ao provider até ser re-gerado. Fechar isso exigiria mexer em `scrub_identifiers`, que é
  **input do LLM** e demanda eval ([[ADR-337]] §Consequências) — deliberadamente fora
  deste escopo.
- **Três vocabulários de PII coexistem** — `pii_patterns` (entrada do LLM),
  `view_model_pii` (saída publicada) e `tests/utils/lint_no_real_pii` (repo). Não se
  unificam: os limiares são legitimamente diferentes. Fica como deferimento datado
  declarar a **matriz** de qual gate cobre qual tipo — é a tese desta ADR aplicada a si
  mesma, e sem ela o par novo recria a mesma drift.
- **`instituicao` não contém instituição** — recebe `descricao or cnpj_emissor`, e as
  linhas de `fonte=extrato` põem ali outra coisa. O campo mente o nome, que é o modo de
  falha desta ADR repetido num campo publicado. `nome_emissor` existe, é obrigatório no
  schema e está no mesmo dicionário que `cnpj_emissor`. Deferido para lane própria com
  dono — ver §Deferimento.

## Deferimento datado (2026-09-01)

**`posicao_31_12[].instituicao` publica emissor.** Sem ele, a máscara troca
`'CDB - Conta 0001-123456789012'` por `'CDB'`, e duas aplicações do mesmo tipo só se
distinguem por o banco ter escrito "CDB" numa e "RDB/CDB" noutra — sorte de transcrição
do LLM, não desenho. Com emissor, o rótulo fica **melhor** que hoje, e destrava leitura
de concentração por risco de crédito e limite FGC (R$ 250k por CPF **por instituição**),
que hoje não é computável porque o dado não existe no payload.

**Condição de retomada:** antes da próxima publicação que dependa de identidade de linha
no `posicao_31_12`. **Dono:** a lane que fizer `nome_emissor` fluir de
`InformeFinanceiroPFPayload` → `baseline_informe_merger._build_entry` →
`_posicao_from_informe`.

**Caso de uso registrado e não atendido:** discriminação de Bens e Direitos no IRPF é o
único uso legítimo de agência+conta completas que sobreviveu ao exame. Rejeitado aqui
porque a fonte natural é o próprio informe que o usuário já tem, e atendê-lo por acidente
de transcrição é frágil. Se virar prioridade, exige campos **estruturados** e um modo de
exportação próprio — não uma string livre no card de posição patrimonial.
