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

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# Constants — re-inicializáveis via _init_config()
# ============================================================================
_DEFAULT_BASE_DIR = Path(__file__).resolve().parent.parent


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
    BASELINE_FILE = E2_DIR / _ARTIFACT_NAMES.get("baseline_patrimonial", "baseline_patrimonial-1.5_consolidated.json")
    _FAMILY = _load_json_config(PROJECT_DIR / "config" / "family_members.json")
    _TITULAR = _FAMILY.get("titular", "")
    _MEMBROS = _FAMILY.get("membros", {})
    _MEMBER_KEYS = [k for k in _MEMBROS if not k.startswith("_")]
    _IMOVEL_MATCH_KEYWORDS = _FAMILY.get("imovel_match_keywords", [])


_init_config(_DEFAULT_BASE_DIR)

# IRPF grupo → categoria
GRUPO_MAP = {
    "01": "imovel",
    "02": "veiculo",
    "03": "investimento",   # Participações societárias, ações
    "04": "investimento",   # Aplicações de renda fixa
    "06": "conta_bancaria", # Depósitos, contas, moeda estrangeira
    "07": "investimento",   # Fundos de investimento
    "99": "investimento",   # Outros bens
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
        keywords_nome = set(re.findall(r'\w{4,}', nome))
        keywords_end = set(re.findall(r'\w{4,}', endereco))
        keywords_desc = set(re.findall(r'\w{4,}', desc_lower))

        score += len(keywords_nome & keywords_desc) * 3
        score += len(keywords_end & keywords_desc) * 2

        for kw in _IMOVEL_MATCH_KEYWORDS:
            if kw in desc_lower and (kw in nome or kw in endereco):
                score += 10

        # Cross-match: IRPF building name ↔ XLSX street/nome
        # E.g., building name in IRPF matches street in XLSX if both
        # refer to same apt number
        irpf_apt = re.search(r'apt[o]?\s*(\d+)', desc_lower)
        xlsx_apt = re.search(r'apt[o]?\s*(\d+)', (nome + " " + endereco).lower())
        if irpf_apt and xlsx_apt and irpf_apt.group(1) == xlsx_apt.group(1):
            score += 8

        # Date match: IRPF "ADQUIRIDO EM DD/MM/YYYY" ↔ XLSX data_compra (±7 days)
        xlsx_data = im.get("data_compra", "")
        if xlsx_data:
            irpf_date_m = re.search(r'(\d{2})/(\d{2})/(\d{4})', desc_lower)
            if irpf_date_m:
                try:
                    from datetime import date as _date
                    irpf_d = _date(int(irpf_date_m.group(3)), int(irpf_date_m.group(2)), int(irpf_date_m.group(1)))
                    xlsx_d = _date.fromisoformat(xlsx_data)
                    if abs((irpf_d - xlsx_d).days) <= 7:
                        score += 15  # Strong signal: same acquisition date (±7 days)
                except (ValueError, TypeError):
                    pass

        if score > best_score:
            best_score = score
            best_match = im

    return best_match if best_score >= 3 else None


def consolidate(baseline: dict) -> dict:
    """Add consolidated keys to baseline from declarations + XLSX data."""

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

            dividas_consolidadas.append({
                "descricao": div.get("descricao", ""),
                "proprietario": member_key,
                "saldo_31_12": {
                    ano_str: valor_atual,
                },
            })
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
            print(f"  [INFO] Imóvel XLSX sem match IRPF: {im.get('nome', '?')} (membro={im.get('membro', '?')})")
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
        veiculos_consolidados.append({
            "descricao": f"{v.get('marca', '')} {v.get('modelo', '')} {v.get('ano', '')}".strip(),
            "proprietario": v.get("membro", _TITULAR),
            "tipo": "veiculo",
            "valores_31_12": {
                str(ano_ref): safe_float(v.get("valor_aquisicao", 0)),
            },
            "fonte": "xlsx",
        })

    # =========================================================================
    # 5. Round patrimonio_por_ano
    # =========================================================================
    for ano_str, data in patrimonio_por_ano.items():
        data["total_bens"] = round(data["total_bens"], 2)
        data["total_dividas"] = round(data["total_dividas"], 2)

    # =========================================================================
    # 6. Print summary
    # =========================================================================
    print(f"  [E1.5] Consolidado:")
    print(f"    Imóveis: {len(imoveis_consolidados)}")
    print(f"    Veículos: {len(veiculos_consolidados)}")
    print(f"    Investimentos/Contas: {len(investimentos_consolidados)}")
    print(f"    Dívidas: {len(dividas_consolidadas)}")
    for ano_str, data in sorted(patrimonio_por_ano.items()):
        print(f"    Patrimônio {ano_str}: bens R$ {data['total_bens']:,.2f}, dívidas R$ {data['total_dividas']:,.2f}")

    # =========================================================================
    # 7. Merge into baseline
    # =========================================================================
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


def main(root_dir: Path = None):
    if root_dir:
        _init_config(root_dir)
    parser = argparse.ArgumentParser(
        description="E1.5 Consolidate — Enriquece baseline com chaves consolidadas",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Mostra resultado sem salvar.",
    )
    parser.add_argument(
        "--baseline", type=str, default=str(BASELINE_FILE),
        help=f"Caminho do baseline JSON (default: {BASELINE_FILE})",
    )
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    if not baseline_path.exists():
        print(f"  [ERROR] Baseline não encontrado: {baseline_path}")
        sys.exit(1)

    print("=" * 60)
    print("  E1.5 Consolidate — Enriquecimento do baseline")
    print("=" * 60)

    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    # Check if already consolidated
    if baseline.get("imoveis_consolidados") and baseline.get("patrimonio_por_ano"):
        print("  [INFO] Baseline já contém chaves consolidadas — serão regeneradas.")

    baseline = consolidate(baseline)

    if args.dry_run:
        print("\n  [DRY-RUN] Resultado (não salvo):")
        print(json.dumps(baseline, indent=2, ensure_ascii=False)[:3000])
        print("  ...")
    else:
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False)
        print(f"\n  [OK] Baseline atualizado: {baseline_path}")

    print("=" * 60)


if __name__ == "__main__":
    main()
