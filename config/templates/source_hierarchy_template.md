# Source Hierarchy — Pipeline {{NOME_FAMILIA}}
## Versão: 1.0 — {{DATA_CRIACAO}}

> ⚠️ **TEMPLATE LEGADO v5.3 — obsoleto, não usar.** Gera artefatos do fluxo CLI antigo
> cujos destinos (`decisions.md` / `definitions.md` / `source_hierarchy.md`,
> `docs/methodology/`) são **paths proibidos** — migrados para o DB (ADR-134/136/137) ou
> para o renderer React (ADR-129). Mantido só como referência histórica.


---

## PRINCÍPIO FUNDAMENTAL

Novos extratos fornecidos são sempre a fonte primária de verdade e têm precedência sobre qualquer informação prévia.

---

## HIERARQUIA DE PRECEDÊNCIA

| Nível | Fonte | Exemplo | Quando usar |
|---|---|---|---|
| 1 — Primária | Documento original (.pdf, .jpg, .xlsx, .docx) | PDF de extrato bancário | Sempre que disponível |
| 2 — Secundária | Dados consolidados no manual de operações | Tabela de referência | Quando original não disponível |
| 3 — Terciária | Relatório HTML anterior | KPIs, gráficos | Para manter consistência visual |
| 4 — Estimativa | Projeção ou cálculo derivado | Renda projetada | Sinalizar explicitamente |

---

## REGRAS PRÁTICAS

### R1 — Extrato vence referência
Se extrato mostrar valor diferente do documentado, usar o valor do extrato e registrar divergência.

### R2 — Sinalizar estimativas
Quando dado não puder ser confirmado, sinalizar explicitamente como estimativa.

### R3 — Divergências relevantes
Ao identificar divergências >5%, destacar com impacto em cascata.

---

## CHECKLIST PRÉ-ATUALIZAÇÃO

Documentos a coletar antes de cada ciclo:
- Extratos bancários de todas as contas (3 meses)
- Faturas de todos os cartões (3 meses)
- Posições de investimento de todas as corretoras
- IRPF (se período de declaração)
- Holerites (se disponíveis)
- Documentos pessoais (se novos/renovados)
