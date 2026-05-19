# Runbook — Dedup PropertyIdentity por workspace

> **ADR:** [[ADR-225]] (Proposto · 2026-05-19) — estende [[ADR-215]] §3 com
> canonicalizer cascade + resolver loose-match + script backfill.
> **Owner:** Engenharia (dev on-call do workspace afetado).
> **Janela alvo:** ~5min dry-run + ~5min apply.

## Quando usar

Workspace com duplicatas visíveis no `/config` → "Residência principal e imóveis"
(ex.: 14 rows quando o usuário tem 5–6 imóveis físicos). Causas comuns:

1. **Multi-ano IRPF sem via+numero extraível** ("CASA QUADRA 33 LOTE 27"
   gera `endereco_canonical=NULL`, cada ano cria row separada).
2. **Cross-fonte mesma propriedade** (IRPF `codigo_rfb="11"` + fonte
   externa `codigo_rfb="01"` para mesmo endereço).

`dev/dedup_property_identity.py` cobre as duas via 3 passes idempotentes.

## Procedimento

### 1. Dry-run (obrigatório antes de aplicar)

```bash
MATHOMS_DATABASE_URL_SYNC="postgresql+psycopg2://..." \
  python3 dev/dedup_property_identity.py <workspace_id> \
  > _scratch/dedup-<workspace_id>-$(date +%F).json
```

Inspecione o JSON:

- `pass_0_recanonicalized` — rows NULL que ganham canonical via matrícula/QA/IPTU.
- `pass_1_strict_merged` — rows com `(codigo_rfb, endereco_canonical)` idênticos.
- `pass_3_cross_codigo_merged` — rows cross-codigo_rfb com 1 lado genérico ("01"/"").
- `pass_3_conflicts_need_human` — rows com **2+ subcódigos específicos divergentes**
  no mesmo endereço (ex.: `11` Apto + `12` Casa). **NÃO funde automaticamente**;
  exige decisão humana (lote com casa + apto coexistindo? merge errado de fonte?).

### 2. Apply (após review do dry-run)

```bash
MATHOMS_DATABASE_URL_SYNC="postgresql+psycopg2://..." \
  python3 dev/dedup_property_identity.py <workspace_id> --apply \
  > _scratch/dedup-applied-<workspace_id>-$(date +%F).json
```

Realocação de overrides (`workspace_property_overrides.property_id` →
canonical) é automática, contada em cada entry merged.

### 3. Verificação

Abra `/config` → "Residência principal e imóveis" no workspace afetado.
Contagem deve refletir imóveis físicos reais. Re-rodar o script em dry-run
deve produzir reporte vazio (idempotência).

## Conflitos manuais (`pass_3_conflicts_need_human`)

Quando o script lista conflitos, **não funda automaticamente**. Inspecione
`descricao_sample` dos `property_ids` envolvidos:

- **Falso conflito** (mesmo imóvel, codigos divergentes por erro de fonte
  ex.: "11" e "13" para mesmo apto): edite manualmente o `codigo_rfb` da
  row a manter, ajuste manualmente via SQL ou abra ADR para tratar.
- **Conflito real** (lote com casa + apto coexistindo): deixe duas rows;
  usuário classifica cada uma independente em `/config`.

## Rollback

Não há rollback automático — operação destrói rows duplicadas. Para reverter:
restore DB de snapshot pré-`--apply`. O JSON de output guarda
`canonical_id` + `dupes_dropped` + `overrides_realocados` para auditoria.

Por isso o dry-run é **obrigatório** antes de aplicar.
