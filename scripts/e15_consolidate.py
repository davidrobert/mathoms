#!/usr/bin/env python3
"""E1.5 Consolidate — Enriquece baseline patrimonial com chaves consolidadas.

Lê o baseline_patrimonial-1.5_consolidated.json (formato declarations) e
adiciona chaves consolidadas que o E5 consume diretamente:

  - imoveis_consolidados[]     (G01 do IRPF + imoveis_xlsx)
  - veiculos_consolidados[]    (G02 do IRPF + veiculos_xlsx)
  - investimentos_consolidados[] (G03/G04/G06/G07/G99 do IRPF)
  - dividas[]                  (dívidas de todas as declarations)
  - patrimonio_por_ano{}       (totais por ano-base)

Cada item consolidado inclui:
  - descricao, tipo, proprietario
  - valores_31_12.{ano} (padrão que E5._resolve_valor espera)
  - dados_completos (enriquecimento com XLSX quando disponível)

Uso:
  python scripts/e15_consolidate.py              # enriquece in-place
  python scripts/e15_consolidate.py --dry-run    # mostra sem salvar
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import scripts.pipeline_common as _pc

# ============================================================================
# Constants — re-inicializáveis via _init_config()
# ============================================================================
_DEFAULT_BASE_DIR = _pc._REPO_ROOT


def _load_json_config(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa paths e config globais a partir de base_dir."""
    global PROJECT_DIR, E2_DIR, BASELINE_FILE
    global _PIPELINE_CONFIG, _ARTIFACT_NAMES
    global _FAMILY, _TITULAR, _MEMBROS, _MEMBER_KEYS, _IMOVEL_MATCH_KEYWORDS
    PROJECT_DIR = base_dir
    E2_DIR = PROJECT_DIR / "processed" / "E2_extracts"
    _PIPELINE_CONFIG = _load_json_config(PROJECT_DIR / "config" / "pipeline.json")
    _ARTIFACT_NAMES = _PIPELINE_CONFIG.get("artifact_names", {})
    BASELINE_FILE = E2_DIR / _ARTIFACT_NAMES.get(
        "baseline_patrimonial", "baseline_patrimonial-1.5_consolidated.json"
    )
    _FAMILY = _load_json_config(PROJECT_DIR / "config" / "family_members.json")
    _TITULAR = _FAMILY.get("titular", "")
    _MEMBROS = _FAMILY.get("membros", {})
    _MEMBER_KEYS = [k for k in _MEMBROS if not k.startswith("_")]
    _IMOVEL_MATCH_KEYWORDS = _FAMILY.get("imovel_match_keywords", [])


# =============================================================================
# Module-level defaults (Sessão A6d.1 — eliminado side-effect no import)
# =============================================================================
#
# Antes de A6d.1: módulo invocava ``_init_config(_pc.PROJECT_DIR)`` no nível
# de módulo. Agora os globals começam com defaults; ``_init_config(base_dir)``
# é invocado explicitamente por ``main(root_dir=...)`` / ``main_with_store(ctx)``.
PROJECT_DIR: Path = _DEFAULT_BASE_DIR
E2_DIR: Path = PROJECT_DIR / "processed" / "E2_extracts"
_PIPELINE_CONFIG: dict = {}
_ARTIFACT_NAMES: dict = {}
BASELINE_FILE: Path = E2_DIR / "baseline_patrimonial-1.5_consolidated.json"
_FAMILY: dict = {}
_TITULAR: str = ""
_MEMBROS: dict = {}
_MEMBER_KEYS: list = []
_IMOVEL_MATCH_KEYWORDS: list = []

# IRPF grupo → categoria
GRUPO_MAP = {
    "01": "imovel",
    "02": "veiculo",
    "03": "investimento",  # Participações societárias, ações
    "04": "investimento",  # Aplicações de renda fixa
    "06": "conta_bancaria",  # Depósitos, contas, moeda estrangeira
    "07": "investimento",  # Fundos de investimento
    "99": "investimento",  # Outros bens
}


def safe_float(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.replace(".", "").replace(",", ".").strip()
        try:
            return float(v)
        except ValueError:
            return 0.0
    return 0.0


def normalize_grupo(grupo: Any) -> str:
    """Normalize IRPF grupo: 'G01' → '01', '1' → '01', 1 → '01'."""
    s = str(grupo).strip().upper()
    # Strip 'G' prefix
    if s.startswith("G"):
        s = s[1:]
    return s.zfill(2)


def _match_imovel_xlsx(descricao_irpf: str, imoveis_xlsx: List[dict]) -> Optional[dict]:
    """Try to match an IRPF imóvel to an imoveis_xlsx entry by keyword overlap."""
    desc_lower = descricao_irpf.lower()
    best_match = None
    best_score = 0

    for im in imoveis_xlsx:
        nome = im.get("nome", "").lower()
        endereco = im.get("endereco", "").lower()

        # Score by keyword overlap
        score = 0
        keywords_nome = set(re.findall(r"\w{4,}", nome))
        keywords_end = set(re.findall(r"\w{4,}", endereco))
        keywords_desc = set(re.findall(r"\w{4,}", desc_lower))

        score += len(keywords_nome & keywords_desc) * 3
        score += len(keywords_end & keywords_desc) * 2

        for kw in _IMOVEL_MATCH_KEYWORDS:
            if kw in desc_lower and (kw in nome or kw in endereco):
                score += 10

        # Cross-match: IRPF building name ↔ XLSX street/nome
        # E.g., building name in IRPF matches street in XLSX if both
        # refer to same apt number
        irpf_apt = re.search(r"apt[o]?\s*(\d+)", desc_lower)
        xlsx_apt = re.search(r"apt[o]?\s*(\d+)", (nome + " " + endereco).lower())
        if irpf_apt and xlsx_apt and irpf_apt.group(1) == xlsx_apt.group(1):
            score += 8

        # Date match: IRPF "ADQUIRIDO EM DD/MM/YYYY" ↔ XLSX data_compra (±7 days)
        xlsx_data = im.get("data_compra", "")
        if xlsx_data:
            irpf_date_m = re.search(r"(\d{2})/(\d{2})/(\d{4})", desc_lower)
            if irpf_date_m:
                try:
                    from datetime import date as _date

                    irpf_d = _date(
                        int(irpf_date_m.group(3)),
                        int(irpf_date_m.group(2)),
                        int(irpf_date_m.group(1)),
                    )
                    xlsx_d = _date.fromisoformat(xlsx_data)
                    if abs((irpf_d - xlsx_d).days) <= 7:
                        score += 15  # Strong signal: same acquisition date (±7 days)
                except (ValueError, TypeError):
                    pass

        if score > best_score:
            best_score = score
            best_match = im

    return best_match if best_score >= 3 else None


def consolidate(baseline: dict, resolver=None) -> dict:
    """Add consolidated keys to baseline from declarations + XLSX data.

    Suporta dois formatos de input do E1.5:
      - Legacy: ``{declarations: [...], imoveis_xlsx: [...]}``
      - Atual (schema flat, ADR-*):
        ``{itens: [{codigo, descricao, categoria, valor_brl, membro, ano}],
           resumo: {...}, _meta: {...}}``

    Quando detecta o formato atual, delega para :func:`consolidate_from_itens`.
    """
    if isinstance(baseline.get("itens"), list) and baseline.get("itens"):
        return consolidate_from_itens(baseline, resolver=resolver)

    declarations = baseline.get("declarations", [])
    imoveis_xlsx = baseline.get("imoveis_xlsx", [])
    veiculos_xlsx = baseline.get("veiculos_xlsx", [])

    if not declarations:
        print("  [WARN] Nenhuma declaration encontrada no baseline")
        return baseline

    # =========================================================================
    # 1. Group declarations by member, keep most recent ano_base
    # =========================================================================
    member_decls: Dict[str, dict] = {}
    all_anos: set = set()
    for decl in declarations:
        membro = decl.get("membro", "").lower()
        ano = decl.get("ano_base", 0)
        all_anos.add(ano)
        key = next((mk for mk in _MEMBER_KEYS if mk in membro), None)
        if key is None:
            continue
        if key not in member_decls or ano > member_decls[key].get("ano_base", 0):
            member_decls[key] = decl

    ano_ref = max(all_anos) if all_anos else (date.today().year - 1)
    print(f"  [E1.5] ano_ref={ano_ref}, membros={list(member_decls.keys())}")

    # =========================================================================
    # 2. Build consolidated lists from declarations
    # =========================================================================
    imoveis_consolidados: List[dict] = []
    veiculos_consolidados: List[dict] = []
    investimentos_consolidados: List[dict] = []
    dividas_consolidadas: List[dict] = []
    patrimonio_por_ano: Dict[str, dict] = {}

    used_xlsx_imoveis: set = set()  # track matched XLSX entries

    for member_key, decl in member_decls.items():
        ano = decl.get("ano_base", ano_ref)
        ano_str = str(ano)
        bens = decl.get("bens_direitos", [])

        member_bens_total = 0.0
        member_dividas_total = 0.0

        for bem in bens:
            grupo = normalize_grupo(bem.get("grupo", ""))
            categoria = GRUPO_MAP.get(grupo, "investimento")
            valor_atual = safe_float(bem.get("situacao_atual", 0))
            valor_anterior = safe_float(bem.get("situacao_anterior", 0))
            descricao = bem.get("descricao", "")

            member_bens_total += valor_atual

            entry = {
                "descricao": descricao,
                "proprietario": member_key,
                "valores_31_12": {
                    ano_str: valor_atual,
                },
            }
            # Include previous year if available
            if valor_anterior > 0:
                ano_anterior = str(ano - 1)
                entry["valores_31_12"][ano_anterior] = valor_anterior

            if categoria == "imovel":
                entry["tipo"] = "imovel"
                # codigo_rfb necessário para PropertyIdentity (ADR-215 P2).
                entry["codigo_rfb"] = str(bem.get("grupo", "") or "").strip()
                entry["ano_referencia"] = ano
                # Try to enrich with XLSX data
                xlsx_match = _match_imovel_xlsx(descricao, imoveis_xlsx)
                if xlsx_match:
                    idx = id(xlsx_match)
                    used_xlsx_imoveis.add(idx)
                    entry["endereco"] = xlsx_match.get("endereco", "")
                    entry["dados_completos"] = {
                        "imovel": xlsx_match.get("nome", ""),
                        "endereco": xlsx_match.get("endereco", ""),
                        "data_compra": xlsx_match.get("data_compra"),
                        "valor_compra": xlsx_match.get("valor_compra"),
                        "situacao": xlsx_match.get("situacao_atual", ""),
                        "financiamento": xlsx_match.get("financiamento"),
                    }
                imoveis_consolidados.append(entry)

            elif categoria == "veiculo":
                entry["tipo"] = "veiculo"
                veiculos_consolidados.append(entry)

            elif categoria == "conta_bancaria":
                # Contas bancárias: treat as investimento for E5 purposes
                entry["tipo"] = "conta_bancaria"
                investimentos_consolidados.append(entry)

            else:  # investimento
                entry["tipo"] = _classify_investimento(grupo, descricao)
                investimentos_consolidados.append(entry)

        # Process dívidas from declaration
        for div in decl.get("dividas", []):
            valor_atual = safe_float(div.get("situacao_atual", 0))
            valor_anterior = safe_float(div.get("situacao_anterior", 0))
            member_dividas_total += valor_atual

            dividas_consolidadas.append(
                {
                    "descricao": div.get("descricao", ""),
                    "proprietario": member_key,
                    "saldo_31_12": {
                        ano_str: valor_atual,
                    },
                }
            )
            if valor_anterior > 0:
                dividas_consolidadas[-1]["saldo_31_12"][str(ano - 1)] = valor_anterior

        # Patrimônio por ano
        if ano_str not in patrimonio_por_ano:
            patrimonio_por_ano[ano_str] = {"total_bens": 0.0, "total_dividas": 0.0}
        patrimonio_por_ano[ano_str]["total_bens"] += member_bens_total
        patrimonio_por_ano[ano_str]["total_dividas"] += member_dividas_total

    # =========================================================================
    # 3. Add imoveis_xlsx entries not matched to IRPF
    # =========================================================================
    for im in imoveis_xlsx:
        if id(im) not in used_xlsx_imoveis:
            print(
                f"  [INFO] Imóvel XLSX sem match IRPF: {im.get('nome', '?')} (membro={im.get('membro', '?')})"
            )
            entry = {
                "descricao": im.get("nome", ""),
                "proprietario": im.get("membro", _TITULAR),
                "endereco": im.get("endereco", ""),
                "tipo": "imovel",
                "valores_31_12": {
                    str(ano_ref): safe_float(im.get("valor_compra", 0)),
                },
                "dados_completos": {
                    "imovel": im.get("nome", ""),
                    "endereco": im.get("endereco", ""),
                    "data_compra": im.get("data_compra"),
                    "valor_compra": im.get("valor_compra"),
                    "situacao": im.get("situacao_atual", ""),
                    "financiamento": im.get("financiamento"),
                },
                "fonte": "xlsx_only",
            }
            imoveis_consolidados.append(entry)

    # =========================================================================
    # 4. Add veiculos_xlsx entries
    # =========================================================================
    for v in veiculos_xlsx:
        veiculos_consolidados.append(
            {
                "descricao": f"{v.get('marca', '')} {v.get('modelo', '')} {v.get('ano', '')}".strip(),
                "proprietario": v.get("membro", _TITULAR),
                "tipo": "veiculo",
                "valores_31_12": {
                    str(ano_ref): safe_float(v.get("valor_aquisicao", 0)),
                },
                "fonte": "xlsx",
            }
        )

    # =========================================================================
    # 5. Round patrimonio_por_ano
    # =========================================================================
    for ano_str, data in patrimonio_por_ano.items():
        data["total_bens"] = round(data["total_bens"], 2)
        data["total_dividas"] = round(data["total_dividas"], 2)

    # =========================================================================
    # 6. Print summary
    # =========================================================================
    print("  [E1.5] Consolidado:")
    print(f"    Imóveis: {len(imoveis_consolidados)}")
    print(f"    Veículos: {len(veiculos_consolidados)}")
    print(f"    Investimentos/Contas: {len(investimentos_consolidados)}")
    print(f"    Dívidas: {len(dividas_consolidadas)}")
    for ano_str, data in sorted(patrimonio_por_ano.items()):
        print(
            f"    Patrimônio {ano_str}: bens R$ {data['total_bens']:,.2f}, dívidas R$ {data['total_dividas']:,.2f}"
        )

    # =========================================================================
    # 7. Merge into baseline
    # =========================================================================
    baseline["imoveis_consolidados"] = imoveis_consolidados
    baseline["veiculos_consolidados"] = veiculos_consolidados
    baseline["investimentos_consolidados"] = investimentos_consolidados
    baseline["dividas"] = dividas_consolidadas
    baseline["patrimonio_por_ano"] = patrimonio_por_ano

    return baseline


def _build_member_resolver(ctx):
    """ADR-267: constrói MemberNameResolver com CPF a partir de family_members do ctx."""
    from pipeline.domain.services.member_name_resolver import MemberNameResolver, MemberRecord

    try:
        fmc = ctx.config_store.get_family_members(ctx.workspace_id)
    except Exception:
        return None
    if fmc is None or not getattr(fmc, "members", None):
        return None
    records = tuple(
        MemberRecord(
            key=m.key,
            full_name=m.full_name or "",
            short_name=m.short_name or "",
            cpf=m.cpf or "",
        )
        for m in fmc.members
    )
    return MemberNameResolver(records)


def _resolve_member(item: dict, resolver) -> str:
    """ADR-267 cascade: CPF (estratégia 0) → name resolver → raw string fallback."""
    if resolver is None:
        return (item.get("membro") or _TITULAR or "").strip().lower()
    # Estratégia 0: CPF invariante.
    cpf = item.get("cpf")
    if cpf and (res := resolver.resolve_by_cpf(cpf)).canonical_key:
        return res.canonical_key
    # Estratégia 1-5: nome.
    membro_raw = item.get("membro") or ""
    if membro_raw and (res := resolver.resolve(membro_raw)).canonical_key:
        return res.canonical_key
    return (item.get("membro") or _TITULAR or "").strip().lower()


def consolidate_from_itens(baseline: dict, resolver=None) -> dict:
    """Consolida schema flat ``itens[]`` do E1.5 atual para as chaves que o E5 espera.

    Schema esperado no input::

        {
          "itens": [
            {"codigo", "descricao", "categoria", "valor_brl", "membro", "ano", "instituicao"?, "cpf"?}
          ],
          "resumo": {"total_ativos", "total_passivos", "patrimonio_liquido", "ano_referencia", "membros"},
          "_meta": {...}
        }

    Categoria ``"outros"`` com ``valor_brl < 0`` é tratada como dívida (valor absoluto).
    Categoria ``"outros"`` com ``valor_brl >= 0`` vira investimento tipo ``outros``.

    ADR-267: quando ``resolver`` (MemberNameResolver) é fornecido E o item traz ``cpf``,
    a identidade do membro é resolvida via CPF (estratégia 0). Fallback: ``item["membro"]``
    como antes. Sem resolver, comportamento legado preservado (backwards compat).
    """
    itens = baseline.get("itens", [])
    resumo = baseline.get("resumo", {})
    ano_ref = resumo.get("ano_referencia") or (date.today().year - 1)
    ano_str = str(ano_ref)

    imoveis_consolidados: List[dict] = []
    veiculos_consolidados: List[dict] = []
    investimentos_consolidados: List[dict] = []
    dividas_consolidadas: List[dict] = []
    total_bens = 0.0
    total_dividas = 0.0

    for item in itens:
        valor = safe_float(item.get("valor_brl", 0))
        categoria = (item.get("categoria") or "").strip().lower()
        # ADR-267: CPF primeiro (cross-year invariant); fallback nome via resolver
        # ou string raw (legado). Resultado é sempre canonical key lowercase.
        membro = _resolve_member(item, resolver)
        descricao = item.get("descricao", "")

        is_divida = categoria == "outros" and valor < 0
        if is_divida:
            dividas_consolidadas.append(
                {
                    "descricao": descricao,
                    "proprietario": membro,
                    "saldo_31_12": {ano_str: abs(valor)},
                }
            )
            total_dividas += abs(valor)
            continue

        entry = {
            "descricao": descricao,
            "proprietario": membro,
            "valores_31_12": {ano_str: valor},
        }
        if item.get("instituicao"):
            entry["instituicao"] = item["instituicao"]

        if categoria == "imovel":
            entry["tipo"] = "imovel"
            # codigo_rfb necessário para PropertyIdentity (ADR-215 P2).
            entry["codigo_rfb"] = str(item.get("codigo", "") or "").strip()
            entry["ano_referencia"] = ano_ref
            imoveis_consolidados.append(entry)
        elif categoria == "veiculo":
            entry["tipo"] = "veiculo"
            veiculos_consolidados.append(entry)
        elif categoria == "poupanca":
            entry["tipo"] = "poupanca"
            investimentos_consolidados.append(entry)
        elif categoria == "conta_corrente":
            entry["tipo"] = "conta_bancaria"
            investimentos_consolidados.append(entry)
        elif categoria == "investimento":
            entry["tipo"] = _classify_investimento(
                normalize_grupo(item.get("codigo", "")), descricao
            )
            investimentos_consolidados.append(entry)
        else:  # "outros" com valor >= 0 (ex: moeda estrangeira) ou desconhecido
            entry["tipo"] = "outros"
            investimentos_consolidados.append(entry)

        total_bens += valor

    # Totais vindo do próprio resumo do E1.5 são mais confiáveis
    # (LLM já somou considerando arredondamentos).
    resumo_bens = safe_float(resumo.get("total_ativos", 0))
    resumo_dividas = safe_float(resumo.get("total_passivos", 0))
    if resumo_bens > 0:
        total_bens = resumo_bens
    if resumo_dividas > 0:
        total_dividas = resumo_dividas

    patrimonio_por_ano = {
        ano_str: {
            "total_bens": round(total_bens, 2),
            "total_dividas": round(total_dividas, 2),
        }
    }

    print("  [E1.5c] Consolidado a partir de itens[]:")
    print(f"    Ano ref: {ano_str}")
    print(f"    Imóveis: {len(imoveis_consolidados)}")
    print(f"    Veículos: {len(veiculos_consolidados)}")
    print(f"    Investimentos/Contas: {len(investimentos_consolidados)}")
    print(f"    Dívidas: {len(dividas_consolidadas)}")
    print(f"    Total bens: R$ {total_bens:,.2f}, total dívidas: R$ {total_dividas:,.2f}")

    baseline["imoveis_consolidados"] = imoveis_consolidados
    baseline["veiculos_consolidados"] = veiculos_consolidados
    baseline["investimentos_consolidados"] = investimentos_consolidados
    baseline["dividas"] = dividas_consolidadas
    baseline["patrimonio_por_ano"] = patrimonio_por_ano

    return baseline


def _classify_investimento(grupo: str, descricao: str) -> str:
    """Classify investimento type based on grupo and description."""
    desc_lower = descricao.lower()
    if grupo == "03":
        if "acao" in desc_lower or "acoes" in desc_lower:
            return "acao"
        return "participacao_societaria"
    elif grupo == "04":
        if "cdb" in desc_lower or "rdb" in desc_lower or "renda fixa" in desc_lower:
            return "renda_fixa"
        if "poupanca" in desc_lower:
            return "poupanca"
        return "renda_fixa"
    elif grupo == "06":
        if "moeda estrangeira" in desc_lower or "dolar" in desc_lower or "us " in desc_lower:
            return "moeda_estrangeira"
        return "conta_bancaria"
    elif grupo == "07":
        return "fundo_investimento"
    elif grupo == "99":
        return "outros"
    return "investimento"


def _reconcile_veiculos_against_db(consolidated: dict, *, workspace_id: str) -> None:
    """ADR-239 D3+D4 — degradação graceful sem backend; muta in-place."""
    runner = _try_import_reconciliation_runner()
    if runner is None:
        return
    reconcile_fn, session_factory = runner
    _invoke_reconciliation(reconcile_fn, session_factory, workspace_id, consolidated)


def _apply_informe_pf_merge(consolidated: dict, *, workspace_id: str) -> None:
    """ADR-238 L3 P3 — anexa `informe_pf_saldos_31_12[]` ao baseline; degrada graceful sem backend."""
    runner = _try_import_informe_pf_merger()
    if runner is None:
        return
    merge_fn, session_factory = runner
    _invoke_informe_pf_merge(merge_fn, session_factory, workspace_id, consolidated)


def _try_import_informe_pf_merger():
    """Try-import do adapter informe_pf; None quando indisponível (CLI/tests)."""
    try:
        from backend.app.core.database import SyncSessionLocal
        from backend.app.services.baseline_informe_merger_adapter import (
            merge_baseline_with_informes_pf,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  [info] informe_pf merge skipped (backend unavailable: {exc})")
        return None
    return merge_baseline_with_informes_pf, SyncSessionLocal


def _invoke_informe_pf_merge(merge_fn, session_factory, workspace_id, consolidated):
    """Aplica merger; muta `consolidated` in-place + loga warnings (ADR-238 D5)."""
    try:
        with session_factory() as db:
            result = merge_fn(consolidated, workspace_id=workspace_id, db=db)
            if result.saldos_added == 0:
                return
            consolidated["informe_pf_saldos_31_12"] = result.baseline.get(
                "informe_pf_saldos_31_12", []
            )
            print(
                f"  [OK] Informe PF merge: {result.informes_processed} informes, "
                f"{result.saldos_added} saldos anexados."
            )
            for w in result.warnings:
                print(f"  [E1.5c warn] {w}")
    except Exception as exc:  # noqa: BLE001 — degradação graceful
        print(f"  [warn] informe_pf merge failed: {exc}")


def _try_import_reconciliation_runner():
    """Try-import do runner backend; None quando indisponível (CLI/tests sem DB)."""
    try:
        from backend.app.core.database import SyncSessionLocal
        from backend.app.services.vehicle_reconciliation_runner import (
            reconcile_baseline_with_db,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  [info] vehicle reconciliation skipped (backend unavailable: {exc})")
        return None
    return reconcile_baseline_with_db, SyncSessionLocal


def _invoke_reconciliation(reconcile_fn, session_factory, workspace_id, consolidated):
    """Helper isolado (mantém caller ≤20L; degrada graceful em runtime)."""
    try:
        with session_factory() as db:
            new_baseline, summary = reconcile_fn(workspace_id, consolidated, db=db)
            consolidated["veiculos_consolidados"] = new_baseline.get("veiculos_consolidados", [])
            print(
                f"  [OK] Reconciliação vehicles: {summary.matched_count} matched, "
                f"{summary.needs_review_count} needs_review, "
                f"{summary.no_candidate_count} no_candidate"
            )
    except Exception as exc:  # noqa: BLE001 — degradação graceful
        print(f"  [warn] vehicle reconciliation failed: {exc}")


def main_with_store(ctx) -> dict:
    """E1.5c — consolida baseline patrimonial via ``ArtifactStore``.

    Reutiliza ``consolidate()``. Lê/escreve baseline via ArtifactStore.
    Skip gracioso quando E1.5 não rodou (free tier).

    Args:
        ctx: ``pipeline.context.WorkspaceContext``.

    Returns:
        Dict com ``success``, ``files_created`` e contagens de itens consolidados.
    """
    _init_config(ctx.root)

    store = ctx.get_artifact_store()

    # 1. Carrega baseline — tenta E1.5c (re-run / já consolidado) e depois
    #    E1.5 bruto. Ambos ficam em E2_extracts/ (convenção aceita — ver CLAUDE.md).
    baseline = store.read("E1.5c", "baseline_patrimonial")
    if baseline is None:
        baseline = store.read("E1.5", "baseline_patrimonial")

    if baseline is None:
        return {
            "success": True,
            "skipped": True,
            "reason": "No baseline artifact — E1.5 not run (free tier)",
        }

    print("=" * 60)
    print("  E1.5 Consolidate — Enriquecimento do baseline (Caminho B)")
    print("=" * 60)

    if baseline.get("imoveis_consolidados") and baseline.get("patrimonio_por_ano"):
        print("  [INFO] Baseline já contém chaves consolidadas — serão regeneradas.")

    # ADR-267: constrói MemberNameResolver com CPF se family_members estiver disponível.
    # Permite resolução por CPF em consolidate_from_itens, eliminando duplicação
    # de membro cross-year (Mariana solteira vs casada → mesmo canonical_key via CPF).
    resolver = _build_member_resolver(ctx) if ctx.config_store is not None else None

    # 2. Consolida (reutiliza lógica legada — paridade garantida).
    consolidated = consolidate(baseline, resolver=resolver)

    # 3. Anexa property_id estável aos imóveis (ADR-215 P2). Skip quando
    #    resolver/workspace_id não estão injetados (CLI legado / tests sem DB).
    if ctx.property_identity_resolver is not None and ctx.workspace_id is not None:
        from pipeline.domain.services.property_identity_enricher import (
            enrich_imoveis_with_property_ids,
        )

        # fix-B3: passar family_members permite normalizar titular_key
        # cross-IRPF (LLM extrai aliases distintos para a mesma pessoa).
        family_members = None
        if ctx.config_store is not None:
            try:
                family_members = ctx.config_store.get_family_members(ctx.workspace_id)
            except Exception:
                family_members = None

        enrich_imoveis_with_property_ids(
            consolidated,
            resolver=ctx.property_identity_resolver,
            workspace_id=ctx.workspace_id,
            family_members=family_members,
        )

    # 3b. Dedup de imóveis co-declarados cross-IRPF (ADR-246). Roda após o
    #     enricher para usar `property_id` como chave primária. Helper puro;
    #     no-op quando não há duplicatas.
    from pipeline.domain.services.imoveis_dedup import dedup_imoveis_consolidados

    _titular_key = None
    try:
        if family_members is not None:
            _titular_key = getattr(family_members, "titular_key", None)
    except Exception:
        _titular_key = None
    _dedup = dedup_imoveis_consolidados(
        consolidated.get("imoveis_consolidados", []),
        titular_key=_titular_key,
    )
    consolidated["imoveis_consolidados"] = _dedup.imoveis
    if _dedup.count_after < _dedup.count_before:
        print(
            f"  [E1.5c] Imóveis dedup: {_dedup.count_before} → {_dedup.count_after} "
            f"(warnings={len(_dedup.warnings)})"
        )

    # 4. Reconciliação fuzzy IRPF G02 ↔ vehicles (ADR-239 D3+D4). Degradação
    #    graceful — backend indisponível (CLI/tests) ou workspace_id ausente
    #    pula a etapa silenciosamente (mesma forma de property_id enrichment).
    if ctx.workspace_id is not None:
        _reconcile_veiculos_against_db(consolidated, workspace_id=ctx.workspace_id)

    # 4b. Anexa saldos_31_12 de informes financeiro_pf (ADR-238 L3 P3 D5).
    #     "Informe 31/12 vence extrato D+1" — seção dedicada, downstream consome.
    if ctx.workspace_id is not None:
        _apply_informe_pf_merge(consolidated, workspace_id=ctx.workspace_id)

    # 5. Persiste via store (write-back no artefato E1.5c).
    store.write("E1.5c", "baseline_patrimonial", consolidated)
    print("\n  [OK] Baseline consolidado e salvo via ArtifactStore (stage=E1.5c)")
    print("=" * 60)

    return {
        "success": True,
        "files_created": ["baseline_patrimonial-1.5_consolidated.json"],
        "imoveis": len(consolidated.get("imoveis_consolidados", [])),
        "veiculos": len(consolidated.get("veiculos_consolidados", [])),
        "investimentos": len(consolidated.get("investimentos_consolidados", [])),
        "dividas": len(consolidated.get("dividas", [])),
    }
