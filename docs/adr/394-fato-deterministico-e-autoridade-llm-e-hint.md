---
id: ADR-394
type: adr
title: "Fato determinístico é autoridade; saída de LLM é hint em vocabulário fechado"
status: Decidido
phase: A40.l66
date: "2026-08-18"
amended_at: ["2026-08-18", "2026-08-19"]
relates_to:
  - "[[ADR-081]]"
  - "[[ADR-090]]"
  - "[[ADR-097]]"
  - "[[ADR-259]]"
  - "[[ADR-261]]"
  - "[[ADR-272]]"
  - "[[ADR-292]]"
  - "[[ADR-357]]"
  - "[[ADR-358]]"
supersedes: []
superseded_by: []
aliases:
  - "ADR 394"
  - "fato determinístico é autoridade"
  - "ADR-A do PLAN-deterministic-authority"
tags:
  - type/adr
  - status/decidido
  - area/pipeline
  - phase/a40-l66
---

# ADR-394 — Fato determinístico é autoridade; saída de LLM é hint

**Status:** Decidido (A40.l66) • **Data:** 2026-08-18 • É a **ADR-A** do
[[PLAN-deterministic-authority]] (§ADRs a abrir), aberta pela [[A40.l66]].
Cobre 1a/1b/1c no corpo original; 1d entra pela emenda abaixo.

> **Emendada em 2026-08-18 (2×)** — a [[A40.l67]] anexa a regra que faltava,
> "prescrição exige cobertura; descrição admite ressalva", e a guarda de sinal
> do E5 que a materializa. A hierarquia de autoridade não muda; o que a emenda
> acrescenta é **o que fazer com o negativo que chega mesmo assim** ao balde
> publicado. Ver §Emenda 2026-08-18. A [[A40.l69]] anexa a segunda emenda do
> mesmo dia: a mesma regra vista pelo outro lado — valor **ausente** em vez de
> impossível. Ver §Emenda 2026-08-18 (b).
>
> **Emendada em 2026-08-19** — a §Emenda (b) shipou com um predicado que media
> o **contêiner**: `nao_apurado` era inalcançável em produção, e a taxa de 50%
> declarada abaixo era a do mecanismo pretendido, não a do código entregue.
> A raiz não era o predicado: era o **eixo de ano**, no grão do domicílio.
> Ver §Emenda 2026-08-19 (c).

## Contexto

`consolidate_baseline.py:501` decide ativo × passivo pelo **rótulo** que o LLM
escreveu:

```python
is_divida = categoria == "outros" and valor < 0
```

Na re-extração do run `7b64b6c7` o `categoria` de um financiamento flipou de
`"outros"` para `"imovel"`, a conjunção quebrou, e a dívida entrou em
`imoveis_consolidados` com valor negativo. O efeito atravessou E5, CV, parecer e
render: o defeito chegou ao leitor promovido a "ponto forte".

### O que a medição diz sobre a hierarquia (7 runs de agosto do dogfood)

O co-design ordenou a autoridade como *catálogo RFB > (secao, codigo) > sinal >
hint*. Medido sobre o corpus real, os dois primeiros degraus **não têm dado**:

| degrau | cobertura medida |
| --- | --- |
| catálogo RFB por `codigo` | `'11' → {imovel: 7, outros: 6}`; `'01' → 5 categorias`. `codigo_rfb` das dívidas do E1.6 **vazio em 6/6** |
| `(secao, codigo)` | `secao` **não existe** no contrato E1.5a — 0/89 itens |
| sinal do valor | flipa: o mesmo item sai `outros`/negativo em 2/7 runs e `imovel`/negativo em 5/7 |
| `categoria_hint` | a enum do prompt **não tem valor de passivo** — dívida só cabe em `"outros"` |

O espaço de `codigo` é **misto**: o `SYSTEM_PROMPT` do e15 ensina a tabela plana
pré-2019 (`"41" poupança`, `"45" CDB`) e o corpus tem `41/45/61/71/74/97`
convivendo com `01`–`12` grupo-shaped. O E1.6 emite `GG-CC` e `GG` no mesmo run.

**O sinal não é fato.** É um segundo campo autoral do mesmo gerador — e o prompt
nunca o pede. Tratá-lo como "o fato" é dar autoridade ao mesmo LLM com outro
chapéu.

### A autoridade estável existe, no artefato vizinho

`extract_irpf_full` (E1.6) separa `bens_direitos` × `dividas_onus` **por seção
da declaração** e devolve 6 dívidas em **7/7** runs — enquanto o rótulo do E1.5a
flipa em 5/7. E `consolidate()`, a irmã legada no mesmo arquivo, itera
`decl["bens_direitos"]`/`decl["dividas"]`: já roteia por seção e lê saldo devedor
**positivo**. São **duas implementações vivas roteando por seção**; só o caminho
`itens[]` — o plano, introduzido depois — perdeu a informação.

E1.6 é `FULL_ORDER[5]`, `consolidate_baseline` é `FULL_ORDER[4]`: nasce uma etapa
tarde demais para servir de fonte sem reordenar o pipeline.

### O critério de aceite original não separava os mundos

Provado por execução: um patch que implementa **só o sinal**, com catálogo e
`secao` inertes, deixa 3 dos 4 `xfail` da lane verdes e satisfaz a prova por
mutação prescrita em 4/4 flips. O entregável principal de 1a não era exercitado
por nenhum critério.

## Decisão

**D1 — a seção da declaração é a autoridade primária, e o E1.5a passa a
emiti-la.** A hierarquia do co-design é mantida na intenção (fato acima de
rótulo) e corrigida na ordem, porque o degrau que ela punha em primeiro não tem
dado:

1. **`secao`** — de qual ficha o item veio (`bens_direitos` | `dividas_onus`).
   Decide sozinha quando presente.
2. **`(secao, codigo)`** — refina o *subtipo* do ativo; nunca o eixo.
3. **sinal do valor** — veto **suficiente, nunca necessário**: negativo prova
   passivo; positivo não prova ativo (o IRPF declara saldo devedor positivo).
4. **`categoria_hint`** — último recurso, e sempre com `review_reason` quando é
   quem decide.

**D2 — o catálogo RFB entra por `(ano_base, secao, codigo)`, não por `codigo`.**
Estende `pipeline/llm/rfb_codes.py` com as seções de bens/direitos e
dívidas/ônus em YAML por ano-base. Sem `secao`, uma entrada de catálogo **não é
consultada** — código sozinho é ambíguo por medição, e consultar assim produz
adjudicação errada com cara de determinística.

**D3 — divergência entre degraus vira `review_reason`, nunca silêncio.**
Reusa `domain.baseline_divergence` ([[ADR-272]]); o schema declara que código
novo não pede migration, mas aqui nem código novo é preciso. Vale também para o
caso que hoje sai calado: dívida **positiva** rotulada como ativo.

**D4 — o agregado do LLM nunca sobrescreve a soma determinística.** O override
de `consolidate_from_itens` (`resumo.total_ativos` vence quando `pj_skipped ==
0`) é deletado. **Ordem é restrição dura:** medido, `resumo.total_passivos ≡
Σ|negativos|` em 7/7 — hoje o override *mascara* o defeito nos totais, então
deletá-lo **antes** do roteamento de D1 piora o run. D4 só aterrissa junto com
D1, nunca antes.

**D5 — conservação por eixo é medida contra a referência do mesmo grão.**
Medido: o `resumo` do agregado é a soma **de todos os anos** (7/7), porque
`_aggregate_baselines` soma os `resumo` per-file de anos distintos. Logo:

- **no E1.5a** (per-file, mono-ano): `Σ itens ≡ resumo`, por eixo, cents int,
  tolerância zero. Dispara 0% hoje — é contrato, não detector.
- **no E1.5c** (agregado, multi-ano): a conservação é **ano-cega** contra o
  `resumo` agregado e **por ano** contra a soma dos E1.5a. Exigir "por ano contra
  o `resumo` agregado" dispararia 100% por construção — seria erro de categoria,
  não achado.

**D6 — WARN-first.** Divergência rebaixa e declara (`review_reason` + stage
`degraded`, [[ADR-357]]); nunca `raise`, nunca retenção de run. Kill-switch por
env var, provado por teste.

**D7 — o contrato do E1.5a evolui aditivo primeiro.** `secao` entra
**opcional**; `categoria` ganha o irmão `categoria_hint` e o leitor aceita os
dois, com preferência pelo novo. Nenhum dos dois vira `required` no PR que o
introduz: há **766 artefatos E1.5a** gravados com `categoria`, o `read` não
valida mas o `write` do agregado valida, e o modo incremental relê todos e
agrega — um flip prematuro monta `itens[]` com as duas formas contra um schema
que admite uma só ([[ADR-261]] Tier 3). Boundary tolerante: valor de enum
desconhecido → `needs_review` no item, resto do documento extraído
([[ADR-292]]).

## Taxa de disparo medida (2026-08-18, pós-implementação)

Rodando o consolidador **real** sobre os 7 agregados dos runs completos de agosto
do dogfood, zero-write:

| sinal | disparo |
| --- | --- |
| **1c** — conservação ano-cega por eixo (cents int, tolerância zero) | **0/7** |
| **1a** — divergência fato × hint | **7/7** |
| valor negativo em balde de ativo | **0/7** (era 3/7 antes) |
| `dividas[]` | **6 entradas em 7/7 runs**, convergindo com `E1.6.dividas_onus` (antes: 4 em 4 runs e **2** nos 3 que consolidaram baseline stale) |

1c é **contrato, não detector**: fecha em todos os runs. O detector é 1a. Com o
cap de cardinalidade ([[ADR-272]] §Cap), run com o item flipado emite **2** razões
e run limpo emite **1** — a separação bate com a taxa de flip de 5/7 medida antes
do fix. Sem o cap eram 84 e 83: os dois mundos ficavam indistinguíveis.

## Consequências

- O `secao` só cobre documento **re-extraído**. Enquanto a cobertura não é 100%,
  o degrau 3 (sinal) segue decidindo o histórico — com `review_reason` sempre que
  for ele quem decide. A taxa de cobertura é medida e citada antes de qualquer
  flip para `required`.
- A prova por mutação precisa de **projeção canônica**: `property_id` é `uuid4()`
  por run, então dois runs do mesmo payload nunca são byte-idênticos. E precisa
  incluir o caso **positivo** e o caso **sem `secao`** — só o flip negativo é
  satisfeito pelo degrau do sinal sozinho e não prova nada acima dele.
- `previdencia` não tem ramo em `consolidate_from_itens` e cai em `outros`; o
  roteamento novo passa a nomeá-la. É correção de subtipo, não de eixo.
- **Deferido, datado (2026-08-18) · dono `data-engineer`:** o eixo de **ativos**
  em `_validate_e15_totals` mantém a tolerância histórica de R$ 1,00 (o de
  passivos nasceu em cents com tolerância zero). Apertá-lo é rebaseline dos
  goldens, com janela própria. Condição de retomada: cobertura de `secao` medida.
- **Deferido, datado (2026-08-18) · dono `data-engineer`:** flip de `secao` e
  `categoria_hint` para `required` no `e15_baseline_extract.schema.json`. Condição:
  cobertura 100% medida após a re-extração do corpus ([[ADR-261]] Tier 3).
- A unificação E1.5a × E1.6 continua deferida (§Deferimentos do plano, dono
  `senior-cto`), mas esta ADR registra que ela é o caminho **estruturalmente**
  certo: `secao` no E1.5a é a ponte enquanto os dois extratores existirem.

## Emenda 2026-08-18 — prescrição exige cobertura; descrição admite ressalva

Anexada pela [[A40.l67]] (item 1d do [[PLAN-deterministic-authority]]). O corpo
original decide **quem tem autoridade** para rotear um item. Falta a regra do
degrau seguinte: o que o relatório faz quando um valor impossível chega ao balde
publicado apesar do roteamento.

**A regra.** Um número **descritivo** (patrimônio, composição, dívida) publica
sempre — com ressalva quando o sistema sabe que ele está sujo. Um número
**prescritivo** ("aporte na classe X", "seu desvio máximo é Y%") só publica sobre
cobertura completa; sem ela é **suprimido com motivo declarado**, e o resto do
relatório sai inteiro. Suprimir a descrição esconderia o defeito exatamente onde
o leitor confere; emitir a prescrição sobre base incompleta o promoveria a
conselho.

### D5 — a reclassificação acontece no componente, nunca na linha da composição

`_compute_bruto` e `_build_composicao` (`patrimonio_calculator.py`) são **duas
somas independentes sobre os mesmos seis componentes**. Guarda que pós-processe
as linhas da `composicao` — zerando o balde e somando à dívida — dessincroniza os
dois agregados, e o `pct` por largest-remainder passa a distribuir sobre um total
que não existe. A reclassificação é **a montante das duas somas**: o componente
vai a zero, o montante vai para `total_dividas`, `composicao ≡ bruto` se preserva
e `patrimonio_liquido` não muda. O que muda é a honestidade da apresentação.

Uma primeira versão escrita sobre a `composicao` foi descartada sem commit ao
medir isto — guarda meio-certa que dessincroniza dois agregados é pior que guarda
nenhuma.

### D6 — negativo financeiro reclassifica; negativo físico só ressalva

| balde | negativo significa | ação |
| --- | --- | --- |
| `caixa_total_brl`, `investimentos_titular`, `investimentos_conjuge` | cheque especial, conta margem — **dívida de curto prazo legítima** | reclassifica: balde → 0, montante → `total_dividas`, publica normal |
| `residencia`, `imoveis_investimento`, `veiculos` | imóvel não vale menos que nada — **defeito de dado** | publica o valor, emite `review_reason`, suprime a prescrição |
| `imoveis_geradores`, `imoveis_nao_geradores` (split derivado) | idem, no split de cat_2 | idem — **sem mutar**: mutar quebraria `imoveis_investimento ≡ geradores + não-geradores ≡ imoveis_fisicos_brl` (invariante 4a) |

O físico não é reclassificado porque não há dívida a nomear: mover o montante
para `total_dividas` inventaria um passivo, e zerá-lo sem mover inventaria
patrimônio. Publicar com ressalva é a única saída que não fabrica número.

### Taxa de disparo medida (r5+r6, e os 4 runs anteriores)

Medido sobre `report_data.json` dos 6 runs completos do dogfood, campo a campo:

| nível | disparo | leitura |
| --- | --- | --- |
| 6 componentes < 0 | **0/36** (0 em 6 runs) | a guarda no componente não teria disparado em nenhum run |
| split derivado < 0 | **1/12** — só r6, `imoveis_nao_geradores` = −125.381,88 | é o único negativo publicado do corpus |
| linhas de `caixa_detalhes` < 0 | **6/6 runs**, sempre a mesma linha de −95,62 | anula dentro de um caixa de +257.683,53 |

Três consequências de desenho, todas medidas e não estimadas:

1. **A guarda mede agregado, não linha.** No nível da linha ela dispararia em 6/6
   runs por R$ 95,62 que se anulam dentro do próprio balde — ruído recorrente, o
   modo de falha que a [[A40.l67]] cita ao exigir a rota de reclassificação.
2. **O split derivado precisa estar coberto.** Ele é o único negativo publicado
   do corpus; uma guarda restrita aos 7 baldes [[ADR-145]] erraria exatamente o
   run que a motivou. No r6 o agregado `imoveis_investimento` seguia **positivo**
   (437.324,36) com o negativo escondido dentro do split.
3. **O disparo esperado em regime é 0.** O único disparo do corpus é o r6, cuja
   causa a [[A40.l66]] fechou a montante (o item negativo não chega mais a balde
   de ativo). A guarda é rede, não detector primário.

### Enforcement (linha 1d da §Enforcement do plano)

Default = o da tabela do plano: **reclassifica → publica; sobrevivente →
`needs_review`**. Kill-switch `MATHOMS_E5_SIGN_GUARD` com três estados, porque um
interruptor binário obriga a escolher entre ruído e cegueira:

- ausente → `enforce` (default): reclassifica, declara, e o sobrevivente pausa
  em `needs_review`. Nunca run vermelho — o artefato E5 já foi persistido.
- `warn` → reclassifica e declara no artefato, sem pausar. Rebaixa sem cegar.
- `off` → **status quo ante literal**, incluindo o clamp `max(0, caixa)` que o
  ramo de posições atuais aplicava. Kill-switch que não restaura o comportamento
  anterior não é kill-switch.

## Emenda 2026-08-18 (b) — cobertura por membro: zero apurado ≠ zero não apurado

Anexada pela [[A40.l69]] (itens 3a/3b do [[PLAN-deterministic-authority]]). A
emenda anterior decidiu o que fazer com **valor impossível**; esta decide o que
fazer com **valor ausente**. É a mesma regra — prescrição exige cobertura — vista
pelo outro lado: lá o número existia e estava errado, aqui ele não existe e o
relatório publicou `0,00` como se existisse.

### D7 — a cobertura é declarada por membro, em enum fechado

`fonte_investimentos` é uma string **do domicílio**: descreve o caminho que o
cálculo tomou, não se cada pessoa foi medida. Com o titular vindo de posições
atuais e o cônjuge de lugar nenhum, ela diz `"posicoes_atuais"` para os dois.

Campo próprio `cobertura_investimentos[]`, por membro, com três estados:

| estado | significado | publica |
| --- | --- | --- |
| `apurado` | fonte presente, valor apurado | o valor |
| `zero_apurado` | fonte presente, valor é zero | **0,00** — é a saída da ressalva |
| `nao_apurado` | sem fonte para o membro | **`null`** + ressalva + `needs_review` |

`null` e não `0,0`: um zero publicado é uma afirmação sobre o patrimônio da
pessoa, e o sistema não a mediu. `fonte_investimentos` permanece por compat de
leitor, mas deixa de responder "este membro foi medido?".

**Não sobrecarregar `pl_ressalva`** ([[ADR-346]]): ela mede posição de renda
variável **sem valor de mercado**, e membro sem posição alguma não produz ticker
sem marcação. São sinais distintos; fundi-los apagaria os dois.

### Taxa de disparo medida (por membro, 6 runs do dogfood)

A medição é **por membro**, nunca por workspace: um domicílio de 2 pessoas com 1
buraco contaria como "100% coberto" no denominador errado.

| run | `fonte_investimentos` | titular | cônjuge | `pl_ressalva` |
| --- | --- | --- | --- | --- |
| r1–r4 (07-25 → 08-04) | `posicoes_atuais+irpf` | 943.189,25 | 188.123,73 | `false` |
| r5 (`0a040a22`) | `posicoes_atuais` | 943.189,25 | **0,00** | `false` |
| r6 (`7b64b6c7`) | `posicoes_atuais` | 943.189,25 | **0,00** | `false` |

- **`nao_apurado` em r5+r6: 2/4 instâncias-membro (50%)**; sobre os 6 runs,
  **2/12 (17%)**. É o budget WARN-first do item 3a.
- **A regressão é datada e localizada.** Entre r4 (2026-08-04) e r5 (2026-08-16)
  o `fonte_investimentos` caiu de `posicoes_atuais+irpf` para `posicoes_atuais`:
  o fallback IRPF do cônjuge **deixou de disparar** (`if irpf_conjuge > 0`), e
  o balde foi de 188.123,73 para 0,00. Não é um zero antigo — é um valor que o
  relatório publicava e parou de publicar, sem dizer nada.
- **`pl_ressalva` é `false` em 6/6 runs** — inclusive nos 2 em que a cobertura
  quebrou. Isso mede, em vez de supor, que ela é **inerte** para esta classe: a
  ressalva não está quebrada, ela responde outra pergunta, e foi lida como "PL
  certificado".

### D8 — slug não canonicalizado não vira membro, e ninguém o absorve

`investments_consolidator.py` preserva o slug cru no miss do resolver
(`else: membro = membro_raw`) e `PatrimonioCalculator._compute_investimentos`
soma o não-atribuído ao titular (`if unattributed > 0: titular_val += unattributed`).
Os dois juntos creditam à pessoa errada, em silêncio. Miss do resolver passa a
produzir `nao_apurado` + `review_reason` nomeando o slug; o valor **não** migra.

Onde há CPF, CPF é a chave ([[ADR-267]]) — esta emenda não re-decide isso, só
proíbe que o agrupamento aconteça antes dele.

### O denominador do gate anti-substring, com o padrão declarado

Medido em `26293e93` com o padrão
`(titular_key|conjuge_key|_TITULAR_KEY|_CONJUGE_KEY)[^=<>!]* in `:

| arquivo | sites |
| --- | --- |
| `patrimonio_resolvers.py` | 12 |
| `analyze_finances.py` | 11 |
| `e5_member_resolver.py` | 10 |
| `patrimonio_calculator.py` | 2 |
| **total da classe** | **35** |

O padrão casa 38 linhas no repo; **3 são falso-positivo** e ficam fora do
denominador — `llm/validators.py` (2: `not in keys_seen`, membership em conjunto
de chaves) e `parecer_context_sanitizer.py` (1: `not in ("titular", "conjuge")`,
membership em tupla). A distinção é a que o gate precisa acertar: `chave in
string` é o defeito; `chave in coleção` é uso legítimo. Gate que não separe os
dois fecha sintaxe, não a classe.

## Emenda 2026-08-19 (c) — o predicado media o contêiner; a raiz era o eixo de ano

Anexada pela [[A40.l69]] depois de um ataque medido aos PRs que entregaram a
§Emenda (b). A regra de D7 não muda. O que muda é **como se decide que um membro
foi medido**, e a descoberta de que o defeito que D7 existe para nomear tinha
uma causa um andar abaixo.

### D9 — presença de linha não é evidência de medição; só valor é

`classificar_cobertura` tinha um 3º ramo: "tem bens no baseline ⇒ `zero_apurado`".
O predicado era `bool(conjuge_bens)`, e `build_members_from_consolidated`
materializa `bens` com 4 chaves **sempre** — dict literal de 4 chaves é truthy
mesmo com as 4 listas vazias. O predicado era constante `True` para qualquer
membro que o resolver produzisse.

Consequência medida: `nao_apurado` **inalcançável** no caminho de produção — 0 em
114 instâncias-membro do corpus. O `null` do balde, o `review_reason`
`domain_membro_nao_apurado` e a supressão da prescrição, os três efeitos do
estado, nunca armaram. A suíte ficou verde o tempo todo.

**O ramo sai.** Se o valor foi lido, o ramo do fallback IRPF já capturou; se não
foi, é `nao_apurado`. `zero_apurado` segue alcançável pelo ramo de posições
atuais (posição atribuída somando zero), que é onde ele sempre teve extensão.

Corolário para gate: **enum fechado de estado precisa de cobertura de estados
medida.** Estado que nunca ocorre é código morto ou predicado quebrado, e o teste
obriga a dizer qual dos dois. Gate:
`test_os_tres_estados_sao_alcancaveis_pela_fachada`.

### D10 — o ano-base é do membro, não do domicílio

`_max_value_year` reduz o baseline inteiro a **um** ano e `resolve_value_year` o
propaga a todos os membros. Com os cônjuges declarando em anos disjuntos isso é
aritmeticamente impossível de acertar: quem não tem item no ano escolhido cai no
fallback de `_resolve_item_valor` e vira `0,00`.

É a mesma conflação `null`↔`0,00` que D7 proíbe um andar acima, cometida um andar
abaixo — e a [[ADR-346]] já a decidiu ("ausência não vira zero"); ela só não fora
aplicada aqui.

Medido no corpus: o balde do cônjuge saía `0,00` com os 9 lançamentos dela
valorando **R$ 110.130,67** em 2023. A simetria prova que o defeito é do eixo e
não do cônjuge — forçando o ano do domicílio para 2023, quem zera é o **titular**.

Consequências:

- **Ano por membro**, com `ano_base` carimbado no dict de cada um. O agregado do
  domicílio pode misturar datas, e quem consome precisa poder ressalvar —
  [[ADR-383]] §6 já decidiu que consolidado de datas mistas **nunca leva data
  única**. Esta emenda aplica aquela regra no grão de membro.
- **`frescor` na linha de cobertura**: `fonte` responde de ONDE, `frescor`
  responde de QUANDO. A §Escopo da [[A40.l69]] pediu os dois e a implementação
  inicial shipou só `fonte`. Defasagem **não** vira estado do enum.
- **O top-up legado do titular** (`total_bens_summary` − sintético → titular) passa
  a valer só quando os dois membros estão no mesmo ano. `total_bens_summary` é de
  um ano só; com anos distintos a divergência dispara por construção e o resíduo
  fabricaria patrimônio — mesma família do `unattributed → titular` que a §D8
  cortou. Medido: sem a guarda o titular perdia R$ 110k.

### Correção da §Taxa de disparo medida (b)

A §Emenda (b) declara **`nao_apurado` em r5+r6: 2/4 (50%)** e 2/12 em 6 runs. Esse
número é a taxa do mecanismo **pretendido**, não a do código que shipou sob ele.
Re-medido em 57 runs com par baseline+investimentos (114 instâncias-membro):

| predicado do 3º ramo | `nao_apurado` | taxa |
| --- | --- | --- |
| `bool(bens)` — o que shipou na (b) | 0/114 | **0,0 %** |
| `any(bens.values())` | 0/114 | 0,0 % |
| `bens["investimentos"]` não-vazio | 0/114 | 0,0 % |
| exigir valor lido (D9) — **antes** do D10 | 5/114 | 4,4 % |
| exigir valor lido (D9) — **depois** do D10 | **0/114** | **0,0 %** |

Duas leituras que só a medição dá:

1. **O conserto óbvio não conserta.** Predicados de *presença* (`any`,
   lista não-vazia) medem exatamente o mesmo que o predicado quebrado. A
   distinção que importa é presença × valor.
2. **A ordem é restrição dura.** D9 sozinho suprimiria a prescrição em **5 de 5**
   dos runs recentes, publicando `null` para alguém cujo valor existe. Com D10
   antes, o valor volta pelo fallback IRPF e a taxa cai a zero — a guarda volta a
   ser **rede**, não detector primário, que é o que esta ADR diz que ela deve ser.

A tabela de sintomas da (b) (cônjuge `0,00`, `fonte=posicoes_atuais`,
`pl_ressalva=false` em 6/6) permanece verdadeira; o que era falso é a inferência
de que o classificador entregue rotularia aqueles casos `nao_apurado`.

### Deferimento datado — 2026-08-19, dono: [[A40.l69]]

Dois itens que esta emenda **não** decide, com condição de retomada:

1. **Trava anti-dupla-contagem no cônjuge dependente.** Bens de dependente vão na
   ficha do declarante (regra RFB), então somar o ano antigo de um membro que
   virou dependente do outro infla patrimônio fabricado. Medido neste corpus: o
   único dependente é o filho (`filho_filha`), o cônjuge é declarante
   independente em 100 % das declarações — a soma cross-ano é legítima **aqui**.
   A trava geral exige `dependentes`/`declarante` no artefato do E1.5c, que hoje
   **não os carrega** (medido: as chaves não existem no consolidado). É mudança
   de contrato do produtor. **Retomar** quando o E1.5c publicar o declarante.
2. **Válvula declarada para domicílio genuinamente sem investimentos.** Sob D9,
   um membro sem investimento nenhum só alcança `zero_apurado` se existir extrato
   de corretora no nome dele somando zero — artefato que quase nunca existe. Sem
   uma afirmação declarada ("este membro não tem investimentos"), esse domicílio
   fica `nao_apurado` e com prescrição suprimida sem caminho de saída dentro do
   produto. **Retomar** ao primeiro workspace real nessa configuração; a válvula
   é ADR nova quando for tomada (não reserve ID — precedente [[ADR-345]]).

O teto de defasagem para suprimir prescrição (quantos anos de distância entre os
membros tornam a composição ficção) também não é decidido aqui: com D10 a
defasagem passa a ser **declarada** em `frescor`, e o consumidor da regra é o
render, fora desta lane.
