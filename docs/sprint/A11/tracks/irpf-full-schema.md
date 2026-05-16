---
id: TRACK-irpf-full-schema
type: track
title: "Track IRPF Full Schema — extração completa de declaração de IRPF (E1.6)"
sprint: A11
status: consumed
created_at: null
consumed_at: null
agent_role: null
tags:
  - type/track
  - sprint/a11
  - status/consumed
---

# Track IRPF Full Schema — extração completa de declaração de IRPF (E1.6)

> **Lane ID:** irpf-full-schema
> **Branch prefix:** `agent/irpf-full-schema/*`
> **Depende de:** nada estrutural. Assume A7 ConfigStore mergeada e fix recente do classificador IRPF (commit `7164067` — `fix(documents): IRPF não fica mais "incerto"...`).
> **Conflita com:** `pipeline/llm/schemas/e15_baseline.py`, `pipeline/llm/prompts/e15_baseline.py`, `pipeline/stages/extract_baseline.py`, `pipeline/llm/validators.py`, `config/schemas/`, `scripts/e5_analyze.py` (consumidor downstream).
> **Onda:** independente — pode rodar paralela a Sprint A6/A7 desde que respeite os arquivos acima.
> **ADR:** **OBRIGATÓRIA** antes de codar (`G1`). Domínio + dados estruturados + custo LLM = decisão arquitetural.
> **Supervisão:** `G0` (financial-planner — cobertura metodológica) · `G1` (senior-cto — ADR) · `G2` (data-engineer — schema/contracts) · `G4` (product-designer — superficie no relatório).

> **Objetivo (1 frase):** capturar **todo** o conteúdo financeiro de uma declaração IRPF (rendimentos, imposto, dependentes, despesas dedutíveis), não só os bens e direitos — desbloqueando KPIs de renda anual, capacidade PGBL e otimização tributária no relatório de planejamento patrimonial.

---

## Por que esta lane

### Sintoma
Quando o usuário sobe um PDF de declaração IRPF, o pipeline hoje extrai **apenas** os itens patrimoniais (Bens e Direitos):

- `pipeline/llm/schemas/e15_baseline.py` → `BaselinePatrimonialOutput` tem só `items[]` (código RFB, descrição, categoria, valor BRL, membro, ano)
- `pipeline/llm/prompts/e15_baseline.py` → instrui o LLM a extrair "baseline patrimonial completo" — só ativos e passivos
- O E2-llm (extract_with_llm) tinha um schema ainda mais estreito (transactions + investments) e não foi pensado para IRPF — agora **não roda mais** em `data/income_tax_br/` (commit `7164067`)

Resultado: ~70% do conteúdo do PDF é descartado.

### O que falta

Para um relatório de planejamento financeiro/patrimonial sério (metodologias Perini/Cerbasi/AUVP), precisamos extrair também:

| Bloco | Campos | KPI/uso no relatório |
|---|---|---|
| **Identificação** | CPF (mascarado), ano-base, exercício, modelo completo/simplificado | Versionar declarações; exibir contexto |
| **Rendimentos tributáveis (PJ)** | Fonte pagadora (CNPJ + nome), valor bruto, IR retido, contribuição previdenciária, 13º | "Renda anual familiar" (Cerbasi) |
| **Rendimentos tributáveis (PF/exterior)** | Pagador, valor BRL, taxa de conversão, país | Renda total, exposição cambial |
| **Rendimentos isentos e não tributáveis** | Código RFB, descrição, valor, fonte | Dividendos, FGTS, indenizações, lucros distribuídos |
| **Tributação exclusiva/definitiva** | Código RFB, descrição, valor | 13º, JCP, ganho de capital |
| **Pagamentos efetuados** | Código RFB, beneficiário (CPF/CNPJ), valor pago, valor dedutível | Previdência, saúde, educação, pensão (Cerbasi: despesas estruturais) |
| **Imposto apurado** | Base de cálculo, IR devido, deduções, IR já pago, IR a pagar/restituir, alíquota efetiva | "Carga tributária real", capacidade de aporte líquido |
| **Dependentes** | CPF mascarado, nome, idade, relação | Dimensionamento da família, alocação de dedutíveis |
| **Doações** | Beneficiário, valor, código RFB (incentivos fiscais) | Otimização tributária |

### KPIs que ficam desbloqueados

- **Renda anual líquida real** = rendimentos tributáveis brutos − IR pago real − contribuições previdenciárias
- **Capacidade PGBL não usada** = `0,12 × rendimento_tributavel − pgbl_aportado_no_ano`
- **Carga tributária efetiva** vs alíquota nominal (compara à média Cerbasi de classe de renda)
- **Patrimônio líquido descontando IR diferido** em previdência privada (PGBL difere imposto)
- **Distribuição de dependentes** entre cônjuges para otimização (declaração separada vs conjunta)
- **Razão renda × patrimônio** (Perini: anos de IF acumulados)
- **Comparação histórica** ano a ano (capacidade de aporte crescendo? IR efetivo subindo? renda real?)

Sem nada disso, o relatório premium fica com lacuna estrutural — explica o "patrimônio" mas não a "renda" nem o "imposto" que produzem o patrimônio.

---

## Regras inegociáveis

1. **Money em `Decimal` / cents** ([ADR-090](../../../DECISIONS.md)). Wire JSON: string decimal. **Nunca `float`.** Aplica a `valor_brl`, `ir_retido`, `base_calculo`, etc.
2. **PII / LGPD**: CPF de contribuinte e dependentes **mascarado** ao serializar (`***.***.***-XX`). Nome completo OK no artifact (já no DB) mas **nunca em logs**. Validador deve recusar payload com CPF claro em campo `cpf_masked`.
3. **Schema novo, não substituir E1.5** — adicionar stage `E1.6` (descritivo: `extract_irpf_full`). E1.5 baseline patrimonial continua emitido (paridade legado, consumidores E5/E1.5c não quebram). Em janela de 1-2 sprints decidimos se E1.6 absorve E1.5 ou ficam coexistentes.
4. **Pipeline não importa `fastapi`/`celery`/`sqlalchemy`** ([CLAUDE.md "Pipeline não importa framework"](../../../../CLAUDE.md)). Domain services recebem value objects de config tipados ([ADR-097/D2](../../../DECISIONS.md)).
5. **Stateless rigoroso** ([ADR-111](../../../DECISIONS.md)) — sem `@lru_cache` no read-path; sem cache em memória de mais de uma chamada.
6. **JSON Schema validation** em `config/schemas/e16_irpf_full.schema.json` — modo strict habilitado por workspace via `pipeline.json → schema_validation.enabled`.
7. **Custo LLM**: PDF IRPF típico ≈ 30–60 páginas, ~80–120k tokens input, ~12–20k output. Estimar e documentar na ADR. Se >$1 USD/declaração → propor amostragem por seções (extrair em 2-3 chamadas).
8. **Idempotência**: re-rodar com mesmo input → mesmo output (modulo confidence flutuando). Goldens byte-a-byte garantem.
9. **Backwards-compatible**: arquivos `*-1.5a_extract.json` continuam sendo gerados por E1.5 (até decisão de cutover). Novos artefatos `*-1.6_irpf_full.json` adicionados.

---

## Entregáveis

### A. ADR (G1 — antes de codar)

- `docs/DECISIONS.md` ganha `ADR-NNN — Schema IRPF completo (stage E1.6)`.
- Cobre: problema, alternativas (estender E1.5 vs novo stage vs split em N stages), decisão, consequências (custo LLM, complexidade prompt, risco de alucinação em campos numéricos), PII/LGPD, plano de cutover E1.5 → E1.6.
- Roda gates: `python3 dev/check_adr_anchors.py && python3 dev/build_adr_toc.py --check && python3 dev/validate_adr_format.py`.

### B. Schemas

```
pipeline/llm/schemas/e16_irpf_full.py       # IRPFFullOutput + sub-models
config/schemas/e16_irpf_full.schema.json    # JSON Schema espelhado
```

Estrutura sugerida (ajustar com financial-planner):

```python
class Contribuinte(BaseModel):
    cpf_masked: str  # "***.***.***-XX"
    nome: str
    ano_base: int        # ano-calendário (2024)
    exercicio: int       # exercício (2025)
    modelo: Literal["completo", "simplificado"]
    natureza: Literal["titular", "dependente_titular"]  # quando declaração separada


class FontePagadoraPJ(BaseModel):
    cnpj: str
    nome: str
    rendimentos_tributaveis_brl: Decimal
    contrib_previdenciaria_brl: Decimal
    ir_retido_brl: Decimal
    decimo_terceiro_bruto_brl: Decimal | None = None
    decimo_terceiro_ir_retido_brl: Decimal | None = None


class RendimentoIsento(BaseModel):
    codigo_rfb: str  # ex: "09" (lucros distribuídos), "12" (FGTS)
    descricao: str
    valor_brl: Decimal
    fonte: str | None = None


class PagamentoDedutivel(BaseModel):
    codigo_rfb: str  # ex: "11" educação, "10" saúde, "36" PGBL
    beneficiario_nome: str
    beneficiario_cpf_cnpj_masked: str | None = None
    valor_pago_brl: Decimal
    valor_dedutivel_brl: Decimal


class ImpostoApurado(BaseModel):
    base_calculo_brl: Decimal
    ir_devido_brl: Decimal
    deducoes_totais_brl: Decimal
    ir_pago_brl: Decimal           # retido na fonte + carnê-leão
    ir_a_pagar_brl: Decimal | None = None
    ir_a_restituir_brl: Decimal | None = None
    aliquota_efetiva_pct: Decimal  # sobre rendimento bruto


class Dependente(BaseModel):
    cpf_masked: str
    nome: str
    relacao: Literal["filho", "conjuge", "pai_mae", "outro"]
    data_nascimento: str | None = None  # YYYY-MM-DD


class IRPFFullOutput(BaseModel):
    contribuinte: Contribuinte
    rendimentos_pj: list[FontePagadoraPJ] = []
    rendimentos_pf: list[FontePagadoraPF] = []
    rendimentos_exterior: list[RendimentoExterior] = []
    rendimentos_isentos: list[RendimentoIsento] = []
    rendimentos_tributacao_exclusiva: list[RendimentoTribExclusiva] = []
    pagamentos_efetuados: list[PagamentoDedutivel] = []
    imposto_apurado: ImpostoApurado
    dependentes: list[Dependente] = []
    doacoes: list[Doacao] = []
    bens_direitos: list[PatrimonialItem] = []  # paridade com E1.5
    confidence: float = Field(..., ge=0.0, le=1.0)
    notes: str | None = None
```

### C. Prompt

```
pipeline/llm/prompts/e16_irpf_full.py
```

Sistema: contador especialista IRPF. Regras explícitas:
- Códigos RFB canônicos (lista de tabela 9 + tabela de bens + códigos de pagamentos efetuados)
- Valores em Decimal numérico, sem máscara BR
- Datas YYYY-MM-DD
- CPF sempre mascarado conforme padrão acima
- Quando ano-calendário ambíguo, preferir o do "Identificação do Contribuinte" / "Resumo da Declaração"
- Confidence 1.0 se todas seções foram extraídas integralmente; 0.7 se algumas seções vazias por ausência no PDF; <0.7 se houve campos não-mapeados

### D. Validator

```
pipeline/llm/validators.py  →  validate_e16_output()
```

Checks:
- Soma rendimentos_pj + pf + exterior ≈ base de cálculo + isentos + exclusiva (com tolerância ADR-097/D5 = 0,01 BRL)
- IR retido ≤ IR devido (IRPF retido na fonte é adiantamento, nunca maior que devido líquido)
- IR a pagar XOR IR a restituir (não ambos ≠ 0)
- Aliquota efetiva entre 0 e 27,5%
- Dependentes com data de nascimento → idade ≤ 21 anos (ou universitário ≤ 24) ou inválido
- CPF format `\*{3}\.\*{3}\.\*{3}-\w{2}`

Erros de coerência → `validation.errors`. Discrepâncias suaves → `validation.warnings`.

### E. Stage runner

```
pipeline/stages/extract_irpf_full.py     (novo, descritivo conforme ADR-093)
```

- Lê `data/income_tax_br/` filtrando filename `irpfdeclaracao*` (recibos NÃO entram aqui — são apenas comprovante de envio)
- Uma chamada LLM por declaração (1 declaração = 1 contribuinte = 1 ano)
- `_artifact_key_for(doc)` espelhando E1.5: `{stem}-1.6_irpf_full.json`
- Persiste via `store.write("E1.6", artifact_key, payload)`
- Emite `LiveStep` (preparing → awaiting_llm → validating → persisting → finalizing)
- Min completion tokens: 16k (igual E1.5; payload é grande)
- Concurrency: igual `e2_llm` settings (default 4, max 8) — IRPF é I/O-bound

### F. Registry / artifact_store

- `pipeline/artifact_store.py`: adicionar mapping `E1.6 → E2_extracts/`, suffix `-1.6_irpf_full.json`
- `pipeline/stage_spec.py`: adicionar key descritiva `extract_irpf_full` ao registry, rodar **após** E1 (members) e **junto com** E1.5 (paralelo OK)

### G. Domain service + value objects

```
pipeline/domain/services/irpf_analyzer.py
pipeline/domain/types/irpf.py    # value objects frozen
```

Queries puras (sem I/O):
```python
class IRPFAnalyzer:
    def __init__(self, declarations: list[IRPFFullOutput]): ...

    def renda_anual_familiar(self, ano: int) -> Money: ...
    def ir_pago_total(self, ano: int) -> Money: ...
    def aliquota_efetiva_familiar(self, ano: int) -> Decimal: ...
    def pgbl_capacidade_dedutivel(self, ano: int) -> Money: ...  # 12% × renda tributável − já aportado
    def renda_liquida_familiar(self, ano: int) -> Money: ...
    def dependentes_validos(self, ano: int) -> list[Dependente]: ...
    def evolucao_renda_anos(self) -> dict[int, Money]: ...
```

### H. Integração E5

`scripts/e5_analyze.py` (ou `pipeline/domain/services/member_analyzer.py` + `e4_serialization.py`):

- Carrega `*-1.6_irpf_full.json` via `ArtifactStore.read("E1.6", ...)`
- Constrói `IRPFAnalyzer` no início do E5
- Adiciona seções no output do E5:
  - `renda_anual_consolidada`
  - `imposto_renda_familiar`
  - `otimizacao_tributaria` (capacidade PGBL, dependentes não usados, etc.)
- Mantém `baseline_patrimonial-1.5_consolidated.json` como source of truth para Bens & Direitos (até cutover)

### I. Frontend / Relatório

`config/report_layout.yaml` ganha seções:

- "Renda anual e impostos" (KPI: renda líquida, IR efetivo)
- "Otimização tributária" (capacidade PGBL não usada, dependentes ociosos, dedutíveis abaixo do ótimo)
- Cards mostrando trend ano a ano se ≥2 declarações

Codegen: rodar `python3 dev/codegen_report_layout.py` após editar YAML (frontend + backend dataclasses).

### J. Tests

```
tests/test_irpf_full_schema_unit.py        # validators, schema boundary cases
tests/test_irpf_full_extract_stage.py      # stage com LLM mock
tests/test_irpf_analyzer.py                # queries puras
tests/test_e5_with_irpf_full_golden.py     # golden byte-a-byte (1 IRPF anonimizado)
backend/tests/test_irpf_full_routes.py     # se expor endpoint admin de visualização
```

Fixture: `tests/fixtures/irpf_2024_anonimizado.pdf` + `tests/fixtures/expected/irpf_2024-1.6_irpf_full.json` (CPFs mascarados, valores realistas mas fictícios).

### K. Documentação

1. ADR (entrega A)
2. `docs/reference/PIPELINE_ARTIFACTS.md` ganha entrada E1.6
3. `docs/reference/ARCHITECTURE.md §4.1 Domain glossary` ganha entrada "IRPF completo (renda + imposto + dependentes)"
4. `docs/CHANGELOG.md` entrada datada quando mergear
5. `docs/BACKLOG.md` linha da lane (se ainda existir tabela ativa)
6. Atualizar `CLAUDE.md` § "Convenções de naming de artefatos" com sufixo `-1.6_irpf_full`

---

## Subagentes obrigatórios

| Gate | Quando | Subagente | O que aprovar |
|---|---|---|---|
| **G0** | Antes da ADR | `financial-planner` | Cobertura de campos vs metodologias Perini/Cerbasi/AUVP. KPIs realmente úteis no relatório de planejamento. Quais despesas dedutíveis priorizam. |
| **G1** | Antes de codar | `senior-cto` | ADR aprovada — incluindo decisão E1.6 separado vs estender E1.5, custo LLM, plano de cutover |
| **G2** | Antes de gravar schema/migration | `data-engineer` | Schema (Pydantic + JSON Schema), naming convention, contrato com E5, política de PII no DB |
| **G3** | Antes de PR | `senior-cto` (review) + `sre-devops` | Custo LLM observabilidade (tokens/USD por declaração no telemetry), retry strategy, schema_validation strict ON |
| **G4** | Antes de surface no relatório | `product-designer` | Hierarquia de informação, rótulos brasileiros corretos ("alíquota efetiva" vs "carga tributária"), formato monetário, copy de "Otimização tributária" |

---

## Sequência de commits sugerida

```
1. docs(adr): ADR-NNN schema IRPF completo (stage E1.6) — Proposto
2. feat(pipeline): IRPFFullOutput schema (Pydantic) + JSON Schema correspondente
3. feat(pipeline): prompt e16_irpf_full + validators
4. feat(pipeline): extract_irpf_full stage runner + artifact_store registration
5. feat(pipeline): irpf_analyzer domain service + value objects frozen
6. feat(pipeline): E5 consome IRPFAnalyzer — KPIs renda/imposto/PGBL
7. test(pipeline): goldens IRPF 2024 anonimizado + analyzer queries
8. feat(report): seções "Renda anual e impostos" + "Otimização tributária" no YAML + codegen
9. feat(frontend): componentes do relatório premium para os novos KPIs
10. docs(adr): ADR-NNN → Decidido + atualizar PIPELINE_ARTIFACTS + ARCHITECTURE glossary
11. chore: CHANGELOG + CLAUDE.md sufixos
```

Cada commit pequeno (≤300 linhas, ≤2 camadas). Diff cross-cutting (backend + pipeline + frontend) → quebrar.

---

## Definition of Done

- [ ] ADR-NNN aprovada por `senior-cto` (G1) e visível em `docs/DECISIONS.md`
- [ ] `financial-planner` validou cobertura metodológica (G0) — anexar transcrição como comentário no PR
- [ ] `data-engineer` aprovou schema + contracts (G2)
- [ ] `product-designer` aprovou superficie no relatório (G4)
- [ ] `pre-commit run --all-files` passa
- [ ] `pytest tests -q` + `pytest backend/tests -q` passam
- [ ] `cd frontend && npm test -- --run` passa
- [ ] Golden IRPF 2024 anonimizado passa byte-a-byte (`tests/fixtures/expected/irpf_2024-1.6_irpf_full.json`)
- [ ] Custo LLM medido em ≥3 declarações reais e dentro do budget proposto na ADR
- [ ] Relatório premium em workspace de demo exibe novos KPIs corretamente (renda anual, IR efetivo, capacidade PGBL)
- [ ] E5 produz métricas de renda/imposto consistentes com o conteúdo das declarações
- [ ] PR mergeada em `main` (commit `abc1234`) com CI verde — só então a lane vira `completed`

---

## Riscos / pontos de atenção

1. **Hallucination em valores numéricos.** LLMs tendem a "completar" valores plausíveis quando o PDF está confuso. Mitigação: validator estrito de coerência (somas, IR pago ≤ devido), confidence < 0,7 → `needs_review=True`, golden byte-a-byte.
2. **Variação de layouts entre PGD e e-CAC.** Anos diferentes têm formatos diferentes. Solução: prompt mostra os 3 formatos canônicos (PGD 2023, 2024, 2025).
3. **Documentos sem camada de texto.** PDFs scaneados — usar Claude vision (mesmo padrão de `e0_route._build_llm_messages`). Documentar custo extra.
4. **PII em logs.** Risco de log de CPF claro durante debug. Mitigação: validator recusa CPF claro no campo `cpf_masked`; logger formatter em `mathoms.*` masca padrões `\d{3}\.\d{3}\.\d{3}-\d{2}` automaticamente.
5. **Cutover E1.5 → E1.6.** Decidir se E1.6 substitui E1.5 (Bens & Direitos sai do baseline patrimonial) ou coexistem. Recomendado: coexistir por 1-2 sprints; depois E1.6 absorve via flag e E1.5 vira deprecated.
6. **Custo LLM por declaração.** Se passar de $1 USD/declaração, dividir extração em 2-3 chamadas (rendimentos + imposto/dedutíveis + dependentes/doações) e reconciliar.
7. **Regressão no relatório existente.** Os consumidores atuais de E1.5 (E1.5c, E5 patrimônio) não devem ser afetados. Goldens existentes precisam continuar passando.

---

## Referências

- Plano canônico que dispara esta lane: análise inicial em commit `7164067` ([fix(documents): IRPF não fica mais "incerto"...](https://github.com/davidrobert/mathoms/commit/7164067))
- ADRs relacionadas: [ADR-090](../../../DECISIONS.md) (Money), [ADR-093](../../../DECISIONS.md) (stage names descritivos), [ADR-097](../../../DECISIONS.md) (config tipados, money tolerância), [ADR-105](../../../DECISIONS.md) (ArtifactStore), [ADR-111](../../../DECISIONS.md) (stateless), [ADR-143](../../../DECISIONS.md) (rules-as-code)
- Schemas atuais: [pipeline/llm/schemas/e15_baseline.py](../../../../pipeline/llm/schemas/e15_baseline.py), [pipeline/llm/schemas/e2_llm_extract.py](../../../../pipeline/llm/schemas/e2_llm_extract.py)
- Prompts atuais: [pipeline/llm/prompts/e15_baseline.py](../../../../pipeline/llm/prompts/e15_baseline.py)
- Tabela RFB de códigos: documentação oficial em receita.fazenda.gov.br (anexo I do DIRPF de cada ano-calendário)
