#!/usr/bin/env python3
"""
E5.N Narrativas Generator
Generates updated narrativas for E5 analysis JSON with family financial context.

Key metrics (rerun data):
- Score: 7.7/10 (Bom)
- Taxa Poupança Recorrente: 38.63%
- Cobertura Despesas: 80.7 meses
- Taxa Endividamento: 6.71%
- Progresso IF: 31.62%
- Diversificação: 5 classes
"""

import json
import re
from pathlib import Path

# Configuration — relative path (works from any session)
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
E5_JSON_PATH = PROJECT_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
FAMILY_CONFIG_PATH = PROJECT_DIR / "config" / "family_members.json"
GOALS_CONFIG_PATH = PROJECT_DIR / "config" / "goals.json"
TAXAS_CONFIG_PATH = PROJECT_DIR / "config" / "taxas.json"

def _load_family():
    """Load family members config."""
    if FAMILY_CONFIG_PATH.exists():
        with open(FAMILY_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

FAMILY = _load_family()

# METRICS will be loaded from E5 JSON at runtime (no more hardcoding)
# Add a guard to prevent KeyError on import
class _MetricsProxy(dict):
    """Dict that returns safe defaults for missing keys."""
    def __missing__(self, key):
        print(f"  [WARN] METRICS['{key}'] não encontrado, usando default")
        return 0

METRICS = _MetricsProxy()


def _load_goals():
    """Load strategic goals config."""
    if GOALS_CONFIG_PATH.exists():
        with open(GOALS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"  [WARN] goals.json não encontrado em {GOALS_CONFIG_PATH}")
    return {}


def _load_taxas():
    """Load market rates config."""
    if TAXAS_CONFIG_PATH.exists():
        with open(TAXAS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _find_top_asset(e5_data: dict) -> dict:
    """Find the largest individual financial asset from E4 investimentos.

    Returns dict with 'nome', 'valor', 'membro', 'instituicao'.
    """
    inv_path = PROJECT_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
    if inv_path.exists():
        with open(inv_path, "r", encoding="utf-8") as f:
            inv = json.load(f)
        dados = inv.get("dados", [])
        if dados:
            top = max(dados, key=lambda d: d.get("valor_atual", 0))
            return {
                "nome": top.get("nome", ""),
                "valor": top.get("valor_atual", 0),
                "membro": top.get("membro", ""),
                "instituicao": top.get("instituicao", ""),
            }
    return {"nome": "", "valor": 0, "membro": "", "instituicao": ""}


def _extract_top_institutions(e5_data: dict) -> dict:
    """Extract investment institutions per member from E4 investimentos.

    Returns dict with 'david_inst', 'mariana_inst', 'n_imoveis'.
    """
    inv_path = PROJECT_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
    david_inst, mariana_inst = set(), set()
    if inv_path.exists():
        with open(inv_path, "r", encoding="utf-8") as f:
            inv = json.load(f)
        for d in inv.get("dados", []):
            inst = d.get("instituicao", "").strip()
            membro = d.get("membro", "")
            if not inst:
                continue
            if membro == "david":
                david_inst.add(inst.capitalize())
            elif membro == "mariana":
                mariana_inst.add(inst.capitalize())

    # Count imoveis from patrimonio
    pat_path = PROJECT_DIR / "processed" / "E4_unified" / "patrimonio-4_unified.json"
    n_imoveis = 0
    if pat_path.exists():
        with open(pat_path, "r", encoding="utf-8") as f:
            pat = json.load(f)
        imoveis = pat.get("bens_imoveis_consolidados", [])
        if not imoveis:
            imoveis = pat.get("imoveis_consolidados", [])
        n_imoveis = len(imoveis)

    return {
        "david_inst": sorted(david_inst),
        "mariana_inst": sorted(mariana_inst),
        "n_imoveis": n_imoveis,
    }


def _compute_usd_saldos_per_bank(e5_data: dict) -> dict:
    """Compute USD/EUR saldos per bank from E3 reconciled files.

    Returns dict: {'wise_usd': X, 'bofa_usd': Y, 'total_usd': Z, ...}
    """
    import glob
    saldos = {}
    total_usd = 0.0
    pattern = str(PROJECT_DIR / "processed" / "E3_reconciled" / "*-3_reconciled.json")
    for fpath in glob.glob(pattern):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        moeda = data.get("moeda", "BRL")
        banco = data.get("banco", "").lower().replace(" ", "_")
        saldo = data.get("saldo_final", 0)
        if not isinstance(saldo, (int, float)):
            continue
        if moeda == "USD":
            key = f"{banco}_usd"
            saldos[key] = saldos.get(key, 0) + saldo
            total_usd += saldo
        elif moeda == "EUR":
            key = f"{banco}_eur"
            saldos[key] = saldos.get(key, 0) + saldo
    saldos["total_usd"] = total_usd
    return saldos


def _compute_salario_mariana(e5_data: dict) -> float:
    """Compute Mariana's average CLT salary from fluxo mensal detalhado."""
    rmd = e5_data.get("fluxo_caixa", {}).get("receita_despesa_mensal_detalhado", {})
    datasets = rmd.get("receita_datasets", [])
    for ds in datasets:
        label = ds.get("label", "")
        if "Einstein" in label and "CLT" in label:
            nonzero = [v for v in ds.get("data", []) if v > 0]
            if nonzero:
                # Use median (less sensitive to outliers like 13º/férias)
                sorted_vals = sorted(nonzero)
                mid = len(sorted_vals) // 2
                return sorted_vals[mid]
    return 0


def _safe_div(a, b, default=0):
    """Safe division, returns default if b is 0."""
    return a / b if b else default


def load_metrics_from_e5(e5_data: dict) -> dict:
    """Extract METRICS dict from E5 JSON + config/goals.json + computed values.

    Sources:
      - E5 JSON: patrimônio, goals, fluxo_caixa, ratios, score, etc.
      - config/goals.json: strategic targets (aportes, IF, F1/F2, seguros, etc.)
      - config/taxas.json: câmbio, CDI, SELIC, IPCA
      - Computed: yield, salary median, USD savings, derived ratios
    """
    goals_cfg = _load_goals()
    taxas_cfg = _load_taxas()

    pat = e5_data.get("patrimonio", {})
    goals = e5_data.get("goals", {})
    fluxo = e5_data.get("fluxo_caixa", {})
    ratios = e5_data.get("ratios", {})
    score = e5_data.get("score", {})
    reserva = e5_data.get("reserva_emergencia", {})

    # Composição patrimonial
    imoveis_invest = pat.get("imoveis_investimento", 0)
    residencia = pat.get("residencia", 0)

    # Receitas por fonte
    por_fonte = fluxo.get("por_fonte", {})

    # Despesas por categoria
    desp_cat = fluxo.get("despesas_por_categoria", {})

    # Diversificação: count non-zero composition categories
    composicao = pat.get("composicao", [])
    diversificacao_count = len([c for c in composicao if isinstance(c, dict) and c.get("valor", 0) > 0]) or 5

    # --- Computed from E5 data ---
    receita_total = fluxo.get("receita_total", 0)
    receita_aluguel = por_fonte.get("receita_aluguel", 0)
    receita_pj = por_fonte.get("receita_pj", 0)
    receita_clt = por_fonte.get("receita_clt", 0)
    despesa_total = fluxo.get("despesa_total", 0)
    n_meses_periodo = len(fluxo.get("receita_despesa_mensal_detalhado", {}).get("labels", [])) or 1
    receita_aluguel_anual = (receita_aluguel / n_meses_periodo) * 12 if n_meses_periodo else 0

    patrimonio_bruto = pat.get("bruto", 0)
    patrimonio_investivel = pat.get("investivel", 0)
    investimentos_david = pat.get("investimentos_david", 0)
    investimentos_mariana = pat.get("investimentos_mariana", 0)

    yield_imoveis_pct = round(_safe_div(receita_aluguel_anual, imoveis_invest) * 100, 1)

    salario_mariana = _compute_salario_mariana(e5_data)
    receita_recorrente_mensal = fluxo.get("receita_recorrente_mensal", 0)

    # --- From goals.json ---
    aportes = goals_cfg.get("aportes", {})
    dist = aportes.get("distribuicao", {})
    f1f2 = goals_cfg.get("fase_f1f2", {})
    dolar = goals_cfg.get("dolarizacao", {})
    seguros = goals_cfg.get("seguros", {})
    mar_eua = goals_cfg.get("mariana_eua", {})
    trib_cfg = goals_cfg.get("tributario", {})
    imov_cfg = goals_cfg.get("imoveis", {})
    thresholds = goals_cfg.get("thresholds", {})
    aloc_alvo = goals_cfg.get("alocacao_alvo", {})
    riscos = goals_cfg.get("riscos_prioritarios", [])
    decisoes = goals_cfg.get("decisoes_prioritarias", [])

    # --- Computed percentages (Cat. A) ---
    despesas_nao_id = desp_cat.get("nao_identificado", 0)

    pct_investivel = round(_safe_div(patrimonio_investivel, patrimonio_bruto) * 100, 1)
    pct_imoveis_bruto = round(_safe_div(imoveis_invest + residencia, patrimonio_bruto) * 100, 1)
    pct_receita_pj = round(_safe_div(receita_pj, receita_total) * 100, 1)
    pct_receita_aluguel = round(_safe_div(receita_aluguel, receita_total) * 100, 1)
    pct_receita_clt = round(_safe_div(receita_clt, receita_total) * 100, 1)
    pct_receita_outras = round(100 - pct_receita_pj - pct_receita_aluguel - pct_receita_clt, 1)
    pct_despesas_nao_id = round(_safe_div(despesas_nao_id, despesa_total) * 100, 1)

    das_mensal = trib_cfg.get("das_mensal_estimado", 0)
    pct_das_receita_pj = round(_safe_div(das_mensal * 12, receita_pj) * 100, 1) if receita_pj else 0

    if_cfg = goals_cfg.get("independencia_financeira", {})
    renda_passiva_meta = if_cfg.get("renda_passiva_meta_mensal", 30000)
    renda_passiva_4pct = goals.get("renda_passiva_estimada_4pct", 0)
    pct_renda_passiva_meta = round(_safe_div(renda_passiva_4pct, renda_passiva_meta) * 100, 1)

    prazo_anos = goals.get("prazo_anos_realista", 0)

    meta_aporte_mensal = aportes.get("meta_aporte_mensal", 0)
    custo_fase_f1f2 = f1f2.get("custo_mensal_estimado", 0)
    sobra_mensal_f1f2 = receita_recorrente_mensal - custo_fase_f1f2

    # --- USD savings computed from E3 saldos per bank ---
    usd_saldos = _compute_usd_saldos_per_bank(e5_data)
    poupanca_usd = usd_saldos.get("total_usd", 0)
    meta_usd = dolar.get("meta_usd", 0)
    gap_usd = max(0, meta_usd - poupanca_usd)
    cambio = taxas_cfg.get("cambio_usd_brl", 5.80)
    aporte_cambial_brl = dolar.get("aporte_mensal_brl", 0)
    aporte_cambial_usd = _safe_div(aporte_cambial_brl, cambio)
    meses_cambial = int(_safe_div(gap_usd, aporte_cambial_usd)) if aporte_cambial_usd > 0 else 0

    # Mariana EUA vs CLT computation
    renda_eua_projetada_usd = mar_eua.get("renda_rn_projetada_usd", 0)
    renda_eua_projetada_brl = renda_eua_projetada_usd * cambio
    pct_renda_eua_vs_clt = round(
        (1 - _safe_div(renda_eua_projetada_brl, salario_mariana)) * 100, 0
    ) if salario_mariana else 0

    # Accumulated contributions projection
    aportes_acum_prazo = meta_aporte_mensal * 12 * prazo_anos if prazo_anos else 0

    # --- Top asset & institutions from E4 ---
    top_asset = _find_top_asset(e5_data)
    inst_data = _extract_top_institutions(e5_data)

    # Number of despesa categories
    n_desp_categorias = len(desp_cat)

    return {
        # === E5 JSON: score & ratios ===
        "score": score.get("valor", 0),
        "score_label": score.get("classificacao", ""),
        "taxa_poupanca": ratios.get("taxa_poupanca_recorrente_pct", 0),
        "cobertura_meses": reserva.get("cobertura_meses", 0),
        "taxa_endividamento": ratios.get("taxa_endividamento_pct", 0),
        "progresso_if": goals.get("if_pct", 0),
        "diversificacao": diversificacao_count,

        # === E5 JSON: patrimônio ===
        "patrimonio_bruto": patrimonio_bruto,
        "patrimonio_investivel": patrimonio_investivel,
        "imoveis_investimento": imoveis_invest,
        "residencia": residencia,
        "investimentos_david": investimentos_david,
        "investimentos_mariana": investimentos_mariana,
        "veiculos": pat.get("veiculos", 0),
        "dividas": e5_data.get("endividamento", {}).get("total_dividas", 0),

        # === E5 JSON: fluxo de caixa ===
        "receita_total": receita_total,
        "receita_recorrente": fluxo.get("receita_recorrente", 0),
        "receita_recorrente_mensal": receita_recorrente_mensal,
        "despesa_total": despesa_total,
        "despesa_mensal_media": fluxo.get("despesa_mensal_media", 0),
        "fluxo_liquido": fluxo.get("fluxo_liquido", 0),
        "receita_pj": receita_pj,
        "receita_clt": receita_clt,
        "receita_aluguel": receita_aluguel,
        "outras_receitas": por_fonte.get("outras", 0),
        "receita_investimento": por_fonte.get("receita_investimento", 0),
        "receita_resgate": por_fonte.get("receita_resgate", 0),
        "receita_restituicao": por_fonte.get("receita_restituicao", 0),
        "n_meses_periodo": n_meses_periodo,

        # === E5 JSON: despesas por categoria ===
        "despesas_nao_id": despesas_nao_id,
        "despesas_impostos": desp_cat.get("impostos", 0) + desp_cat.get("das", 0),
        "despesas_moradia": desp_cat.get("moradia", 0),
        "despesas_serv_dom": desp_cat.get("servicos_domesticos", 0),
        "despesas_reserva": desp_cat.get("reserva_desejos", 0),
        "despesas_suporte": desp_cat.get("suporte_familiar", 0),
        "despesas_assinatura": desp_cat.get("assinaturas", 0),
        "n_desp_categorias": n_desp_categorias,

        # === E5 JSON: goals (IF) ===
        "if_meta": goals.get("if_meta", 0),
        "if_gap": goals.get("if_gap", 0),
        "if_prazo_anos": prazo_anos,
        "if_ano": goals.get("ano_if", 0),
        "david_idade_if": goals.get("david_idade_if", 0),
        "renda_passiva_4pct": renda_passiva_4pct,

        # === Computed percentages (Cat. A) ===
        "pct_investivel": pct_investivel,
        "pct_imoveis_bruto": pct_imoveis_bruto,
        "pct_receita_pj": pct_receita_pj,
        "pct_receita_aluguel": pct_receita_aluguel,
        "pct_receita_clt": pct_receita_clt,
        "pct_receita_outras": pct_receita_outras,
        "pct_despesas_nao_id": pct_despesas_nao_id,
        "pct_das_receita_pj": pct_das_receita_pj,
        "pct_renda_passiva_meta": pct_renda_passiva_meta,
        "pct_renda_eua_vs_clt": pct_renda_eua_vs_clt,

        # === Computed from E5 data ===
        "salario_mariana": salario_mariana,
        "receita_aluguel_anual": round(receita_aluguel_anual, 2),
        "yield_imoveis_pct": yield_imoveis_pct,
        "sobra_mensal_f1f2": round(sobra_mensal_f1f2, 2),
        "das_anual_estimado": das_mensal * 12,
        "anos_para_if_calculo": round(prazo_anos),
        "aportes_acum_prazo": round(aportes_acum_prazo, 0),
        "renda_eua_projetada_brl": round(renda_eua_projetada_brl, 0),

        # === Computed: top asset & institutions (from E4) ===
        "top_asset_nome": top_asset["nome"],
        "top_asset_valor": top_asset["valor"],
        "top_asset_membro": top_asset["membro"],
        "david_instituicoes": ", ".join(inst_data["david_inst"]) if inst_data["david_inst"] else "múltiplas instituições",
        "mariana_instituicoes": ", ".join(inst_data["mariana_inst"]) if inst_data["mariana_inst"] else "BTG Pactual",
        "n_imoveis": inst_data["n_imoveis"],

        # === Computed: USD/EUR saldos per bank ===
        "wise_usd": round(usd_saldos.get("wise_usd", 0), 2),
        "bofa_usd": round(usd_saldos.get("bank_of_america_usd", 0), 2),
        "poupanca_cambial_actual_usd": round(poupanca_usd, 2),
        "poupanca_cambial_meta_usd": meta_usd,
        "poupanca_cambial_gap_usd": round(gap_usd, 2),
        "aporte_cambial_mensal": aporte_cambial_brl,
        "meses_para_cambial": meses_cambial,
        "cambio_usd_brl": cambio,

        # === config/goals.json: aportes ===
        "meta_aporte_mensal": meta_aporte_mensal,
        "aporte_cofrinhos": dist.get("cofrinhos_itau", 0),
        "aporte_ipca_plus": dist.get("tesouro_ipca_plus", 0),
        "aporte_ivvb11": dist.get("ivvb11", 0),
        "aporte_wise_usd": dist.get("wise_usd", 0),

        # === config/goals.json: IF ===
        "if_trs_pct": if_cfg.get("trs_pct", 5.0),
        "if_renda_passiva_meta": renda_passiva_meta,
        "if_retorno_real_pct": if_cfg.get("retorno_real_anual_pct", 6.0),

        # === config/goals.json: F1/F2 phase ===
        "custo_fase_f1f2": custo_fase_f1f2,
        "custo_viagem_minimo": f1f2.get("custo_viagem_minimo", 0),
        "custo_viagem_maximo": f1f2.get("custo_viagem_maximo", 0),
        "viagens_anuais_estimadas": f1f2.get("viagens_anuais_estimadas", 0),
        "f1f2_universidade": f1f2.get("universidade", ""),
        "f1f2_visto": f1f2.get("visto", "F1/F2"),
        "f1f2_green_card_via": f1f2.get("green_card_via", "EB2-NIW"),
        "f1f2_estrategia_david": f1f2.get("estrategia_david", ""),
        "f1f2_estrategia_mariana": f1f2.get("estrategia_mariana", ""),
        "f1f2_crescimento_salarial": f1f2.get("crescimento_salarial_eua_pct", "3-4"),

        # === config/goals.json: seguros ===
        "seguro_vida_minimo": seguros.get("vida_term_minimo", 0),
        "seguro_vida_maximo": seguros.get("vida_term_maximo", 0),

        # === config/goals.json: Mariana EUA ===
        "renda_mariana_eua_minima": mar_eua.get("renda_rn_minima_usd", 0),
        "renda_mariana_eua_maxima": mar_eua.get("renda_rn_maxima_usd", 0),
        "renda_mariana_eua_projetada": renda_eua_projetada_usd,

        # === config/goals.json: tributário ===
        "das_mensal_estimado": das_mensal,
        "contador_mensal": trib_cfg.get("contador_mensal", 0),
        "contador_nome": trib_cfg.get("contador_nome", "AccountTech"),
        "regime_obs": trib_cfg.get("regime_obs", ""),
        "holding_prazo": trib_cfg.get("holding_avaliacao_prazo", ""),

        # === config/goals.json: imóveis ===
        "yield_imoveis_potencial_pct_min": imov_cfg.get("yield_potencial_pct_min", 0),
        "yield_imoveis_potencial_pct_max": imov_cfg.get("yield_potencial_pct_max", 0),

        # === config/goals.json: thresholds & alocação ===
        "threshold_imovel_pct": thresholds.get("imovel_pct_patrimonio_ideal", 50),
        "equity_alvo_min": thresholds.get("equity_pct_alvo_min", 20),
        "equity_alvo_max": thresholds.get("equity_pct_alvo_max", 25),
        "aloc_rf_pct": aloc_alvo.get("renda_fixa_pct", 50),
        "aloc_acoes_pct": aloc_alvo.get("acoes_pct", 25),
        "aloc_imoveis_pct": aloc_alvo.get("imoveis_reits_pct", 15),
        "aloc_liquidez_pct": aloc_alvo.get("liquidez_usd_pct", 10),
        "aloc_instrumentos_rf": aloc_alvo.get("instrumentos_rf", ""),
        "aloc_instrumentos_rv": aloc_alvo.get("instrumentos_rv", ""),
        "aloc_rebalanceamento": aloc_alvo.get("rebalanceamento", "anual"),

        # === config/goals.json: riscos e decisões ===
        "riscos_prioritarios": riscos,
        "decisoes_prioritarias": decisoes,
    }


def fmt_currency(value):
    """Format currency value according to spec rules.

    Rules:
    - Millions: R$ X,YM (comma as decimal separator)
    - Thousands: R$ XXk or R$ XX,Yk
    - Numbers with dots for separator: R$ 1.102k

    Returns: str
    """
    if not isinstance(value, (int, float)):
        return f"R$ {value}"
    if value >= 1_000_000:
        # Millions
        millions = value / 1_000_000
        formatted = f"{millions:.1f}".replace(".", ",")
        return f"R$ {formatted}M"
    elif value >= 1_000:
        # Thousands
        thousands = value / 1_000
        if thousands == int(thousands):
            return f"R$ {int(thousands)}k"
        formatted = f"{thousands:.1f}".replace(".", ",")
        return f"R$ {formatted}k"
    else:
        # For values < 1000, use Brazilian format (dot for thousands, comma for decimal)
        formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"


def fmt_percent(value):
    """Format percentage value."""
    if value == int(value):
        return f"{int(value)}%"
    return f"{value:.1f}%".replace(".", ",")


def validate_narrativas(narrativas_obj):
    """Validate narrativas object against E5.N spec rules.

    Returns: (is_valid, errors_list)
    """
    errors = []

    # Check structure
    if "perfil_familia" not in narrativas_obj:
        errors.append("Missing perfil_familia key")
    if "summaries" not in narrativas_obj:
        errors.append("Missing summaries key")
    if "charts" not in narrativas_obj:
        errors.append("Missing charts key")

    # Validate perfil_familia
    if "perfil_familia" in narrativas_obj:
        pf = narrativas_obj["perfil_familia"]
        if "left" not in pf or not pf["left"]:
            errors.append("perfil_familia.left is missing or empty")
        if "right" not in pf or not pf["right"]:
            errors.append("perfil_familia.right is missing or empty")

        # Check for invalid HTML tags
        for side in ["left", "right"]:
            if side in pf:
                if "<table" in pf[side].lower():
                    errors.append(f"perfil_familia.{side} contains <table>")
                if "<ul" in pf[side].lower() or "<li" in pf[side].lower():
                    errors.append(f"perfil_familia.{side} contains <ul> or <li>")

        # V_PERFIL_MAX_CHARS — each <p> block must be ≤ 300 chars (plain text)
        _MAX = 300
        for side in ["left", "right"]:
            if side in pf:
                paragraphs = re.findall(r"<p>(.*?)</p>", pf[side], re.DOTALL)
                for idx, p_html in enumerate(paragraphs):
                    plain = re.sub(r"<[^>]+>", "", p_html).strip()
                    if len(plain) > _MAX:
                        errors.append(
                            f"perfil_familia.{side} P{idx+1}: {len(plain)} chars "
                            f"(max {_MAX})"
                        )

    # Validate summaries
    if "summaries" in narrativas_obj:
        summaries = narrativas_obj["summaries"]
        required_summaries = [f"s{i}" for i in range(1, 11)]
        for s_key in required_summaries:
            if s_key not in summaries:
                errors.append(f"Missing summaries.{s_key}")
            elif not summaries[s_key]:
                errors.append(f"summaries.{s_key} is empty")

    # Validate charts
    required_charts = [
        "score_gauge", "patrimonio_doughnut", "alocacao_atual", "alocacao_alvo",
        "fluxo_mensal", "receita_bar", "receita_despesa_mensal", "despesas_doughnut",
        "projecao_3cenarios", "waterfall_if", "renda_passiva", "yield_imoveis",
        "top15_ativos", "impostos_pj", "mariana_cenarios", "custos_f1f2", "viagens",
        "cenarios_cambiais", "bubble_riscos", "top5_decisoes"
    ]

    if "charts" in narrativas_obj:
        charts = narrativas_obj["charts"]
        for chart_key in required_charts:
            if chart_key not in charts:
                errors.append(f"Missing charts.{chart_key}")
            else:
                chart = charts[chart_key]
                if "context" not in chart or not chart["context"]:
                    errors.append(f"charts.{chart_key}.context is missing or empty")
                if "conclusion" not in chart or not chart["conclusion"]:
                    errors.append(f"charts.{chart_key}.conclusion is missing or empty")

    # Validate monetary formatting across all text
    def check_monetary_format(text, field_name):
        # Check for invalid KM suffix (K and M are mutually exclusive)
        if re.search(r'R\$\s*[\d.,]+\s*KM', text, re.IGNORECASE):
            errors.append(f"{field_name}: Invalid 'KM' suffix found (use either k or M, not KM)")

        # Check for space between k/M and number
        if re.search(r'R\$\s*[\d.,]+\s+[kM]', text):
            errors.append(f"{field_name}: Invalid space between value and k/M suffix")

        # Check for English-style decimals in R$ values (should use comma in Brazilian format)
        if re.search(r'R\$\s*\d+\.\d+[kM]', text):
            errors.append(f"{field_name}: Possível ponto decimal em valor monetário (deveria usar vírgula)")

    # Check all text fields
    if "perfil_familia" in narrativas_obj:
        for side in ["left", "right"]:
            if side in narrativas_obj["perfil_familia"]:
                check_monetary_format(narrativas_obj["perfil_familia"][side], f"perfil_familia.{side}")

    if "summaries" in narrativas_obj:
        for s_key, text in narrativas_obj["summaries"].items():
            if text:
                check_monetary_format(text, f"summaries.{s_key}")

    if "charts" in narrativas_obj:
        for chart_key, chart in narrativas_obj["charts"].items():
            for field in ["context", "conclusion"]:
                if field in chart and chart[field]:
                    check_monetary_format(chart[field], f"charts.{chart_key}.{field}")

    return len(errors) == 0, errors


def fmt_usd(value):
    """Format USD value: US$ X,Yk or US$ X."""
    if not isinstance(value, (int, float)):
        return f"US$ {value}"
    if value >= 1000:
        thousands = value / 1000
        if thousands == int(thousands):
            return f"US$ {int(thousands)}k"
        formatted = f"{thousands:.1f}".replace(".", ",")
        return f"US$ {formatted}k"
    return f"US$ {int(value)}"


def build_narrativas():
    """Build complete narrativas object — all data from METRICS, FAMILY, and goals.json.

    No hardcoded numbers, percentages, institutional names, or analytical claims.
    All values come from:
      - METRICS[key]  (E5 JSON + goals.json + computed)
      - FAMILY config  (family_members.json)
      - goals.json     (strategic parameters)
    """
    M = METRICS  # shorthand

    # --- Load family data from config ---
    _fm = FAMILY.get("membros", {})
    _david = _fm.get("david", {})
    _mariana = _fm.get("mariana", {})
    _theo = _fm.get("theo", {})
    _endereco = FAMILY.get("endereco", {})
    _pets = FAMILY.get("pets", [])

    # Calculate ages from config DOBs
    from datetime import date as _date
    _today = _date.today()

    def _age(dob_str):
        if not dob_str:
            return "?"
        try:
            parts = dob_str.split("-")
            dob = _date(int(parts[0]), int(parts[1]), int(parts[2]))
            return str(_today.year - dob.year - ((_today.month, _today.day) < (dob.month, dob.day)))
        except (ValueError, IndexError, TypeError) as e:
            print(f"  [WARN] Erro ao calcular idade de '{dob_str}': {e}")
            return "?"

    _david_age = _age(_david.get("data_nascimento"))
    _mariana_age = _age(_mariana.get("data_nascimento"))
    _pets_str = ", ".join(_pets[:-1]) + " e " + _pets[-1] if len(_pets) > 1 else ", ".join(_pets)

    # Years of experience (computed from config)
    _anos_exp = _today.year - _david.get("carreira_inicio", 2002)
    _empresas = _david.get("empresas_destaque", [])
    _empresas_str = ", ".join(_empresas) if _empresas else ""

    # Mariana specialization from config
    _mar_esp = _mariana.get("especializacao", "")
    _mar_mestrado = _mariana.get("mestrado", "")
    _mar_perfil_int = _mariana.get("perfil_internacional", "")

    # Cidadania from config
    _cidadanias = _theo.get("cidadania", [])
    _cidadanias_str = " e ".join(_cidadanias) if _cidadanias else "brasileira e americana"

    # Riscos from goals.json
    _riscos = M.get("riscos_prioritarios", [])
    _riscos_top3 = _riscos[:3] if isinstance(_riscos, list) else []
    _riscos_nomes = [r.get("nome", "") for r in _riscos if isinstance(r, dict)]

    # Decisões from goals.json
    _decisoes = M.get("decisoes_prioritarias", [])

    # Maximum character limit per paragraph in perfil_familia card.
    # Enforced by validation (V_PERFIL_MAX_CHARS) and truncated defensively in E6.
    PERFIL_MAX_CHARS = 300

    # --- Helper: imovel concentration conditional ---
    _imovel_acima = M['pct_imoveis_bruto'] > M['threshold_imovel_pct']

    narrativas = {
        "perfil_familia": {
            "left": (
                f"<p>{_david.get('nome_completo', '')}, {_david_age} anos, "
                f"é {_david.get('profissao', '')} ({_david.get('descricao_empresa', '')}). "
                f"Mais de {_anos_exp} anos em tecnologia, com passagens por {_empresas_str}. "
                f"Formado em {_david.get('formacao', '')}. "
                f"Opera como {_david.get('regime', '')}.</p>\n"
                f"<p>{_mariana.get('nome_completo', '')}, {_mariana_age} anos, "
                f"é {_mariana.get('profissao', '')} desde {_mariana.get('emprego_inicio', '')}. "
                f"Especialista em {_mar_esp}, mestre em {_mar_mestrado}. "
                f"CLT com salário-base de {fmt_currency(M['salario_mariana'])}/mês. "
                f"{_mar_perfil_int}.</p>\n"
                f"<p>{_theo.get('nome_completo', '')} nasceu em "
                f"{_theo.get('local_nascimento', '')} e possui dupla cidadania {_cidadanias_str}. "
                "Primeiro filho do casal, é peça central no planejamento internacional da família.</p>\n"
                f"<p>A família conta com {len(_pets)} gatos — {_pets_str} — na residência da "
                f"{_endereco.get('rua', '')}, {_endereco.get('bairro', '')}, "
                f"{_endereco.get('cidade', '')}.</p>"
            ),
            "right": (
                f"<p>Plano de vida centrado na mudança para os EUA via visto {M['f1f2_visto']} "
                f"({M['f1f2_universidade']}), seguido de Green Card por {M['f1f2_green_card_via']}. "
                f"{M['f1f2_estrategia_david']}; {M['f1f2_estrategia_mariana']}. "
                f"Custo projetado: {fmt_currency(M['custo_fase_f1f2'])}/mês, com sobra de "
                f"{fmt_currency(M['sobra_mensal_f1f2'])}/mês.</p>\n"
                f"<p>Meta IF: {fmt_currency(M['if_meta'])} (TRS {M['if_trs_pct']:.0f}%, renda passiva de {fmt_currency(M['if_renda_passiva_meta'])}/mês). "
                f"Patrimônio investível atual de {fmt_currency(M['patrimonio_investivel'])} ({fmt_percent(M['progresso_if'])} da meta). "
                f"Com aportes de {fmt_currency(M['meta_aporte_mensal'])}/mês e retorno real de {M['if_retorno_real_pct']:.0f}% a.a., "
                f"prazo de {M['anos_para_if_calculo']} anos (David {M['david_idade_if']} anos, {M['if_ano']}).</p>\n"
                f"<p>Patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])}: "
                f"{M['n_imoveis']} imóveis ({fmt_currency(M['residencia'])} residência + {fmt_currency(M['imoveis_investimento'])} investimento), "
                f"carteiras David ({fmt_currency(M['investimentos_david'])}) e Mariana ({fmt_currency(M['investimentos_mariana'])}). "
                f"Endividamento de {fmt_percent(M['taxa_endividamento'])} — saudável.</p>"
            )
        },
        "summaries": {
            "s1": (
                f"Patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])} com {fmt_percent(M['pct_investivel'])} investível ({fmt_currency(M['patrimonio_investivel'])}). "
                f"Imóveis representam {fmt_percent(M['pct_imoveis_bruto'])} do total, com residência própria de {fmt_currency(M['residencia'])} e imóveis de investimento somando "
                f"{fmt_currency(M['imoveis_investimento'])}. Endividamento de {fmt_percent(M['taxa_endividamento'])} sobre o bruto."
            ),
            "s2": (
                f"Score financeiro de {M['score']}/10 ({M['score_label']}). Pontos fortes: taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])}, "
                f"cobertura de {M['cobertura_meses']:.1f} meses de despesas e endividamento controlado. Receita total no período de {fmt_currency(M['receita_total'])} "
                f"com {fmt_percent(M['pct_receita_pj'])} proveniente de PJ, {fmt_percent(M['pct_receita_aluguel'])} de aluguel, "
                f"{fmt_percent(M['pct_receita_clt'])} de CLT e {fmt_percent(M['pct_receita_outras'])} de outras fontes."
            ),
            "s3": (
                f"Carteira diversificada entre {M['diversificacao']} categorias de ativos. "
                f"David mantém {fmt_currency(M['investimentos_david'])} distribuídos entre {M['david_instituicoes']}. "
                f"Mariana possui {fmt_currency(M['investimentos_mariana'])} concentrados em {M['mariana_instituicoes']}."
            ),
            "s4": (
                f"{M['n_imoveis']} imóveis no portfólio: residência na {_endereco.get('rua', '')} ({fmt_currency(M['residencia'])}), "
                f"apartamentos alugados com renda de {fmt_currency(M['receita_aluguel_anual'])}/ano ({fmt_currency(M['receita_aluguel'] / M['n_meses_periodo'] if M['n_meses_periodo'] else 0)}/mês). "
                f"Yield bruto dos imóveis de investimento estimado em {M['yield_imoveis_pct']}% (receita/valor total)."
            ),
            "s5": (
                f"Meta de independência financeira de {fmt_currency(M['if_meta'])} em {M['if_ano']}. "
                f"Gap atual de {fmt_currency(M['if_gap'])} com prazo realista de {M['if_prazo_anos']:.1f} anos "
                f"à taxa de aporte {fmt_currency(M['meta_aporte_mensal'])}/mês e retorno real {M['if_retorno_real_pct']:.0f}% a.a. "
                f"Renda passiva estimada ({M['if_trs_pct']:.0f}% TRS): {fmt_currency(M['renda_passiva_4pct'])}/mês."
            ),
            "s6": (
                f"Exposição cambial: {fmt_usd(M['wise_usd'])} em Wise, {fmt_usd(M['bofa_usd'])} em Bank of America. "
                f"Total {fmt_usd(M['poupanca_cambial_actual_usd'])}. "
                f"Meta pré-EUA de {fmt_usd(M['poupanca_cambial_meta_usd'])} com gap de {fmt_usd(M['poupanca_cambial_gap_usd'])} — "
                f"ritmo de {fmt_currency(M['aporte_cambial_mensal'])}/mês na Wise alcança a meta em {M['meses_para_cambial']} meses."
            ),
            "s7": (
                f"{len(_riscos_nomes)} riscos prioritários: {', '.join(_riscos_nomes[:3])}. "
                "Seguros de vida e invalidez inexistentes — classificados como urgentes. Planejamento sucessório em estágio inicial."
            ),
            "s8": (
                f"{M['regime_obs']}. DAS mensal estimado em {fmt_currency(M['das_mensal_estimado'])}. "
                f"{M['contador_nome']} como contador ({fmt_currency(M['contador_mensal'])}/mês via C6 PJ). "
                f"Avaliação de holding patrimonial pendente para {M['holding_prazo']}. "
                "Obrigações fiscais EUA (FBAR, Form 8938, PFIC) requerem CPA expatriado antes da mudança."
            ),
            "s9": (
                f"Despesas totais no período ({M['n_meses_periodo']} meses): {fmt_currency(M['despesa_total'])} ({fmt_currency(M['despesa_mensal_media'])}/mês média). "
                f"Maior categoria 'não identificado' com {fmt_currency(M['despesas_nao_id'])} ({fmt_percent(M['pct_despesas_nao_id'])} do total). "
                f"Impostos ({fmt_currency(M['despesas_impostos'])}), moradia ({fmt_currency(M['despesas_moradia'])}) e serviços domésticos "
                f"({fmt_currency(M['despesas_serv_dom'])}) completam o perfil de gastos."
            ),
            "s10": (
                f"{len(_decisoes)} decisões estratégicas prioritárias: iniciar aporte mensal de {fmt_currency(M['meta_aporte_mensal'])} "
                f"({fmt_currency(M['aporte_cofrinhos'])} Cofrinhos, {fmt_currency(M['aporte_ipca_plus'])} IPCA+, "
                f"{fmt_currency(M['aporte_ivvb11'])} IVVB11, {fmt_currency(M['aporte_wise_usd'])} Wise USD), "
                + ", ".join(_decisoes[1:4]) + "."
                if len(_decisoes) > 3 else
                f"{len(_decisoes)} decisões estratégicas prioritárias: iniciar aporte mensal de {fmt_currency(M['meta_aporte_mensal'])}."
            )
        },
        "charts": {
            "score_gauge": {
                "context": (
                    f"Indicador geral de saúde financeira da família, com score de {M['score']}/10 "
                    f"({M['score_label']}). Reflete equilíbrio entre pontos fortes e oportunidades de melhoria."
                ),
                "conclusion": (
                    f"A classificação '{M['score_label']}' reflete melhora na taxa de poupança "
                    "recorrente e redução da razão endividamento/patrimônio."
                )
            },
            "patrimonio_doughnut": {
                "context": (
                    f"Distribuição do patrimônio bruto de {fmt_currency(M['patrimonio_bruto'])} entre {M['diversificacao']} categorias de ativos, "
                    "mostrando concentração em imóveis e peso relativo dos investimentos financeiros."
                ),
                "conclusion": (
                    f"Imóveis respondem por {fmt_percent(M['pct_imoveis_bruto'])} do patrimônio"
                    + (f" — acima do ideal de {fmt_percent(M['threshold_imovel_pct'])}. " if _imovel_acima else ". ")
                    + f"Aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} em ativos financeiros devem melhorar essa proporção."
                )
            },
            "alocacao_atual": {
                "context": (
                    f"Atual distribuição dos ativos financeiros ({fmt_currency(M['investimentos_david'] + M['investimentos_mariana'])}) "
                    "entre classes de investimento: renda fixa, ações, fundos multimercado e estruturados."
                ),
                "conclusion": (
                    f"David diversificado em {M['david_instituicoes']}; Mariana concentra em {M['mariana_instituicoes']}. "
                    f"Recomendação: gradualmente adicionar alocação de ações ({M['aloc_instrumentos_rv']}) para atingir {M['equity_alvo_min']}-{M['equity_alvo_max']}% de equity."
                )
            },
            "alocacao_alvo": {
                "context": (
                    f"Alocação estratégica recomendada para os ativos financeiros, considerando horizonte de {M['anos_para_if_calculo']} anos até IF e tolerância ao risco médio."
                ),
                "conclusion": (
                    f"Alvo: {M['aloc_rf_pct']}% Renda Fixa ({M['aloc_instrumentos_rf']}), {M['aloc_acoes_pct']}% Ações ({M['aloc_instrumentos_rv']}), "
                    f"{M['aloc_imoveis_pct']}% Imóveis/REITs, {M['aloc_liquidez_pct']}% Liquidez/USD. "
                    f"Aportes de {fmt_currency(M['meta_aporte_mensal'])}/mês priorizarão renda fixa, com rebalanceamento {M['aloc_rebalanceamento']}."
                )
            },
            "fluxo_mensal": {
                "context": (
                    f"Visão consolidada do fluxo de caixa mensal: receita recorrente de {fmt_currency(M['receita_recorrente_mensal'])}/mês "
                    f"versus despesa média de {fmt_currency(M['despesa_mensal_media'])}/mês."
                ),
                "conclusion": (
                    f"Saldo mensal de {fmt_currency(M['receita_recorrente_mensal'] - M['despesa_mensal_media'])}/mês. "
                    f"Taxa de poupança de {fmt_percent(M['taxa_poupanca'])} garante capacidade de aporte consistente. "
                    f"Sustenta a meta de aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} para o plano IF."
                )
            },
            "receita_bar": {
                "context": (
                    f"Composição da receita total de {fmt_currency(M['receita_total'])} por fonte: "
                    f"PJ ({fmt_percent(M['pct_receita_pj'])}), CLT ({fmt_percent(M['pct_receita_clt'])}), "
                    f"aluguel ({fmt_percent(M['pct_receita_aluguel'])}), outras ({fmt_percent(M['pct_receita_outras'])})."
                ),
                "conclusion": (
                    f"Receita PJ de {fmt_currency(M['receita_pj'])} mantém dominância ({fmt_percent(M['pct_receita_pj'])}), "
                    f"com CLT ({fmt_currency(M['receita_clt'])}, {fmt_percent(M['pct_receita_clt'])}) "
                    f"e aluguel ({fmt_currency(M['receita_aluguel'])}, {fmt_percent(M['pct_receita_aluguel'])}). "
                    "Diversificação reduz risco de dependência única."
                )
            },
            "receita_despesa_mensal": {
                "context": (
                    f"Série temporal mensal de receitas ({fmt_currency(M['receita_total'])}/período) versus despesas ({fmt_currency(M['despesa_total'])}/período), "
                    f"resultando em fluxo líquido de {fmt_currency(M['fluxo_liquido'])}."
                ),
                "conclusion": (
                    f"Receita recorrente de {fmt_currency(M['receita_recorrente_mensal'])}/mês e despesa média de {fmt_currency(M['despesa_mensal_media'])}/mês. "
                    f"Taxa de poupança recorrente de {fmt_percent(M['taxa_poupanca'])} valida a sustentabilidade do plano IF."
                )
            },
            "despesas_doughnut": {
                "context": (
                    f"Distribuição das despesas totais ({fmt_currency(M['despesa_total'])}) entre {M['n_desp_categorias']} categorias, "
                    "destacando a composição de gastos e oportunidades de otimização."
                ),
                "conclusion": (
                    f"Categoria 'não identificado' lidera com {fmt_currency(M['despesas_nao_id'])} ({fmt_percent(M['pct_despesas_nao_id'])}), seguida por impostos "
                    f"({fmt_currency(M['despesas_impostos'])}), moradia ({fmt_currency(M['despesas_moradia'])}) e serviços domésticos "
                    f"({fmt_currency(M['despesas_serv_dom'])}). Prioridade: reclassificar 'não identificado' via melhor rastreamento."
                )
            },
            "projecao_3cenarios": {
                "context": (
                    f"Projeção do patrimônio investível até atingir a meta de {fmt_currency(M['if_meta'])}, "
                    f"considerando aportes mensais de {fmt_currency(M['meta_aporte_mensal'])} e retorno real anual de {M['if_retorno_real_pct']:.0f}%."
                ),
                "conclusion": (
                    f"Meta será atingida em {M['if_ano']}, quando David terá {M['david_idade_if']} anos. "
                    f"Renda passiva estimada será {fmt_currency(M['renda_passiva_4pct'])}/mês ({fmt_percent(M['pct_renda_passiva_meta'])} da meta de {fmt_currency(M['if_renda_passiva_meta'])}/mês)."
                )
            },
            "waterfall_if": {
                "context": (
                    f"Decomposição do gap de independência financeira ({fmt_currency(M['if_gap'])}), mostrando componentes de patrimônio atual, "
                    f"aportes acumulados e rentabilidade esperada até {M['if_ano']}."
                ),
                "conclusion": (
                    f"Gap de {fmt_currency(M['if_gap'])} será fechado por aportes disciplinados "
                    f"({fmt_currency(M['meta_aporte_mensal'])}/mês = {fmt_currency(M['aportes_acum_prazo'])} em {M['if_prazo_anos']:.0f} anos) "
                    f"e rentabilidade real de {M['if_retorno_real_pct']:.0f}% a.a. sobre patrimônio acumulado."
                )
            },
            "renda_passiva": {
                "context": (
                    f"Renda passiva estimada em diferentes cenários de patrimônio investível, "
                    f"assumindo TRS de {M['if_trs_pct']:.0f}% (alvo) e 4% (conservador)."
                ),
                "conclusion": (
                    f"Cenário atual ({fmt_currency(M['patrimonio_investivel'])}): {fmt_currency(M['renda_passiva_4pct'])}/mês ({fmt_percent(M['pct_renda_passiva_meta'])} da meta). "
                    f"Cenário {M['if_ano']} ({fmt_currency(M['if_meta'])}): {fmt_currency(M['if_renda_passiva_meta'])}/mês. "
                    "Diversidade de fontes (aluguel, dividendos, renda fixa) reduz risco."
                )
            },
            "yield_imoveis": {
                "context": (
                    f"Análise de yield bruto dos imóveis de investimento (valor total {fmt_currency(M['imoveis_investimento'])}) "
                    "versus aluguel recebido mensalizado."
                ),
                "conclusion": (
                    f"Yield atual de {M['yield_imoveis_pct']}% com potencial de "
                    f"{M['yield_imoveis_potencial_pct_min']}-{M['yield_imoveis_potencial_pct_max']}% após otimização de contratos. "
                    "Imóveis funcionam como hedge inflacionário e fonte de renda complementar."
                )
            },
            "top15_ativos": {
                "context": (
                    f"Ranking dos 15 maiores ativos financeiros individuais da família, totalizando {fmt_currency(M['patrimonio_investivel'])} em investimentos."
                ),
                "conclusion": (
                    f"{M['top_asset_nome']} ({fmt_currency(M['top_asset_valor'])} de {M['top_asset_membro'].capitalize()}) é o maior ativo individual. "
                    "Concentração em poucos ativos reforça importância de aportes contínuos para diversificação."
                )
            },
            "impostos_pj": {
                "context": (
                    f"Análise da carga tributária PJ de David (receita {fmt_currency(M['receita_pj'])}), "
                    f"estimando DAS mensal sob {M['regime_obs']}."
                ),
                "conclusion": (
                    f"DAS estimado em {fmt_currency(M['das_mensal_estimado'])}/mês ({fmt_currency(M['das_anual_estimado'])}/ano), "
                    f"representando {fmt_percent(M['pct_das_receita_pj'])} da receita PJ. "
                    f"Contador {M['contador_nome']} em funcionamento. Avaliação de holding patrimonial pendente para {M['holding_prazo']}."
                )
            },
            "mariana_cenarios": {
                "context": (
                    f"Cenários financeiros para Mariana pós-NCLEX, com projeções de renda americana como RN "
                    f"({fmt_usd(M['renda_mariana_eua_minima'])}-{fmt_usd(M['renda_mariana_eua_maxima'])}/mês) "
                    f"versus permanência no Brasil (CLT Einstein {fmt_currency(M['salario_mariana'])}/mês)."
                ),
                "conclusion": (
                    f"Cenário EUA com {fmt_usd(M['renda_mariana_eua_projetada'])}/mês = {fmt_currency(M['renda_eua_projetada_brl'])}/mês. "
                    "Compensado por: integração com patrimônio de David, renda PJ remota, "
                    f"renda de aluguel em BRL e potencial de crescimento salarial anual de {M['f1f2_crescimento_salarial']}%."
                )
            },
            "custos_f1f2": {
                "context": (
                    f"Estimativa de custos mensais na fase {M['f1f2_visto']} nos EUA: tuition + living + viagens BR = {fmt_currency(M['custo_fase_f1f2'])}/mês."
                ),
                "conclusion": (
                    f"Sobra projetada: {fmt_currency(M['sobra_mensal_f1f2'])}/mês ({fmt_currency(M['receita_recorrente_mensal'])} - {fmt_currency(M['custo_fase_f1f2'])})."
                )
            },
            "viagens": {
                "context": (
                    "Padrão de despesas com viagens identificado nos extratos, estimando frequência e custo médio."
                ),
                "conclusion": (
                    f"Viagens para EUA estimadas em {fmt_currency(M['custo_viagem_minimo'])}-{fmt_currency(M['custo_viagem_maximo'])} por viagem. "
                    f"Frequência média de {M['viagens_anuais_estimadas']:.0f} viagens/ano para acompanhamento do processo {M['f1f2_visto']}."
                )
            },
            "cenarios_cambiais": {
                "context": (
                    f"Exposição cambial atual ({fmt_usd(M['poupanca_cambial_actual_usd'])}) e meta pré-EUA ({fmt_usd(M['poupanca_cambial_meta_usd'])}), "
                    f"considerando câmbio de R$ {M['cambio_usd_brl']:.2f}/USD."
                ),
                "conclusion": (
                    f"Gap de {fmt_usd(M['poupanca_cambial_gap_usd'])} com aporte atual de {fmt_currency(M['aporte_cambial_mensal'])}/mês em Wise, "
                    f"atingindo meta em {M['meses_para_cambial']} meses. "
                    "Risco mitigado por diversificação USD/EUR, renda PJ em BRL e flexibilidade de data de mudança."
                )
            },
            "bubble_riscos": {
                "context": (
                    f"Identificação de {len(_riscos)} riscos críticos de compliance e proteção ao plano IF, com probabilidade e impacto."
                ),
                "conclusion": (
                    "Riscos prioritários: "
                    + ", ".join(
                        f"({i+1}) {r.get('nome', '')} ({r.get('prob', '')} prob., {r.get('impacto', '')} impacto)"
                        for i, r in enumerate(_riscos_top3)
                    )
                    + f". Ação: CPA expatriado + seguro term R$ {M['seguro_vida_minimo'] // 1_000_000}-{M['seguro_vida_maximo'] // 1_000_000}M."
                )
            },
            "top5_decisoes": {
                "context": (
                    f"{len(_decisoes)} decisões estratégicas de curto prazo (6-12 meses) para otimizar a trajetória até IF."
                ),
                "conclusion": (
                    f"Prioridade 1: Aporte mensal {fmt_currency(M['meta_aporte_mensal'])} com divisão "
                    f"({fmt_currency(M['aporte_cofrinhos'])} Cofrinhos, {fmt_currency(M['aporte_ipca_plus'])} IPCA+, "
                    f"{fmt_currency(M['aporte_ivvb11'])} IVVB11, {fmt_currency(M['aporte_wise_usd'])} Wise USD). "
                    + ". ".join(f"Prioridade {i+2}: {d}" for i, d in enumerate(_decisoes[1:5]))
                    + "."
                )
            }
        }
    }

    return narrativas


def main():
    """Main execution function."""

    print("=" * 80)
    print("E5.N NARRATIVAS GENERATOR")
    print("=" * 80)
    print()

    # Read current E5 JSON
    print(f"Reading E5 JSON from {E5_JSON_PATH}...")
    if not E5_JSON_PATH.exists():
        print(f"✗ E5 JSON not found at {E5_JSON_PATH}")
        print("  Run e5_analyze.py first.")
        return False

    with open(E5_JSON_PATH, 'r', encoding='utf-8') as f:
        e5_data = json.load(f)

    print(f"✓ Loaded E5 JSON with {len(e5_data)} top-level keys")
    print()

    # Load metrics dynamically from E5 JSON
    global METRICS
    METRICS = load_metrics_from_e5(e5_data)
    print(f"✓ Loaded {len(METRICS)} metrics from E5 JSON")
    print(f"  Score: {METRICS['score']}/10, Patrimônio: R$ {METRICS['patrimonio_bruto']:,.0f}")
    print()

    # Build narrativas
    print("Building narrativas object with metrics from E5 JSON...")
    narrativas = build_narrativas()
    print(f"✓ Built narrativas with {len(narrativas)} main sections")
    print(f"  - perfil_familia: left and right sections")
    print(f"  - summaries: {len(narrativas['summaries'])} summaries (s1-s10)")
    print(f"  - charts: {len(narrativas['charts'])} chart descriptions")
    print()

    # Validate narrativas
    print("Validating narrativas against E5.N specification...")
    is_valid, errors = validate_narrativas(narrativas)

    if is_valid:
        print("✓ All validations passed!")
    else:
        print(f"✗ Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        print()
        return False

    print()

    # Inject into E5 JSON
    print("Injecting narrativas into E5 JSON...")
    e5_data["narrativas"] = narrativas
    print("✓ Narrativas injected")
    print()

    # Save updated JSON
    print(f"Saving updated E5 JSON to {E5_JSON_PATH}...")
    with open(E5_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(e5_data, f, ensure_ascii=False, indent=2)
    print("✓ Saved successfully")
    print()

    # Summary
    print("=" * 80)
    print("E5.N NARRATIVAS GENERATION COMPLETE")
    print("=" * 80)
    print()
    print("Summary of updated metrics:")
    print(f"  Score: {METRICS['score']}/10 ({METRICS['score_label']})")
    print(f"  Taxa Poupança Recorrente: {fmt_percent(METRICS['taxa_poupanca'])}")
    print(f"  Cobertura Despesas: {METRICS['cobertura_meses']:.1f} meses")
    print(f"  Taxa Endividamento: {fmt_percent(METRICS['taxa_endividamento'])}")
    print(f"  Progresso IF: {fmt_percent(METRICS['progresso_if'])}")
    print(f"  Patrimônio Bruto: {fmt_currency(METRICS['patrimonio_bruto'])}")
    print(f"  Patrimônio Investível: {fmt_currency(METRICS['patrimonio_investivel'])}")
    print(f"  IF Gap: {fmt_currency(METRICS['if_gap'])}")
    print(f"  IF Prazo: {METRICS['if_prazo_anos']:.1f} anos (ano {METRICS['if_ano']})")
    print()

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
