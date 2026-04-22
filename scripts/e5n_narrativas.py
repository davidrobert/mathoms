#!/usr/bin/env python3
"""
E5.N Narrativas Generator
Generates updated narrativas for E5 analysis JSON with family financial context.
Metrics are loaded dynamically from E5 JSON at runtime.
"""

import json
import re
from pathlib import Path

import scripts.pipeline_common as _pc

# Configuration — paths e config re-inicializáveis via _init_config()
_DEFAULT_BASE_DIR = _pc._REPO_ROOT


def _load_json_safe(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _init_config(base_dir: Path) -> None:
    """(Re-)inicializa paths e config globals a partir de base_dir."""
    global SCRIPTS_DIR, PROJECT_DIR
    global E5_JSON_PATH, FAMILY_CONFIG_PATH, GOALS_CONFIG_PATH
    global TAXAS_CONFIG_PATH, CATEGORIZATION_CONFIG_PATH, FISCAL_CONFIG_PATH
    global FAMILY, _CATEGORIZATION
    global _TITULAR_KEY, _MEMBROS, _CONJUGE_KEY, _TITULAR_NOME, _CONJUGE_NOME
    global _KEY_INV_TITULAR, _KEY_INV_CONJUGE, _KEY_CENARIOS_CONJUGE
    global _KEY_IDADE_TITULAR_IF, _KEY_SAL_CONJUGE
    global _KEY_INST_TITULAR, _KEY_INST_CONJUGE
    global _KEY_F1F2_TITULAR, _KEY_F1F2_CONJUGE
    global _KEY_RENDA_CONJUGE_EUA_PROJ, _KEY_CENARIOS_SECTION

    SCRIPTS_DIR = base_dir / "scripts"
    PROJECT_DIR = base_dir
    E5_JSON_PATH = PROJECT_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    FAMILY_CONFIG_PATH = PROJECT_DIR / "config" / "family_members.json"
    GOALS_CONFIG_PATH = PROJECT_DIR / "config" / "goals.json"
    TAXAS_CONFIG_PATH = PROJECT_DIR / "config" / "taxas.json"
    CATEGORIZATION_CONFIG_PATH = PROJECT_DIR / "config" / "categorization.json"
    FISCAL_CONFIG_PATH = PROJECT_DIR / "config" / "parametros_fiscais.json"

    FAMILY = _load_json_safe(FAMILY_CONFIG_PATH)
    _CATEGORIZATION = _load_json_safe(CATEGORIZATION_CONFIG_PATH)

    _TITULAR_KEY = FAMILY.get("titular", "")
    _MEMBROS = FAMILY.get("membros", {})
    _CONJUGE_KEY = next(
        (k for k, v in _MEMBROS.items() if isinstance(v, dict) and v.get("papel") == "conjuge"), ""
    )
    _TITULAR_NOME = _MEMBROS.get(_TITULAR_KEY, {}).get("nome_curto", _TITULAR_KEY.title())
    _CONJUGE_NOME = _MEMBROS.get(_CONJUGE_KEY, {}).get("nome_curto", _CONJUGE_KEY.title())

    _KEY_INV_TITULAR = f"investimentos_{_TITULAR_KEY}"
    _KEY_INV_CONJUGE = f"investimentos_{_CONJUGE_KEY}"
    _KEY_CENARIOS_CONJUGE = f"cenarios_{_CONJUGE_KEY}"
    _KEY_IDADE_TITULAR_IF = f"idade_{_TITULAR_KEY}_if"
    _KEY_SAL_CONJUGE = f"salario_{_CONJUGE_KEY}"
    _KEY_INST_TITULAR = f"{_TITULAR_KEY}_instituicoes"
    _KEY_INST_CONJUGE = f"{_CONJUGE_KEY}_instituicoes"
    _KEY_F1F2_TITULAR = f"f1f2_estrategia_{_TITULAR_KEY}"
    _KEY_F1F2_CONJUGE = f"f1f2_estrategia_{_CONJUGE_KEY}"
    _KEY_RENDA_CONJUGE_EUA_PROJ = f"renda_{_CONJUGE_KEY}_eua_projetada"
    _KEY_CENARIOS_SECTION = f"{_CONJUGE_KEY}_cenarios"


_init_config(_pc.PROJECT_DIR)


def _load_fiscal():
    """Load fiscal parameters config (parametros_fiscais.json)."""
    if FISCAL_CONFIG_PATH.exists():
        with open(FISCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"  [WARN] parametros_fiscais.json não encontrado em {FISCAL_CONFIG_PATH}")
    return {}


FISCAL = _load_fiscal()
_CLT_SOURCE_LABELS = list(_CATEGORIZATION.get("clt_source_mapping", {}).values())


# METRICS will be loaded from E5 JSON at runtime (no more hardcoding)
# Add a guard to prevent KeyError on import
class _MetricsProxy(dict):
    """Dict that returns None for missing keys (distinguishes from 0)."""

    def __missing__(self, key):
        print(f"  [WARN] METRICS['{key}'] não encontrado, retornando None")
        return None


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
    Falls back to 'tipo (instituicao)' when nome is empty.
    """
    inv_path = PROJECT_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
    if inv_path.exists():
        with open(inv_path, "r", encoding="utf-8") as f:
            inv = json.load(f)
        dados = inv.get("dados", [])
        if dados:
            top = max(dados, key=lambda d: d.get("valor_atual", 0))
            nome = top.get("nome", "").strip()
            if not nome:
                tipo = top.get("tipo", "Investimento")
                inst = top.get("instituicao", "").capitalize()
                nome = f"{tipo} ({inst})" if inst else tipo
            return {
                "nome": nome,
                "valor": top.get("valor_atual", 0),
                "membro": top.get("membro", ""),
                "instituicao": top.get("instituicao", ""),
            }
    return {"nome": "", "valor": 0, "membro": "", "instituicao": ""}


def _extract_top_institutions(e5_data: dict) -> dict:
    """Extract investment institutions per member from E4 investimentos.

    Returns dict with '{member}_inst' for each member, plus 'n_imoveis'.
    Member keys are loaded from family_members.json config.
    """
    _titular = FAMILY.get("titular", "")
    _membros = FAMILY.get("membros", {})
    _conjuge = next((k for k, v in _membros.items() if v.get("papel") == "conjuge"), None)

    inv_path = PROJECT_DIR / "processed" / "E4_unified" / "investimentos-4_unified.json"
    titular_inst, conjuge_inst = set(), set()
    if inv_path.exists():
        with open(inv_path, "r", encoding="utf-8") as f:
            inv = json.load(f)
        for d in inv.get("dados", []):
            inst = d.get("instituicao", "").strip()
            membro = d.get("membro", "")
            if not inst:
                continue
            if membro == _titular:
                titular_inst.add(inst.capitalize())
            elif _conjuge and membro == _conjuge:
                conjuge_inst.add(inst.capitalize())

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
        "titular_inst": sorted(titular_inst),
        "conjuge_inst": sorted(conjuge_inst),
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


def _compute_salario_conjuge(e5_data: dict) -> float:
    """Compute conjuge CLT salary from fluxo mensal detalhado.

    Matches dataset labels against CLT source mappings from categorization.json.
    """
    rmd = e5_data.get("fluxo_caixa", {}).get("receita_despesa_mensal_detalhado", {})
    datasets = rmd.get("receita_datasets", [])
    for ds in datasets:
        label = ds.get("label", "")
        is_clt = (
            any(src_label in label for src_label in _CLT_SOURCE_LABELS)
            if _CLT_SOURCE_LABELS
            else ("CLT" in label)
        )
        if is_clt:
            nonzero = [v for v in ds.get("data", []) if v > 0]
            if nonzero:
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
    diversificacao_count = (
        len([c for c in composicao if isinstance(c, dict) and c.get("valor", 0) > 0]) or 5
    )

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
    investimentos_titular = pat.get(_KEY_INV_TITULAR, 0)
    investimentos_conjuge = pat.get(_KEY_INV_CONJUGE, 0)

    yield_imoveis_pct = round(_safe_div(receita_aluguel_anual, imoveis_invest) * 100, 1)

    salario_conjuge = _compute_salario_conjuge(e5_data)
    receita_recorrente_mensal = fluxo.get("receita_recorrente_mensal", 0)

    # --- From goals.json ---
    aportes = goals_cfg.get("aportes", {})
    dist = aportes.get("distribuicao", {})
    f1f2 = goals_cfg.get("fase_f1f2", {})
    dolar = goals_cfg.get("dolarizacao", {})
    seguros = goals_cfg.get("seguros", {})
    mar_eua = goals_cfg.get("cenarios_conjuge", goals_cfg.get("mariana_eua", {}))
    trib_cfg = goals_cfg.get("tributario", {})
    imov_cfg = goals_cfg.get("imoveis", {})
    thresholds = goals_cfg.get("thresholds", {})
    aloc_alvo = goals_cfg.get("alocacao_alvo", {})
    riscos = goals_cfg.get("riscos_prioritarios", [])
    decisoes = goals_cfg.get("decisoes_prioritarias", [])

    # --- Cenários cônjuge (computed by E5) ---
    cm = e5_data.get(_KEY_CENARIOS_CONJUGE, {})

    # --- Computed percentages (Cat. A) ---
    despesas_nao_id = desp_cat.get("nao_identificado", 0)

    pct_investivel = round(_safe_div(patrimonio_investivel, patrimonio_bruto) * 100, 1)
    pct_imoveis_bruto = round(_safe_div(imoveis_invest + residencia, patrimonio_bruto) * 100, 1)
    pct_receita_pj = round(_safe_div(receita_pj, receita_total) * 100, 1)
    pct_receita_aluguel = round(_safe_div(receita_aluguel, receita_total) * 100, 1)
    pct_receita_clt = round(_safe_div(receita_clt, receita_total) * 100, 1)
    pct_receita_outras = round(100 - pct_receita_pj - pct_receita_aluguel - pct_receita_clt, 1)
    pct_despesas_nao_id = round(_safe_div(despesas_nao_id, despesa_total) * 100, 1)

    receita_pj_anual = (receita_pj / n_meses_periodo) * 12 if n_meses_periodo else 0
    das_aliquota_pct = FISCAL.get("das_simples", {}).get("aliquota_efetiva_pct", 6.0) / 100
    das_anual = receita_pj_anual * das_aliquota_pct
    das_mensal = das_anual / 12 if receita_pj_anual else 0
    pct_das_receita_pj = round(das_aliquota_pct * 100, 1)

    if_cfg = goals_cfg.get("independencia_financeira", {})
    renda_passiva_meta = if_cfg.get("renda_passiva_meta_mensal", 0)
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

    # Cônjuge EUA vs CLT computation
    renda_eua_projetada_usd = mar_eua.get("renda_rn_projetada_usd", 0)
    renda_eua_projetada_brl = renda_eua_projetada_usd * cambio
    pct_renda_eua_vs_clt = (
        round((1 - _safe_div(renda_eua_projetada_brl, salario_conjuge)) * 100, 0)
        if salario_conjuge
        else 0
    )

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
        _KEY_INV_TITULAR: investimentos_titular,
        _KEY_INV_CONJUGE: investimentos_conjuge,
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
        _KEY_IDADE_TITULAR_IF: goals.get(f"idade_{_TITULAR_KEY}_if", 0),
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
        _KEY_SAL_CONJUGE: salario_conjuge,
        "receita_aluguel_anual": round(receita_aluguel_anual, 2),
        "yield_imoveis_pct": yield_imoveis_pct,
        "sobra_mensal_f1f2": round(sobra_mensal_f1f2, 2),
        "das_anual_estimado": round(das_anual, 2),
        "receita_pj_anual": round(receita_pj_anual, 2),
        "das_aliquota_pct": round(das_aliquota_pct * 100, 1),
        "anos_para_if_calculo": round(prazo_anos),
        "aportes_acum_prazo": round(aportes_acum_prazo, 0),
        "renda_eua_projetada_brl": round(renda_eua_projetada_brl, 0),
        # === Computed: top asset & institutions (from E4) ===
        "top_asset_nome": top_asset["nome"],
        "top_asset_valor": top_asset["valor"],
        "top_asset_membro": top_asset["membro"],
        _KEY_INST_TITULAR: ", ".join(inst_data["titular_inst"])
        if inst_data["titular_inst"]
        else "múltiplas instituições",
        _KEY_INST_CONJUGE: ", ".join(inst_data["conjuge_inst"])
        if inst_data["conjuge_inst"]
        else "não identificadas",
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
        _KEY_F1F2_TITULAR: f1f2.get(f"estrategia_{_TITULAR_KEY}", ""),
        _KEY_F1F2_CONJUGE: f1f2.get(f"estrategia_{_CONJUGE_KEY}", ""),
        "f1f2_crescimento_salarial": f1f2.get("crescimento_salarial_eua_pct", "3-4"),
        # === config/goals.json: seguros ===
        "seguro_vida_minimo": seguros.get("vida_term_minimo", 0),
        "seguro_vida_maximo": seguros.get("vida_term_maximo", 0),
        # === config/goals.json: cônjuge EUA ===
        f"renda_{_CONJUGE_KEY}_eua_minima": mar_eua.get("renda_rn_minima_usd", 0),
        f"renda_{_CONJUGE_KEY}_eua_maxima": mar_eua.get("renda_rn_maxima_usd", 0),
        _KEY_RENDA_CONJUGE_EUA_PROJ: renda_eua_projetada_usd,
        # === Tributário (calculado a partir de parametros_fiscais.json + dados reais) ===
        "das_mensal_estimado": round(das_mensal, 2),
        "contador_mensal": trib_cfg.get("contador_mensal", 0),
        "contador_nome": trib_cfg.get("contador_nome", ""),
        "contador_canal": trib_cfg.get("contador_canal_pagamento", ""),
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
        # === cenarios cônjuge (computed by E5) ===
        "cm_labels": cm.get("labels", []),
        "cm_aportes": cm.get("aportes", []),
        "cm_prazos": cm.get("prazos_if", []),
        "cm_anos_if": cm.get("anos_if", []),
        f"cm_idade_{_TITULAR_KEY}": cm.get(f"idade_{_TITULAR_KEY}_if", []),
        "cm_cenarios": cm.get("cenarios", []),
        "cm_fator_reduzido": cm.get("premissas", {}).get("fator_reduzido", 0.66),
        "cm_renda_nclex_usd": cm.get("premissas", {}).get("renda_nclex_usd", 4000),
        "cm_renda_nclex_brl": cm.get("premissas", {}).get("renda_nclex_brl", 0),
        "cm_renda_gc_usd": cm.get("premissas", {}).get("renda_gc_usd", 7000),
        "cm_renda_gc_brl": cm.get("premissas", {}).get("renda_gc_brl", 0),
        "cm_salario_clt_brl": cm.get("premissas", {}).get(f"salario_{_CONJUGE_KEY}_clt_brl", 0),
        "cm_recovery_nclex_pct": cm.get("premissas", {}).get("recovery_nclex_pct", 0),
        "cm_recovery_gc_pct": cm.get("premissas", {}).get("recovery_gc_pct", 0),
    }


# ------------------------------------------------------------------------
# Helpers de formatação + validator
# ------------------------------------------------------------------------
# A6d.3.2 — lógica movida para ``pipeline/domain/services/narrativas/``.
# Mantemos aliases aqui para backward-compat com scripts/testes legados que
# fazem ``from scripts.e5n_narrativas import fmt_currency``.
from pipeline.domain.services.narrativas.format_helpers import (
    fmt_currency,
    fmt_num,
    fmt_percent,
    fmt_usd,
)
from pipeline.domain.services.narrativas.format_helpers import (
    validate_narrativas as _validate_narrativas_impl,
)


def validate_narrativas(narrativas_obj):
    """Delegates para ``pipeline.domain.services.narrativas.validate_narrativas``.

    Injeta a ``cenarios_section`` key dinâmica do módulo
    (``_KEY_CENARIOS_SECTION``, ex.: ``"mariana_cenarios"``), preservando
    paridade com o legado sem depender de globals no helper.
    """
    return _validate_narrativas_impl(narrativas_obj, cenarios_section_key=_KEY_CENARIOS_SECTION)


def build_narrativas():
    """Constrói o objeto ``narrativas`` completo — delega para
    :class:`pipeline.domain.services.narrativas.E5NarrativasBuilder`
    (A6d.3.2, Caminho B puro).

    Mantido como entry-point legado que lê ``METRICS`` + ``FAMILY`` do
    módulo (populados por ``main`` / ``main_with_store``). Paridade 100%
    com a implementação original (425 locs) coberta por
    ``tests/test_e5n_main_with_store_parity.py``.
    """
    from pipeline.domain.services.narrativas import E5NarrativasBuilder

    builder = E5NarrativasBuilder.from_family_config(FAMILY)
    return builder.build(METRICS, FAMILY)


def main(root_dir: Path = None):
    """Main execution function."""
    if root_dir:
        _init_config(root_dir)

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

    with open(E5_JSON_PATH, "r", encoding="utf-8") as f:
        e5_data = json.load(f)

    print(f"✓ Loaded E5 JSON with {len(e5_data)} top-level keys")
    print()

    # Load metrics dynamically from E5 JSON
    global METRICS
    METRICS = load_metrics_from_e5(e5_data)
    none_count = sum(1 for v in METRICS.values() if v is None)
    if none_count > 0:
        print(f"  [WARN] {none_count} métricas com valor None após carregamento do E5")
    print(f"✓ Loaded {len(METRICS)} metrics from E5 JSON")
    print(f"  Score: {METRICS['score']}/10, Patrimônio: R$ {METRICS['patrimonio_bruto']:,.0f}")
    print()

    # Build narrativas
    print("Building narrativas object with metrics from E5 JSON...")
    narrativas = build_narrativas()
    print(f"✓ Built narrativas with {len(narrativas)} main sections")
    print("  - perfil_familia: left and right sections")
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
    with open(E5_JSON_PATH, "w", encoding="utf-8") as f:
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
    print(f"  Cobertura Despesas: {fmt_num(METRICS['cobertura_meses'])} meses")
    print(f"  Taxa Endividamento: {fmt_percent(METRICS['taxa_endividamento'])}")
    print(f"  Progresso IF: {fmt_percent(METRICS['progresso_if'])}")
    print(f"  Patrimônio Bruto: {fmt_currency(METRICS['patrimonio_bruto'])}")
    print(f"  Patrimônio Investível: {fmt_currency(METRICS['patrimonio_investivel'])}")
    print(f"  IF Gap: {fmt_currency(METRICS['if_gap'])}")
    print(f"  IF Prazo: {fmt_num(METRICS['if_prazo_anos'])} anos (ano {METRICS['if_ano']})")
    print()

    return True


def main_with_store(ctx) -> dict:
    """E5.N Caminho B (Sessão A5e da Fase 8) — enriquece E5 com narrativas
    sobre ``ArtifactStore`` em vez de disco direto.

    Coexiste com ``main(root_dir)`` legado. Wrapper ``pipeline/stages/e5n.py``
    chama esta função direto, sem ``MaterializationBridge``.

    Estratégia pragmática (mesma de A5d): reutiliza ``load_metrics_from_e5``
    + ``build_narrativas`` + ``validate_narrativas`` legados para paridade
    garantida no golden. Lê/escreve E5 via ``ArtifactStore``.

    Args:
        ctx: ``pipeline.context.WorkspaceContext``.

    Returns:
        Dict com ``success``, ``narrativas_section_count``, ``files_created``.
    """
    import scripts.pipeline_common as _pc

    # Reinicializa globals do módulo + pipeline_common.
    _pc._init_config(ctx.root)
    _init_config(ctx.root)

    print("=" * 80)
    print("E5.N NARRATIVAS GENERATOR — Caminho B (main_with_store)")
    print("=" * 80)
    print()

    store = ctx.get_artifact_store()
    print(f"[E5.N.0] Workspace root: {ctx.root}")
    print(f"[E5.N.0] Store impl:     {type(store).__name__}")

    # 1. Lê E5 via store.
    e5_data = store.read("E5", "analise_financeira") or {}
    if not e5_data:
        print("✗ E5 artifact 'analise_financeira' não encontrado. Execute E5 primeiro.")
        return {"success": False, "reason": "e5_not_found"}

    print(f"✓ Loaded E5 artifact with {len(e5_data)} top-level keys")

    # 2. Carrega métricas + constrói narrativas via funções legadas.
    global METRICS
    METRICS = load_metrics_from_e5(e5_data)
    none_count = sum(1 for v in METRICS.values() if v is None)
    if none_count > 0:
        print(f"  [WARN] {none_count} métricas com valor None após carregamento do E5")
    print(f"✓ Loaded {len(METRICS)} metrics from E5")

    narrativas = build_narrativas()
    print(f"✓ Built narrativas with {len(narrativas)} main sections")

    # 3. Valida.
    is_valid, errors = validate_narrativas(narrativas)
    if not is_valid:
        print(f"✗ Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        return {"success": False, "reason": "validation_failed", "errors": errors}

    print("✓ Validation passed")

    # 4. Injeta narrativas no E5 e re-escreve via store.
    e5_data["narrativas"] = narrativas
    store.write("E5", "analise_financeira", e5_data)

    print("\n[E5.N.FINAL] Narrativas enriched!")
    print("  ✓ Stored: E5/analise_financeira (with narrativas)")
    print("=" * 80)

    return {
        "success": True,
        "narrativas_section_count": len(narrativas),
        "summaries_count": len(narrativas.get("summaries", {})),
        "charts_count": len(narrativas.get("charts", {})),
        "files_created": ["analise_financeira-5_analysis.json"],
    }


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
