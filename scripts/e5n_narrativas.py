#!/usr/bin/env python3
"""
E5.N Narrativas Generator
Generates updated narrativas for E5 analysis JSON with family financial context.
Metrics are loaded dynamically from E5 JSON at runtime.
"""

import json
import re
from decimal import Decimal
from pathlib import Path

import scripts.pipeline_common as _pc

# Configuration — paths e config re-inicializáveis via _init_config()
_DEFAULT_BASE_DIR = _pc._REPO_ROOT


def _load_json_safe(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _read_config_blob(name: str, disk_path: Path, ctx) -> dict:
    """Read config via ``ctx.load_config`` (DB-first via overrides, A7.1) or disk fallback."""
    if ctx is not None:
        return ctx.load_config(name)
    return _load_json_safe(disk_path)


def _init_config(base_dir: Path, *, ctx=None) -> None:
    """(Re-)inicializa paths/config globals a partir de base_dir; ``ctx`` lido em A7.1 via ``ctx.load_config`` (ADR-134)."""
    global SCRIPTS_DIR, PROJECT_DIR
    global E5_JSON_PATH, FAMILY_CONFIG_PATH, GOALS_CONFIG_PATH
    global TAXAS_CONFIG_PATH, CATEGORIZATION_CONFIG_PATH, FISCAL_CONFIG_PATH
    global FAMILY, _CATEGORIZATION, FISCAL, _CLT_SOURCE_LABELS
    global _TITULAR_KEY, _MEMBROS, _CONJUGE_KEY, _TITULAR_NOME, _CONJUGE_NOME
    global _KEY_INV_TITULAR, _KEY_INV_CONJUGE, _KEY_CENARIOS_CONJUGE
    global _KEY_IDADE_TITULAR_IF, _KEY_SAL_CONJUGE
    global _KEY_INST_TITULAR, _KEY_INST_CONJUGE
    global _KEY_CENARIOS_SECTION

    SCRIPTS_DIR = base_dir / "scripts"
    PROJECT_DIR = base_dir
    E5_JSON_PATH = PROJECT_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
    FAMILY_CONFIG_PATH = PROJECT_DIR / "config" / "family_members.json"
    GOALS_CONFIG_PATH = PROJECT_DIR / "config" / "goals.json"
    TAXAS_CONFIG_PATH = PROJECT_DIR / "config" / "taxas.json"
    CATEGORIZATION_CONFIG_PATH = PROJECT_DIR / "config" / "categorization.json"
    FISCAL_CONFIG_PATH = PROJECT_DIR / "config" / "parametros_fiscais.json"

    FAMILY = _read_config_blob("family_members.json", FAMILY_CONFIG_PATH, ctx)
    _CATEGORIZATION = _read_config_blob("categorization.json", CATEGORIZATION_CONFIG_PATH, ctx)

    _TITULAR_KEY = FAMILY.get("titular", "")
    _MEMBROS = FAMILY.get("membros", {})
    _CONJUGE_KEY = next(
        (k for k, v in _MEMBROS.items() if isinstance(v, dict) and v.get("papel") == "conjuge"), ""
    )
    _TITULAR_NOME = _MEMBROS.get(_TITULAR_KEY, {}).get("nome_curto", _TITULAR_KEY.title())
    _CONJUGE_NOME = _MEMBROS.get(_CONJUGE_KEY, {}).get("nome_curto", _CONJUGE_KEY.title())

    _KEY_INV_TITULAR = f"investimentos_{_TITULAR_KEY}"
    _KEY_INV_CONJUGE = f"investimentos_{_CONJUGE_KEY}"
    _KEY_IDADE_TITULAR_IF = f"idade_{_TITULAR_KEY}_if"
    _KEY_SAL_CONJUGE = f"salario_{_CONJUGE_KEY}"
    _KEY_INST_TITULAR = f"{_TITULAR_KEY}_instituicoes"
    _KEY_INST_CONJUGE = f"{_CONJUGE_KEY}_instituicoes"
    # ADR-166 + ADR-176: chave universal estável; não mais derivada de _CONJUGE_KEY.
    _KEY_CENARIOS_SECTION = "cenarios_conjuge"
    # ADR-168 cleanup (Sprint A10.1): _KEY_F1F2_TITULAR, _KEY_F1F2_CONJUGE,
    # _KEY_RENDA_CONJUGE_EUA_PROJ removidos — globals do Modo USA descontinuado
    # em A8.4 PR4 sem leitor após cirurgia das narrativas órfãs.

    FISCAL = _load_fiscal()
    _CLT_SOURCE_LABELS = list(_CATEGORIZATION.get("clt_source_mapping", {}).values())


def _load_fiscal():
    """Load fiscal parameters config (parametros_fiscais.json)."""
    if FISCAL_CONFIG_PATH.exists():
        with open(FISCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"  [WARN] parametros_fiscais.json não encontrado em {FISCAL_CONFIG_PATH}")
    return {}


# =============================================================================
# Module-level defaults (Sessão A6d.1 — eliminado side-effect no import)
# =============================================================================
#
# Antes de A6d.1: módulo invocava ``_init_config(_pc.PROJECT_DIR)`` no nível
# de módulo + ``FISCAL = _load_fiscal()`` (que lê parametros_fiscais.json).
# Agora ambos passam para dentro de ``_init_config`` e são populados por
# ``main(root_dir=...)`` / ``main_with_store(ctx)``. Os defaults abaixo
# garantem que helpers do módulo possam ser importados puros.
SCRIPTS_DIR: Path = _DEFAULT_BASE_DIR / "scripts"
PROJECT_DIR: Path = _DEFAULT_BASE_DIR
E5_JSON_PATH: Path = (
    PROJECT_DIR / "processed" / "E5_analysis" / "analise_financeira-5_analysis.json"
)
FAMILY_CONFIG_PATH: Path = PROJECT_DIR / "config" / "family_members.json"
GOALS_CONFIG_PATH: Path = PROJECT_DIR / "config" / "goals.json"
TAXAS_CONFIG_PATH: Path = PROJECT_DIR / "config" / "taxas.json"
CATEGORIZATION_CONFIG_PATH: Path = PROJECT_DIR / "config" / "categorization.json"
FISCAL_CONFIG_PATH: Path = PROJECT_DIR / "config" / "parametros_fiscais.json"
FAMILY: dict = {}
_CATEGORIZATION: dict = {}
FISCAL: dict = {}
_CLT_SOURCE_LABELS: list = []
_TITULAR_KEY: str = ""
_MEMBROS: dict = {}
_CONJUGE_KEY: str = ""
_TITULAR_NOME: str = ""
_CONJUGE_NOME: str = ""
_KEY_INV_TITULAR: str = "investimentos_"
_KEY_INV_CONJUGE: str = "investimentos_"
_KEY_IDADE_TITULAR_IF: str = "idade__if"
_KEY_SAL_CONJUGE: str = "salario_"
_KEY_INST_TITULAR: str = "_instituicoes"
_KEY_INST_CONJUGE: str = "_instituicoes"
_KEY_CENARIOS_SECTION: str = "cenarios_conjuge"


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
    """Lê o maior ativo individual de ``e5_data["investimentos"]["top_ativos"][0]`` (fonte canônica TopAtivosAnalyzer; substituiu leitura legacy do E4 disk artifact)."""
    top_ativos = (e5_data.get("investimentos") or {}).get("top_ativos") or []
    if not top_ativos:
        return {"nome": "", "valor": 0, "membro": "", "instituicao": ""}
    top = top_ativos[0]
    return {
        "nome": top.get("nome", ""),
        "valor": top.get("valor", 0),
        "membro": top.get("membro", ""),
        "instituicao": top.get("instituicao", ""),
    }


def _extract_top_institutions(e5_data: dict) -> dict:
    """Lê instituições por membro + n_imoveis de ``e5_data["investimentos"]`` (fonte canônica InstituicoesPorMembroAnalyzer; substituiu leitura legacy de E4 disk artifacts)."""
    _titular = FAMILY.get("titular", "")
    _membros = FAMILY.get("membros", {})
    _conjuge = next((k for k, v in _membros.items() if v.get("papel") == "conjuge"), None)

    inv_block = e5_data.get("investimentos") or {}
    by_member = {
        entry.get("membro", ""): list(entry.get("instituicoes") or [])
        for entry in inv_block.get("instituicoes_por_membro") or []
        if isinstance(entry, dict)
    }
    return {
        "titular_inst": sorted(by_member.get(_titular, [])),
        "conjuge_inst": sorted(by_member.get(_conjuge, [])) if _conjuge else [],
        "n_imoveis": int(inv_block.get("n_imoveis_total", 0)),
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


def load_metrics_from_e5(e5_data: dict, *, cambio_usd_brl: Decimal | float | None = None) -> dict:
    """Extract METRICS dict from E5 JSON + config/goals.json + computed values.

    Sources:
      - E5 JSON: patrimônio, goals, fluxo_caixa, ratios, score, etc.
      - config/goals.json: strategic targets (aportes, IF, F1/F2, seguros, etc.)
      - config/taxas.json: câmbio, CDI, SELIC, IPCA
      - Computed: yield, salary median, USD savings, derived ratios

    A7.5: ``cambio_usd_brl`` (Decimal/float) tem prioridade sobre ``taxas.json``
    quando passado pelo caller (resolvido via ``ConfigStore.get_market_rate``).
    """
    goals_cfg = _load_goals()
    taxas_cfg = _load_taxas()
    if cambio_usd_brl is not None:
        taxas_cfg = {**taxas_cfg, "cambio_usd_brl": float(cambio_usd_brl)}

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
    # ADR-168 cleanup (Sprint A10.1): `fase_f1f2` ainda lida para 3 campos
    # de viagem (custo_viagem_minimo/maximo, viagens_anuais_estimadas)
    # consumidos pelo chart `viagens` — outras chaves do Modo USA foram
    # removidas. `mariana_eua`/`cenarios_conjuge` (renda_rn_*) removidas.
    # Quando o seed (A10.1+) não popular essas seções, `f1f2.get(...)`
    # retorna 0 sem quebrar narrativas.
    f1f2 = goals_cfg.get("fase_f1f2", {})
    dolar = goals_cfg.get("dolarizacao", {})
    seguros = goals_cfg.get("seguros", {})
    trib_cfg = goals_cfg.get("tributario", {})
    aloc_alvo = goals_cfg.get("alocacao_alvo", {})
    riscos = goals_cfg.get("riscos_prioritarios", [])
    decisoes = goals_cfg.get("decisoes_prioritarias", [])

    # --- Rules-as-code (ADR-177): thresholds metodológicos universais ---
    # Imports locais por simetria com convenção do módulo (paths/config
    # também são late-bound). Substitui leituras de
    # ``goals_cfg["imoveis"]`` e ``goals_cfg["thresholds"]``.
    from pipeline.domain.services.methodology_constants import (
        EQUITY_PCT_ALVO_DEFAULT_MAX,
        EQUITY_PCT_ALVO_DEFAULT_MIN,
        IMOVEL_PCT_PATRIMONIO_IDEAL,
        YIELD_POTENCIAL_FII_BR_PCT_MAX,
        YIELD_POTENCIAL_FII_BR_PCT_MIN,
    )

    # --- Cenários cônjuge (computed by E5) ---
    cm = e5_data.get("cenarios_conjuge", {})

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

    # --- USD savings computed from E3 saldos per bank ---
    usd_saldos = _compute_usd_saldos_per_bank(e5_data)
    poupanca_usd = usd_saldos.get("total_usd", 0)
    meta_usd = dolar.get("meta_usd", 0)
    gap_usd = max(0, meta_usd - poupanca_usd)
    cambio = taxas_cfg.get("cambio_usd_brl", 5.80)
    aporte_cambial_brl = dolar.get("aporte_mensal_brl", 0)
    aporte_cambial_usd = _safe_div(aporte_cambial_brl, cambio)
    meses_cambial = int(_safe_div(gap_usd, aporte_cambial_usd)) if aporte_cambial_usd > 0 else 0

    # ADR-168 cleanup (Sprint A10.1): cálculo de `renda_eua_projetada_*` e
    # `pct_renda_eua_vs_clt` removidos — chaves dead-data do Modo USA.

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
        # === Computed from E5 data ===
        _KEY_SAL_CONJUGE: salario_conjuge,
        "receita_aluguel_anual": round(receita_aluguel_anual, 2),
        "yield_imoveis_pct": yield_imoveis_pct,
        "das_anual_estimado": round(das_anual, 2),
        "receita_pj_anual": round(receita_pj_anual, 2),
        "das_aliquota_pct": round(das_aliquota_pct * 100, 1),
        "anos_para_if_calculo": round(prazo_anos),
        "aportes_acum_prazo": round(aportes_acum_prazo, 0),
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
        # === config/goals.json: viagens (chart vivo — único campo F1/F2 preservado) ===
        # ADR-168 cleanup (Sprint A10.1): demais campos de fase_f1f2,
        # mariana_eua/cenarios_conjuge (renda_rn_*) removidos. Chave
        # `fase_f1f2` em goals.json passou a ser dead-data filtrada do seed.
        "custo_viagem_minimo": f1f2.get("custo_viagem_minimo", 0),
        "custo_viagem_maximo": f1f2.get("custo_viagem_maximo", 0),
        "viagens_anuais_estimadas": f1f2.get("viagens_anuais_estimadas", 0),
        # === config/goals.json: seguros ===
        "seguro_vida_minimo": seguros.get("vida_term_minimo", 0),
        "seguro_vida_maximo": seguros.get("vida_term_maximo", 0),
        # === Tributário (calculado a partir de parametros_fiscais.json + dados reais) ===
        "das_mensal_estimado": round(das_mensal, 2),
        "contador_mensal": trib_cfg.get("contador_mensal", 0),
        "contador_nome": trib_cfg.get("contador_nome", ""),
        "contador_canal": trib_cfg.get("contador_canal_pagamento", ""),
        "regime_obs": trib_cfg.get("regime_obs", ""),
        "holding_prazo": trib_cfg.get("holding_avaliacao_prazo", ""),
        # === imóveis (rules-as-code, ADR-177) ===
        "yield_imoveis_potencial_pct_min": float(YIELD_POTENCIAL_FII_BR_PCT_MIN),
        "yield_imoveis_potencial_pct_max": float(YIELD_POTENCIAL_FII_BR_PCT_MAX),
        # === thresholds (rules-as-code, ADR-177) & alocação ===
        "threshold_imovel_pct": float(IMOVEL_PCT_PATRIMONIO_IDEAL),
        "equity_alvo_min": float(EQUITY_PCT_ALVO_DEFAULT_MIN),
        "equity_alvo_max": float(EQUITY_PCT_ALVO_DEFAULT_MAX),
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
        "cm_salario_clt_brl": cm.get("premissas", {}).get(f"salario_{_CONJUGE_KEY}_clt_brl", 0),
        # ADR-168 cleanup (Sprint A10.1): cm_renda_nclex_*, cm_renda_gc_*,
        # cm_recovery_nclex_pct, cm_recovery_gc_pct removidos — premissas
        # NCLEX/Green Card do Modo USA descontinuado em A8.4 PR4 (ADR-167
        # já reduziu cenários do analyzer para 1 universal "Sem renda do
        # cônjuge"; este dict era débito remanescente).
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

    Repassa ``_KEY_CENARIOS_SECTION``, fixado em ``"cenarios_conjuge"``
    desde ADR-176 (era ``f"{_CONJUGE_KEY}_cenarios"`` antes). Mantido
    como entry-point legado.
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


def _e5n_print_header(ctx, store) -> None:
    print("=" * 80)
    print("E5.N NARRATIVAS GENERATOR — Caminho B (main_with_store)")
    print("=" * 80)
    print()
    print(f"[E5.N.0] Workspace root: {ctx.root}")
    print(f"[E5.N.0] Store impl:     {type(store).__name__}")


def _e5n_load_e5(store) -> dict | None:
    e5_data = store.read("E5", "analise_financeira") or {}
    if not e5_data:
        print("✗ E5 artifact 'analise_financeira' não encontrado. Execute E5 primeiro.")
        return None
    print(f"✓ Loaded E5 artifact with {len(e5_data)} top-level keys")
    return e5_data


def _e5n_load_metrics(
    e5_data: dict, *, cambio_usd_brl: Decimal | float | None = None
) -> _MetricsProxy:
    global METRICS
    METRICS = load_metrics_from_e5(e5_data, cambio_usd_brl=cambio_usd_brl)
    none_count = sum(1 for v in METRICS.values() if v is None)
    if none_count > 0:
        print(f"  [WARN] {none_count} métricas com valor None após carregamento do E5")
    print(f"✓ Loaded {len(METRICS)} metrics from E5")
    return METRICS


def _e5n_build_and_validate() -> tuple[dict | None, list[str]]:
    narrativas = build_narrativas()
    print(f"✓ Built narrativas with {len(narrativas)} main sections")
    is_valid, errors = validate_narrativas(narrativas)
    if not is_valid:
        print(f"✗ Validation failed with {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        return None, errors
    print("✓ Validation passed")
    return narrativas, []


def _resolve_cambio_via_config_store(ctx) -> Decimal | None:
    """Resolve USD/BRL via ``ctx.config_store.get_market_rate`` (A7.5); ``None`` se indisponível."""
    cs = getattr(ctx, "config_store", None) if ctx is not None else None
    if cs is None:
        return None
    try:
        from datetime import date as _date

        return cs.get_market_rate("USD/BRL", _date.today())
    except Exception as exc:  # pragma: no cover — fallback transparente
        print(f"  [warn] ConfigStore.get_market_rate USD/BRL falhou ({exc}); usando taxas.json")
        return None


def _e5n_persist(store, e5_data: dict, narrativas: dict) -> None:
    e5_data["narrativas"] = narrativas
    store.write("E5", "analise_financeira", e5_data)
    print("\n[E5.N.FINAL] Narrativas enriched!")
    print("  ✓ Stored: E5/analise_financeira (with narrativas)")
    print("=" * 80)


def _e5n_generate_section_summaries(ctx, e5_data: dict) -> dict:
    """Hook v2.9 — gera section_summaries via LLM se MATHOMS_LLM_SECTION_SUMMARIES=1."""
    # Falha aberta: import erro / generator off → retorna {} (E5.N
    # continua sem o campo; frontend cai em deriveSectionSummary).
    try:
        from backend.app.services.section_summary_orchestrator import (
            generate_all_section_summaries,
        )
    except Exception as exc:  # noqa: BLE001 — pipeline standalone (sem backend)
        print(f"  [info] section_summaries skipped (backend unavailable): {exc}")
        return {}

    workspace_id = _resolve_workspace_id(ctx)
    return generate_all_section_summaries(workspace_id=workspace_id, e5_data=e5_data)


def _resolve_workspace_id(ctx) -> int:
    candidate = getattr(ctx, "workspace_id", None) if ctx is not None else None
    if isinstance(candidate, int):
        return candidate
    if isinstance(candidate, str) and candidate.isdigit():
        return int(candidate)
    return 0


def main_with_store(ctx) -> dict:
    """E5.N Caminho B (Sessão A5e da Fase 8) — enriquece E5 com narrativas
    sobre ``ArtifactStore`` em vez de disco direto.

    Coexiste com ``main(root_dir)`` legado. Wrapper ``pipeline/stages/e5n.py``
    chama esta função direto, sem ``MaterializationBridge``.

    Estratégia pragmática (mesma de A5d): reutiliza ``load_metrics_from_e5``
    + ``build_narrativas`` + ``validate_narrativas`` legados para paridade
    garantida no golden. Lê/escreve E5 via ``ArtifactStore``.
    """
    import scripts.pipeline_common as _pc

    _pc._init_config(ctx.root)
    _init_config(ctx.root, ctx=ctx)

    store = ctx.get_artifact_store()
    _e5n_print_header(ctx, store)

    e5_data = _e5n_load_e5(store)
    if e5_data is None:
        return {"success": False, "reason": "e5_not_found"}

    cambio_usd_brl = _resolve_cambio_via_config_store(ctx)
    _e5n_load_metrics(e5_data, cambio_usd_brl=cambio_usd_brl)
    narrativas, errors = _e5n_build_and_validate()
    if narrativas is None:
        return {"success": False, "reason": "validation_failed", "errors": errors}

    # v2.9 · ADR-144 — LLM-driven section summaries (toggle por env;
    # default OFF até v2.9.1 revisar copy). Falha aberta.
    e5_data["narrativas"] = narrativas  # disponível p/ fallback determinístico do generator
    section_summaries = _e5n_generate_section_summaries(ctx, e5_data)
    if section_summaries:
        e5_data["section_summaries"] = section_summaries
        print(f"  ✓ section_summaries (LLM): {len(section_summaries)} seções")

    _e5n_persist(store, e5_data, narrativas)
    return {
        "success": True,
        "narrativas_section_count": len(narrativas),
        "summaries_count": len(narrativas.get("summaries", {})),
        "charts_count": len(narrativas.get("charts", {})),
        "section_summaries_count": len(section_summaries),
        "files_created": ["analise_financeira-5_analysis.json"],
    }
