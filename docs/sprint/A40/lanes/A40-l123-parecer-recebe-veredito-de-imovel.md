---
id: A40.l123
type: lane
title: "O parecer não recebe o veredito do balde de imóvel: lê como medida o número que pode conter a moradia, e pode prescrever vendê-la"
sprint: A40
plan: PLAN-report-trust
status: shipped
ship_pr: 2117
ship_date: "2026-10-09"
priority: P1
branch_slug: parecer-cobertura-imovel
owner: prompt-engineer
adrs:
  - "[[ADR-439]]"
  - "[[ADR-433]]"
  - "[[ADR-420]]"
  - "[[ADR-233]]"
depends_on: []
tags:
  - type/lane
  - sprint/a40
  - status/shipped
  - priority/p1
  - area/llm
  - area/pipeline
---

# A40.l123 — `parecer-recebe-veredito-de-imovel`

> **Origem:** desdobramento da [[A40.l113]] ([[ADR-439]]), aberta em 2026-10-08. Até aqui o
> único registro do item em `main` era o comentário de `dev/_planner_coverage_scope.py`, que
> apontava para um "§Deferimento da A40.l113" sem a linha — ponteiro pendurado, que ficaria
> órfão no fecho da l113 (achado do `product-manager`). **Fora da cláusula de reinício:** não
> muta E3/E5 (critério mecânico, precedente [[A40.l117]]).

## O defeito

O manifest do parecer é whitelist. Desde o #2049 o E5 publica
`patrimonio.cobertura_classificacao_imovel` — a fatia do **valor** de imóveis sem
classificação e um veredito por balde ([[ADR-439]] D1) — e o parecer não recebia nada.

Imóvel sem classificação cai no `else` dos splitters: conta como **não residência** e **não
gerador**. Daí a direção do erro, verificada no código:

| número que o parecer recebe | com fatia sem classificação |
|---|---|
| linha "Imóveis Investimento" da tabela de classes, total de imóveis de investimento | **teto** — pode conter a moradia |
| `ratios.concentracao_imobiliaria` ([[ADR-420]] §D2: numerador **e** denominador) | **teto** |
| patrimônio gerador (`imoveis_investimento` entra na carteira de renda) | **teto**; a TRS sobre ele é **piso** |
| IF ([[ADR-439]] D6: só geradores identificados) | **extremo conservador** |
| imobilização patrimonial (residência + cat_2) | insensível à classificação |

Com imóvel **sem valor apurado** ([[ADR-431]]) a direção é indeterminada: ele entra com zero.
O parecer podia prescrever "reduzir a concentração vendendo imóvel" sobre a casa da família —
e o dogfood U5 (`40d1af2a`) está nesse regime: residência identificada como piso, geradores
`vinculo_perdido`.

## Decisão (co-design 2026-10-08)

`prompt-engineer` (forma, custo, eval), `financial-planner` (direção do erro e guarda
prescritiva), `product-manager` (prioridade, aceite). Manifest **2.21.0**, MINOR
([[ADR-233]]); `PROMPT_VERSION` fica — nem prompt nem persona mudam.

- **4 campos** no bloco "Cobertura e incerteza": `pct_desconhecido` (base na label),
  `residencia.status`, `residencia.motivo`, `imoveis_geradores.status`. Labels curtas: o
  significado mora nos hints, fora do orçamento.
- **Fora, com razão** (escapes estreitos em `E5_FIELDS_FORA_DO_PARECER`): os R$ da partição
  (a ressalva usa a fatia em %), as contagens (a fatia que decide é de valor, [[ADR-433]]
  §D3; o imóvel sem valor já chega por `itens_sem_valor`), `overrides_sem_imovel`,
  `residencia_status` e `imoveis_geradores.motivo` (os três motivos dão a mesma direção na
  IF; o único uso seria pedido de cadastro). Os 3 baldes também ficam: o parecer recebe o
  veredito, não o número.
- **6 hints**, cada um ≤ 240 caracteres (limite do schema; 8 por seção). Veto à prescrição de
  venda de imóvel com fatia em aberto — diluir por aporte segue válido, confiança da
  concentração no máximo `media` (`financial-planner`: venda é irreversível, aporte acerta
  nos dois cenários); aluguel declarado sem prescrição de compra; código interno nunca na
  prosa nem convertido em pedido de cadastro (`prompt-engineer`). "Severidade da
  concentração" muda de `patrimonio` para `ratios`, texto idêntico, para abrir espaço.
- **Junto:** `_is_money_key` deixa de tomar `n_total` por dinheiro. Num E5 com o bloco, o
  catálogo de citação listava a contagem de imóveis como "R$ 5,00". O catálogo compõe o
  prompt e não entra na chave de cache, então só podia sair no mesmo bump.

## Medido

- Corpo orçado: **+203 B** no pior regime (motivo mais longo, fatia de três dígitos; o
  título do bloco já existe em todo E5 desde a [[A40.l83]]).
- **E5 real do dogfood** — run `40d1af2a` (o U5), autorizado pelo dono em 2026-10-08. Só
  bytes e ids de seção, sem o sanitizer nome→papel; o E5 do run é anterior ao #2049, então o
  bloco entrou no pior regime sintético:

  | manifest | corpo inteiro | após eviction | folga | evictadas |
  |---|---|---|---|---|
  | 2.19.0 | 19.529 B | 15.665 B | 719 B | `plano_acao_atual`, `investimentos`, `independencia_financeira` |
  | 2.20.1 | 19.944 B | 16.080 B | 304 B | idem |
  | 2.21.0 | 20.147 B | 16.283 B | 101 B | idem |

  O conjunto evictado não muda (critério 4). A folga é fina: a próxima da fila é `ratios`,
  onde mora a concentração, e foi por isso que duas labels encurtaram (77 B → 101 B).
- **Checagem com LLM real, braço único** — autorizada pelo dono: 9 chamadas, manifest
  2.21.0, E5 sintético PII-zero com concentração de ~60%, US$ 2,49. Com fatia em aberto (U5
  ×3, golden ×2): ressalva de classificação de imóvel em **5/5**, IF descrita como extremo
  conservador em **5/5**, **nenhuma** prescrição de venda e nenhum código interno na prosa
  renderizada. No controle (aluguel ×2, tudo apurado ×2): nenhum alarme de classificação,
  nenhuma ressalva de IF e nenhuma compra de moradia sugerida a quem aluga. Com N=9 só falha
  grosseira aparece, e não apareceu. Três sinais finos para o re-run: um caso lista "venda"
  entre os desfechos de uma avaliação de yield; o modelo copiou o código para o campo
  `evidencia`, que não é renderizado; e um run disse que o retrato "pode ser mais
  concentrado" — o oposto do teto.
- Débito herdado do gate de drift: **82 → 82** — nenhum escape consciente virou débito.
- Snapshot de ancorabilidade: `medicao` e `inancoraveis` intactos; entram só a versão e os 4
  paths projetados sem dado no corpus sintético.

## Critério de aceite

1. O bloco sai do escape amplo: folha nova sob ele reprova o gate de drift.
2. Matriz de 9 regimes montada pelo **produtor** (golden, U5, tudo apurado, aluguel, sem
   imóvel e um por motivo): o corpo carrega o veredito; typo de subpath reprova.
3. Hints só consomem [[ADR-439]] D2/D3/D6 e [[ADR-420]] §D2; vocabulário da residência
   fechado contra o produtor, por balde.
4. Orçamento: teto declarado de 240 B no pior regime; eviction no E5 real — ver §Medido.
   O parecer fica declarado como terceiro leitor do veredito em [[ADR-439]] §Gates.
5. Mutação: hint removido, campo removido, escape amplo restaurado e escape estreito
   removido reprovam.
6. **Comportamento do modelo:** verificado no 1º re-run da A40, como insumo operacional no
   `_README` da sprint (adendo de 2026-10-09 ao §Insumo declarado do 1º re-run) — não como
   cláusula desta lane, por decisão do `product-manager`. A checagem de braço único do
   §Medido antecipa o sinal, sem substituí-lo.

## Eval — por que o golden do parecer não ganha o caso

O corpus do golden e do holdout (`make_workspace_e5`) não tem o bloco; o holdout é lacrado e
ciclado por **posição** (eixo novo re-embaralha os 24); a única métrica do eval LLM é violação
de citação; e o golden mensal nunca rodou (sem secret). O caso criado é determinístico e mede
o que o modelo **vê**. A/B com LLM não serve: o braço 2.20.0 não recebe a informação, então o
resultado está decidido antes de rodar (`prompt-engineer`).

## Deferimento datado — 2026-10-08

1. **Checker pós-LLM** (lista de palavras, padrão `parecer_red_lines`) para prescrição de
   venda de imóvel com fatia em aberto e sem ressalva. Dono `prompt-engineer`; promover a red
   line é do `financial-planner`. Retomada: o re-run 1 mostrar a prescrição.
2. **O parecer do dogfood não vê IF nem investimentos.** Medido acima: desde a 2.19.0 o E5
   real evicta `independencia_financeira` e `investimentos`, e os hints delas orientam sobre
   dado ausente do corpo. O orchestrator não loga bytes do corpo nem seções evictadas, então
   isso só aparece medindo à mão. Anterior a esta lane e fora dela (`PV13-17` em
   [[PIPELINE-REVIEWS-active]] já registrava a eviction por seleção, sem lane). Dono
   `prompt-engineer` + `product-manager`. Retomada: **antes do 1º re-run**, porque muda a
   leitura do parecer dele.
3. **`pct_desconhecido` 0/0 publica 0,0** em família sem imóvel — zero sem evidência de zero.
   Dono `data-engineer`; não bloqueia (o veredito da residência diz `nao_declarada`).
4. **CTA de cadastro no parecer:** hoje o hint o proíbe. Reabrir é do `product-designer`, que
   também recebe a lateral do `financial-planner`: o card em `nao_declarada` diz "qual imóvel
   é", o que pressupõe casa própria.
5. **Sensibilidade da concentração** (publicar a concentração sem a fatia desconhecida), em
   lugar do piso da [[ADR-420]] §D2, que espera a escada da [[ADR-353]] — julgada imprópria
   para imóvel pela [[ADR-439]] D4. Dono `financial-planner`.
6. **[[A40.l112]] precisa de re-triagem** no fecho da l113: a cobertura que ela pede saiu no
   #2049, e o parecer passa a ressalvar a concentração — o KPI do relatório, não.
7. **Acoplamento com a [[A40.l122]]** (#2096 é o expand; o produtor emite no PR-B): quando o
   imóvel de uso não apurado ganhar linha própria na tabela de classes, o hint de `ratios`
   que chama "imóveis de investimento" de TETO deixa de valer para essa linha. Dono: o PR-C
   da l122, que já planeja as superfícies LLM — registrado na lane dela.
