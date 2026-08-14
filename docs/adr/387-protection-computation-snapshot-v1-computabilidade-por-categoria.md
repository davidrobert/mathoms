---
id: ADR-387
type: adr
title: "ProtectionComputationSnapshotV1 pina insumos ao run e declara computabilidade por categoria"
status: Decidido
phase: A40.l62
date: "2026-08-13"
amended_at: ["2026-08-14"]
relates_to:
  - "[[ADR-131]]"
  - "[[ADR-135]]"
  - "[[ADR-187]]"
  - "[[ADR-192]]"
  - "[[ADR-240]]"
  - "[[ADR-365]]"
supersedes: []
superseded_by: []
aliases: ["ADR 387", "ProtectionComputationSnapshotV1", "computabilidade de proteção"]
tags:
  - type/adr
  - status/decidido
  - area/backend
  - area/pipeline
  - area/persistence
  - area/report
  - area/financial-planning
  - phase/a40-l62
---

# ADR-387 — `ProtectionComputationSnapshotV1` pina insumos ao run

> **Decidido em 2026-08-14**, após co-design `financial-planner` +
> `data-engineer` e arbitragem `senior-cto`. A arquitetura está fechada antes da
> implementação; categoria sem contrato financeiro/fiscal aprovado permanece
> `missing_data`. Congelar um cálculo incorreto não satisfaz esta decisão.

## Contexto

O `Report` referencia um E5 exato pela [[ADR-131]], mas o adapter live de
proteção lê `Protection`, `FamilyMember` e `Workspace` mutáveis e usa o relógio
corrente. Recalcular no GET mudaria a mesma fotografia sem novo run, contra a
[[ADR-187]]. E1.x antigo também não é recuperável com precisão por run.

A [[A40.l61]] removeu cinco zeros e dois `False` fabricados. Restam dois
problemas distintos: capturar a fotografia correta e só declarar `computed`
quando pessoa, janela, unidade, inventário e regra sustentarem o cálculo.

## Decisão

### D1 — O `Report` é dono do snapshot imutável

`Report.protection_snapshot_json` será JSON nullable, pequeno, sem índice e sem
backfill. `NULL` significa exclusivamente Report legado. Report novo persiste um
envelope V1, ainda que `snapshot_status=unavailable` ou todas as instâncias
estejam `missing_data`; nenhum endpoint o atualiza depois do INSERT.

O snapshot e o Report nascem na mesma transação. Erro técnico inesperado gera
envelope `unavailable` com código estável e telemetria sem valores; nunca
fallback live nem meia-fotografia.

### D2 — Tudo que o cálculo lê já foi observado pelo run

O E5 exato em `analysis_artifact_id` emite bloco strict e versionado
`protection_computation_inputs_v1`. Ele contém a projeção mínima dos fatos
financeiros, cadastrais e fiscais observados no run, com proveniência e digest.
Não contém CPF, nomes, `policy_ref`, notas livres ou rows inteiras.

Fontes editáveis continuam relacionais; o run as projeta no E5. Criação e leitura
do Report não consultam aggregates live, E1.x `latest`, parâmetro fiscal corrente
ou `date.today()`. O endpoint `/protection-bundle` permanece live e não alimenta
Report histórico.

### D3 — Computabilidade é por instância, não por família

A identidade mínima é `(categoria, regra, subject_family_member_id | estate_subject_id)`.
FBAR, FATCA e Estate Tax NRA são checks independentes. Cada instância carrega:

- `computed | not_applicable | missing_data`, `reason_code` fechado e
  `missing_inputs` fechado;
- versão do calculator/regra, fontes, janela, unidade e data-base;
- inputs e outputs em cents/inteiros ou `null`.

`not_applicable` exige evidência positiva completa. Ausência, ambiguidade,
conflito, inventário parcial, unidade errada ou regra não aprovada é
`missing_data`. Calculator incompleto não roda nem emite gap, conselho ou risco.
Zero só é observado com proveniência e confirmação de completude.

### D4 — Gates financeiros e fiscais

- **Vida, por segurado:** dependência econômica explícita, renda ativa líquida
  recorrente de 12 meses completos, dívida atribuída e capital do mesmo segurado.
  `role`/idade não prova dependência adulta; ausência de apólice só vale zero com
  inventário confirmado para pessoa/categoria/data.
- **Invalidez, por segurado:** renda ativa e passiva líquidas na mesma janela e
  benefício mensal contratual. É proibido converter capital único em renda por
  `coverage_brl / 12`.
- **Sucessório, por cenário de falecimento:** titularidade/quinhão, meação,
  natureza e localização do direito, domicílio/UF e regra fiscal vigente. É
  proibido apresentar `patrimônio bruto familiar × alíquota de uma UF` como
  imposto devido. Referências de competência: [CF art. 155](https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm)
  e [LC 227/2026](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp227.htm).
- **EUA, por pessoa e ano:** FBAR usa U.S. person + contas financeiras fora dos
  EUA + máximo agregado; FATCA usa specified foreign financial assets +
  residência/filing status/valores aplicáveis; Estate Tax NRA usa NRA + ativos
  US-situs. Moeda USD, renda exterior e `has_us_assets` não substituem essas
  bases. Referências: [FinCEN FBAR](https://www.fincen.gov/report-foreign-bank-and-financial-accounts),
  [IRS Form 8938](https://www.irs.gov/businesses/corporations/do-i-need-to-file-form-8938-statement-of-specified-foreign-financial-assets) e
  [IRS Estate Tax NRNC](https://www.irs.gov/businesses/small-businesses-self-employed/frequently-asked-questions-on-estate-taxes-for-nonresidents-not-citizens-of-the-united-states).

### D5 — Fontes relacionais e regras por vigência

Perfil fiscal é por membro, nunca por `Workspace`. O PR1 da [[A40.l62]] cria
fonte relacional tipada para status fiscal/filing/residência e as três bases EUA;
`NULL` é não declarado e zero é declaração explícita. Dependência econômica,
segurado, modo de benefício e confirmação de inventário também ganham contrato
tipado; `FamilyMember.extra` não vira schema clandestino.

ITCMD e regras EUA não cabem na row IRPF atual. Uma tabela global
`fiscal_rule_sets(rule_code, jurisdiction_code, rule_version, effective_from,
effective_to, parameters_json, source)` usa modelos discriminados fechados para
`BR_ITCMD`, `US_FBAR`, `US_FATCA` e `US_ESTATE_NRA`. Zero ou múltiplas versões
vigentes retêm apenas o check afetado.

### D6 — Calculators atuais não são promovidos por plumbing

`compliance_risk_us_person` não pode produzir `computed` antes de separar os três
checks. A invalidez não usa o proxy capital/12. ITCMD simples só pode ser cenário
bruto claramente rotulado, nunca obrigação fiscal. Vida/invalidez não agregam
renda ou cobertura entre segurados. Correção dessas regras precede qualquer S9.

Copy permitida qualifica data, escopo e fonte: “a estimativa indica”. São
proibidos “cobertura adequada”, “sem risco”, “FBAR obrigatório” e prescrição de
produto, holding, LLC ou estrutura fiscal. Casos fiscais pedem validação de
especialista habilitado.

### D7 — Envelope V1 e proveniência

O schema Pydantic strict (`extra=forbid`) contém `snapshot_version`,
`snapshot_status`, `input_contract_version`, ids/digest do run e E5,
`captured_at`, `as_of_date`, versões dos calculators, `source_refs`, projeções
mínimas de família/apólices, referências fiscais, instâncias e bundle pronto.

`source_refs` discrimina `pipeline_artifact` (id/run/path JSON), `db_row`
(tabela/id/`observed_updated_at`) e `fiscal_rule_set` (id/versão/vigência).
Alterar semântica, enum ou shape obrigatório cria V2; o reader despacha por
`snapshot_version`.

### D8 — Publicação referencia o Report e usa hash versionado

`report_publications` ganha `report_id` nullable com FK `ON DELETE SET NULL` e
`hash_version`. Legado permanece `e5-v1`; publicação nova usa `report-v2`, exige
Report exato e valida `report.analysis_artifact_id == artifact_id`.

`report-v2` hasheia, com prefixo de domínio, o digest E5 legado versionado e a
serialização canônica integral do snapshot. Chaves reordenadas não mudam o hash;
`snapshot_version`, `captured_at`, vigências, fontes e versões entram. Não se
aplica `_strip_volatile` recursivo ao snapshot.

### D9 — Compatibilidade e leitura

E5 antigo continua válido. Report legado serve `protection_bundle: null`; não há
reconstrução histórica. `get_report_data` apenas injeta `snapshot.bundle`.
Imutabilidade é provada sobre o slice/digest de proteção — o GET inteiro ainda
possui lineage/comparações live e não promete bytes idênticos.

### D10 — Rollout

1. [[A40.l62]] PR1: contratos/fontes relacionais, bloco E5 V1, regras fiscais e
   correção dos calculators, com schema strict e goldens; nenhuma S9.
2. [[A40.l62]] PR2: migrations de Report/publicação, builder/persistência
   transacional, compatibilidade e hash `report-v2`; nenhuma S9.
3. [[A40.l35]]: projeção no view-model, S9, render/PDF e gate visual.

## Alternativas rejeitadas

- Recalcular no GET ou ler E1.x `latest`: mistura temporalidades.
- Snapshot como novo `PipelineArtifact`: pertence ao Report, não a um stage.
- Snapshot totalmente relacional: não há query analítica que pague as tabelas.
- Um resultado por workspace ou um único `us_assets_usd`: mascara pessoas e
  obrigações diferentes.
- Persistir o bundle atual: tornaria inferências erradas reproduzíveis.

## Critério de aceite

- Snapshot/slice não muda após editar cadastro, regra fiscal ou relógio.
- Novo Report sempre tem envelope V1; legado nunca cai em fallback live.
- Dois provedores e três checks EUA permanecem instâncias independentes.
- Ausência, zero confirmado e não aplicabilidade têm goldens distintos.
- Nenhum capital de invalidez é dividido por 12; nenhum ITCMD familiar é imposto
  devido; nenhum USD é inferido como situs.
- Reader usa fakes explosivos para provar zero acesso live.
- `report-v2` muda com qualquer byte semântico e `e5-v1` segue verificável.
- Schema E5/snapshot strict, migrations, OpenAPI/view-model, `golden_diff`,
  render/PDF e logs PII-zero ficam verdes antes de abrir a [[A40.l35]].
