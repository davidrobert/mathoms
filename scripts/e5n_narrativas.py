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


def load_metrics_from_e5(e5_data: dict) -> dict:
    """Extract METRICS dict from E5 JSON data — replaces hardcoded values."""
    pat = e5_data.get("patrimonio", {})
    goals = e5_data.get("goals", {})
    fluxo = e5_data.get("fluxo_caixa", {})
    ratios = e5_data.get("ratios", {})
    score = e5_data.get("score", {})
    reserva = e5_data.get("reserva_emergencia", {})

    # Composição patrimonial — values stored as top-level keys in patrimonio
    imoveis_invest = pat.get("imoveis_investimento", 0)
    residencia = pat.get("residencia", 0)

    # Receitas por fonte
    por_fonte = fluxo.get("por_fonte", {})

    # Despesas por categoria
    desp_cat = fluxo.get("despesas_por_categoria", {})

    # Extract diversificacao from composition (count non-zero valued items)
    composicao = pat.get("composicao", [])
    diversificacao_count = len([c for c in composicao if isinstance(c, dict) and c.get("valor", 0) > 0]) or 5

    return {
        "score": score.get("valor", 0),
        "score_label": score.get("classificacao", ""),
        "taxa_poupanca": ratios.get("taxa_poupanca_recorrente_pct", 0),
        "cobertura_meses": reserva.get("cobertura_meses", 0),
        "taxa_endividamento": ratios.get("taxa_endividamento_pct", 0),
        "progresso_if": goals.get("if_pct", 0),
        "diversificacao": diversificacao_count,
        "patrimonio_bruto": pat.get("bruto", 0),
        "patrimonio_investivel": pat.get("investivel", 0),
        "imoveis_investimento": imoveis_invest,
        "residencia": residencia,
        "investimentos_david": pat.get("investimentos_david", 0),
        "investimentos_mariana": pat.get("investimentos_mariana", 0),
        "veiculos": pat.get("veiculos", 0),
        "dividas": e5_data.get("endividamento", {}).get("total_dividas", 0),
        "receita_total": fluxo.get("receita_total", 0),
        "receita_recorrente": fluxo.get("receita_recorrente", 0),
        "receita_recorrente_mensal": fluxo.get("receita_recorrente_mensal", 0),
        "despesa_total": fluxo.get("despesa_total", 0),
        "despesa_mensal_media": fluxo.get("despesa_mensal_media", 0),
        "fluxo_liquido": fluxo.get("fluxo_liquido", 0),
        "if_meta": goals.get("if_meta", 0),
        "if_gap": goals.get("if_gap", 0),
        "if_prazo_anos": goals.get("prazo_anos_realista", 0),
        "if_ano": goals.get("ano_if", 0),
        "renda_passiva_4pct": goals.get("renda_passiva_estimada_4pct", 0),
        "receita_pj": por_fonte.get("receita_pj", 0),
        "receita_clt": por_fonte.get("receita_clt", 0),
        "receita_aluguel": por_fonte.get("receita_aluguel", 0),
        "outras_receitas": por_fonte.get("outras", 0),
        "receita_investimento": por_fonte.get("receita_investimento", 0),
        "receita_resgate": por_fonte.get("receita_resgate", 0),
        "receita_restituicao": por_fonte.get("receita_restituicao", 0),
        "despesas_nao_id": desp_cat.get("nao_identificado", 0),
        "despesas_impostos": desp_cat.get("impostos", 0) + desp_cat.get("das", 0),
        "despesas_moradia": desp_cat.get("moradia", 0),
        "despesas_serv_dom": desp_cat.get("servicos_domesticos", 0),
        "despesas_reserva": desp_cat.get("reserva_desejos", 0),
        "despesas_suporte": desp_cat.get("suporte_familiar", 0),
        "despesas_assinatura": desp_cat.get("assinaturas", 0),
        "salario_mariana": 10900,  # R$ 10,9k (hardcoded, can be updated from config if needed)
        "custo_fase_f1f2": 32400,  # R$ 32,4k estimated F1/F2 phase cost
        "sobra_mensal_f1f2": 38200,  # R$ 38,2k estimated monthly surplus during F1/F2
        "david_idade_if": 52,  # David's age when reaching IF (hardcoded, can be calculated from DOB)
        "anos_para_if_calculo": 9,  # Years to reach IF (can be derived from if_prazo_anos)
        "receita_aluguel_anual": 111343,  # Annual rental income (R$ 111.343)
        "das_mensal_estimado": 5000,  # Monthly DAS estimate (R$ 5k)
        "contador_mensal": 390,  # Monthly accountant fee (R$ 390)
        "das_anual_estimado": 60000,  # Annual DAS estimate (R$ 60k = 5k * 12)
        "meta_aporte_mensal": 20000,  # R$ 20k monthly contribution
        "yield_imoveis_pct": 3.2,  # 3.2% gross yield on investment properties
        "yield_imoveis_potencial_pct_min": 4,  # 4% potential minimum yield
        "yield_imoveis_potencial_pct_max": 6,  # 6% potential maximum yield
        "aporte_cofrinhos": 10000,  # R$ 10k to savings account
        "aporte_ipca_plus": 5000,  # R$ 5k to IPCA+
        "aporte_ivvb11": 3000,  # R$ 3k to IVVB11 (stocks)
        "aporte_wise_usd": 2000,  # R$ 2k to Wise (USD conversion)
        "seguro_vida_minimo": 3000000,  # R$ 3M minimum life insurance
        "seguro_vida_maximo": 5000000,  # R$ 5M maximum life insurance
        "renda_mariana_eua_minima": 4000,  # US$ 4k/month minimum RN salary USA
        "renda_mariana_eua_maxima": 7000,  # US$ 7k/month maximum RN salary USA
        "renda_mariana_eua_projetada": 5500,  # US$ 5.5k/month projected RN salary USA
        "poupanca_cambial_actual_usd": 7300,  # US$ 7.3k actual USD savings
        "poupanca_cambial_meta_usd": 20000,  # US$ 20k target USD savings
        "poupanca_cambial_gap_usd": 12600,  # US$ 12.6k gap to reach target
        "aporte_cambial_mensal": 2000,  # R$ 2k monthly USD contribution
        "meses_para_cambial": 37,  # Months to reach USD target (37 months)
        "custo_viagem_minimo": 20000,  # R$ 20k minimum per trip cost
        "custo_viagem_maximo": 30000,  # R$ 30k maximum per trip cost
        "viagens_anuais_estimadas": 2.5,  # 2-3 trips per year (average 2.5)
        "cdb_santander_david": 300000,  # R$ 300k CDB Santander (largest individual asset)
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


def build_narrativas():
    """Build complete narrativas object with updated metrics."""

    # Load family data from config
    _fm = FAMILY.get("membros", {})
    _david = _fm.get("david", {})
    _mariana = _fm.get("mariana", {})
    _theo = _fm.get("theo", {})
    _endereco = FAMILY.get("endereco", {})
    _pets = FAMILY.get("pets", [])
    _sobrenome = FAMILY.get("familia", {}).get("sobrenome", "Ferreira Campos")

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

    narrativas = {
        "perfil_familia": {
            "left": (
                f"<p>{_david.get('nome_completo', 'David Robert Camargo Ferreira Campos')}, {_david_age} anos, é o titular da família e atua como {_david.get('profissao', 'CTO da Arvo')}, "
                "healthtech especializada em auditoria de contas médicas com IA. Com mais de 23 anos de carreira em tecnologia, "
                f"{_david.get('nome_curto', 'David')} acumula passagens por Elo7, Loft e Kiwify em posições de liderança executiva. Formado em {_david.get('formacao', 'Ciência da Computação pela PUC-SP com mestrado em IA pela USP/IME')}, opera como {_david.get('regime', 'PJ Simples Nacional (Anexo V)')} através da empresa "
                f"{_david.get('nome_pj', 'David Robert Camargo de Campos Ltda.')}.</p>\n"
                f"<p>{_mariana.get('nome_completo', 'Mariana Ferreira Campos')}, {_mariana_age} anos, é {_mariana.get('profissao', 'enfermeira no Hospital Israelita Albert Einstein')} desde {_mariana.get('emprego_inicio', 'julho de 2014')}, "
                f"com especialização em {_mariana.get('formacao', 'Cardiologia e Hemodinâmica pela UNIFESP e mestrado em Enfermagem pela USP')}. Atualmente em "
                f"regime CLT com salário-base de {fmt_currency(METRICS['salario_mariana'])}/mês, Mariana também acumula experiência docente na Faculdade Einstein e no Senac. "
                f"Seu perfil é altamente competitivo para o mercado americano via NCLEX, com projeção de US$ {METRICS['renda_mariana_eua_minima']//1000}k a US$ {METRICS['renda_mariana_eua_maxima']//1000}k/mês como RN de cardiologia nos EUA.</p>\n"
                f"<p>{_theo.get('nome_completo', 'Theo Ferreira Campos')} nasceu em {_theo.get('local_nascimento', 'Orlando, Flórida')}, e possui dupla cidadania brasileira e americana. "
                "Com menos de um ano, é o primeiro filho do casal e peça central no planejamento de vida internacional da família.</p>\n"
                f"<p>A família conta ainda com {len(_pets)} gatos — {_pets_str} — que fazem parte do cotidiano na residência da {_endereco.get('rua', 'Rua Tasso da Silveira')}, em {_endereco.get('bairro', 'Vila Guarani')}, {_endereco.get('cidade', 'São Paulo')}.</p>"
            ),
            "right": (
                "<p>O plano de vida da família tem como eixo central a mudança para os Estados Unidos via visto F1/F2 "
                "(Anderson University, Carolina do Sul), seguida de processo de Green Card por EB2-NIW. Durante a estadia, David manterá seus contratos PJ brasileiros "
                "trabalhando remotamente, enquanto Mariana se prepara para a licença de enfermagem americana via NCLEX. O custo projetado da fase F1/F2 é de "
                f"{fmt_currency(METRICS['custo_fase_f1f2'])}/mês, com sobra estimada de {fmt_currency(METRICS['sobra_mensal_f1f2'])}/mês graças à renda PJ de David.</p>\n"
                "<p>A meta de independência financeira é de R$ 7,2M em patrimônio investível, correspondente a uma renda passiva de R$ 30k/mês com TRS de 5%. "
                f"O patrimônio investível atual de {fmt_currency(METRICS['patrimonio_investivel'])} representa {fmt_percent(METRICS['progresso_if'])} da meta. "
                f"No cenário realista com aportes de {fmt_currency(METRICS['meta_aporte_mensal'])}/mês e retorno real de 6% ao ano, o prazo estimado é de {METRICS['anos_para_if_calculo']} anos — David com {METRICS['david_idade_if']} anos, em {METRICS['if_ano']}. "
                "A renda passiva atual já atinge R$ 10k/mês (33,5% da meta) distribuída entre aluguéis, dividendos e rendimentos de renda fixa.</p>\n"
                f"<p>O patrimônio bruto da família totaliza {fmt_currency(METRICS['patrimonio_bruto'])}, composto por quatro imóveis "
                f"({fmt_currency(METRICS['imoveis_investimento'] + METRICS['residencia'])}, sendo {fmt_currency(METRICS['residencia'])} de residência própria e "
                f"{fmt_currency(METRICS['imoveis_investimento'])} em investimento), carteiras de investimentos financeiros de David ({fmt_currency(METRICS['investimentos_david'])}) "
                f"e Mariana ({fmt_currency(METRICS['investimentos_mariana'])}), e veículos ({fmt_currency(METRICS['veiculos'])}). O endividamento é baixo: "
                f"{fmt_currency(METRICS['dividas'])} em financiamento imobiliário no Itaú, representando {fmt_percent(METRICS['taxa_endividamento'])} do patrimônio bruto — "
                "classificado como saudável.</p>"
            )
        },
        "summaries": {
            "s1": (
                f"Patrimônio bruto de {fmt_currency(METRICS['patrimonio_bruto'])} com 65% investível ({fmt_currency(METRICS['patrimonio_investivel'])}). "
                f"Imóveis representam 71% do total, com residência própria de {fmt_currency(METRICS['residencia'])} e três imóveis de investimento somando "
                f"{fmt_currency(METRICS['imoveis_investimento'])}. Endividamento saudável de {fmt_percent(METRICS['taxa_endividamento'])} sobre o bruto."
            ),
            "s2": (
                f"Score financeiro de {METRICS['score']}/10 ({METRICS['score_label']}). Pontos fortes: taxa de poupança recorrente de {fmt_percent(METRICS['taxa_poupanca'])}, "
                f"cobertura de {fmt_percent(METRICS['cobertura_meses'])} meses de despesas e endividamento controlado. Receita total no período de {fmt_currency(METRICS['receita_total'])} "
                "com 78% proveniente de PJ, 9% de aluguel (QuintoAndar + imóveis), 8,6% de CLT (Mariana/Einstein) e 4,3% de outras fontes."
            ),
            "s3": (
                f"Carteira diversificada entre {METRICS['diversificacao']} categorias de ativos. David mantém {fmt_currency(METRICS['investimentos_david'])} distribuídos entre "
                "CDBs Santander, fundos Rico, renda fixa Itaú e C6. Mariana possui {fmt_currency(METRICS['investimentos_mariana'])} concentrados em BTG Pactual "
                "(82% renda fixa). Rentabilidade BTG Mariana: 10,8% em 12 meses."
            ),
            "s4": (
                f"Quatro imóveis no portfólio: residência na Tasso da Silveira ({fmt_currency(METRICS['residencia'])}), dois apartamentos alugados via QuintoAndar "
                f"(renda {fmt_currency(METRICS['receita_aluguel_anual'])}/ano = {fmt_currency(METRICS['receita_aluguel']/12)}/mês) e os apartamentos de Mariana via Living Wish (em consolidação). "
                f"Yield bruto dos imóveis de investimento estimado em {METRICS['yield_imoveis_pct']}% (receita/valor total)."
            ),
            "s5": (
                f"Meta de independência financeira atingirá {fmt_currency(METRICS['if_meta'])} em {METRICS['if_ano']}. "
                f"Gap atual de {fmt_currency(METRICS['if_gap'])} com prazo realista de {METRICS['if_prazo_anos']:.1f} anos à taxa de aporte R$ 20k/mês e retorno real 6% a.a. "
                f"Renda passiva estimada (4% TRS): {fmt_currency(METRICS['renda_passiva_4pct'])}/mês."
            ),
            "s6": (
                "Exposição cambial diversificada: US$ 4,7k em Wise, US$ 2,6k em Bank of America, US$ 92 em C6 Global e EUR 9 em C6 EUR. "
                "Meta pré-EUA de US$ 20k com gap de US$ 12,6k — ritmo de R$ 2k/mês na Wise alcança a meta em 37 meses."
            ),
            "s7": (
                f"Cinco riscos prioritários: FBAR/FATCA compliance, Estate Tax para non-residents, tributação PFIC sobre fundos brasileiros, dupla tributação BR-EUA "
                "e perda de qualidade INSS. Seguros de vida e invalidez inexistentes — classificados como urgentes. Planejamento sucessório em estágio inicial."
            ),
            "s8": (
                f"Regime Simples Nacional Anexo V com fator R favorável. DAS mensal estimado em {fmt_currency(METRICS['das_mensal_estimado'])}. AccountTech como contador ({fmt_currency(METRICS['contador_mensal'])}/mês via C6 PJ). "
                "Avaliação de holding patrimonial pendente para T4/2026. Obrigações fiscais EUA (FBAR, Form 8938, PFIC) requerem CPA expatriado antes da mudança."
            ),
            "s9": (
                f"Despesas totais no período: {fmt_currency(METRICS['despesa_total'])} ({fmt_currency(METRICS['despesa_mensal_media'])}/mês média). "
                f"Aumento de 51% em relação ao período anterior due to poupança direcionada e transferências para investimento. "
                f"Maior categoria 'não identificado' com {fmt_currency(METRICS['despesas_nao_id'])} (34% do total). "
                f"Impostos ({fmt_currency(METRICS['despesas_impostos'])}), moradia ({fmt_currency(METRICS['despesas_moradia'])}) e serviços domésticos "
                f"({fmt_currency(METRICS['despesas_serv_dom'])}) completam o perfil de gastos."
            ),
            "s10": (
                f"Cinco decisões estratégicas prioritárias: iniciar aporte mensal de {fmt_currency(METRICS['meta_aporte_mensal'])} ({fmt_currency(METRICS['aporte_cofrinhos'])} Cofrinhos, {fmt_currency(METRICS['aporte_ipca_plus'])} IPCA+, {fmt_currency(METRICS['aporte_ivvb11'])} IVVB11, {fmt_currency(METRICS['aporte_wise_usd'])} Wise USD), "
                f"contratar seguro de vida term R$ {METRICS['seguro_vida_minimo']//1_000_000}-{METRICS['seguro_vida_maximo']//1_000_000}M, agendar teste de inglês OET/MET para Mariana, consultar CPA expatriado para obrigações EUA, "
                "e agendar advogado sucessório para planejamento de herança."
            )
        },
        "charts": {
            "score_gauge": {
                "context": (
                    f"Indicador geral de saúde financeira da família, com score de {METRICS['score']}/10 "
                    f"({METRICS['score_label']}). Reflete equilíbrio entre pontos fortes (baixo endividamento, alta poupança) e oportunidades de melhoria."
                ),
                "conclusion": (
                    "A classificação 'Bom' representa melhoria significativa face aos ciclos anteriores, impulsionada por aumento na taxa de poupança "
                    "recorrente e redução da razão endividamento/patrimônio."
                )
            },
            "patrimonio_doughnut": {
                "context": (
                    f"Distribuição do patrimônio bruto de {fmt_currency(METRICS['patrimonio_bruto'])} entre 6 categorias de ativos, "
                    "mostrando concentração em imóveis e peso relativo dos investimentos financeiros e veículos."
                ),
                "conclusion": (
                    "Imóveis respondem por 71% do patrimônio — acima do ideal de 50%. "
                    "A venda do Living Concept (em andamento) e aportes mensais de R$ 20k em ativos financeiros devem melhorar essa proporção ao longo de 2026."
                )
            },
            "alocacao_atual": {
                "context": (
                    f"Atual distribuição dos ativos financeiros ({fmt_currency(METRICS['investimentos_david'] + METRICS['investimentos_mariana'])}) "
                    "entre classes de investimento: renda fixa, ações, fundos multimercado e estruturados."
                ),
                "conclusion": (
                    "Carteira de David é mais diversificada (CDB, fundos, renda fixa em múltiplas instituições) enquanto Mariana concentra em renda fixa BTG. "
                    "Recomendação: gradualmente adicionar alocação de ações (IVVB11, SCHP11) para atingir 20-25% de equity."
                )
            },
            "alocacao_alvo": {
                "context": (
                    "Alocação estratégica recomendada para os ativos financeiros, considerando horizonte de 20 anos até IF e tolerância ao risco médio."
                ),
                "conclusion": (
                    "Alvo: 50% Renda Fixa (IPCA+, CDBs), 25% Ações (IVVB11, SCHP11), 15% Imóveis/REITs, 10% Liquidez/USD. "
                    "Aportes de R$ 20k/mês priorizarão renda fixa em 2026, com rebalanceamento anual."
                )
            },
            "fluxo_mensal": {
                "context": (
                    f"Visão consolidada do fluxo de caixa mensal: receita recorrente de {fmt_currency(METRICS['receita_recorrente_mensal'])}/mês "
                    f"versus despesa média de {fmt_currency(METRICS['despesa_mensal_media'])}/mês."
                ),
                "conclusion": (
                    f"Saldo mensal positivo de {fmt_currency(METRICS['receita_recorrente_mensal'] - METRICS['despesa_mensal_media'])}/mês. "
                    f"Taxa de poupança de {fmt_percent(METRICS['taxa_poupanca'])} garante capacidade de aporte consistente. "
                    "Este saldo sustenta a meta de aportes mensais de R$ 20k para o plano IF."
                )
            },
            "receita_bar": {
                "context": (
                    f"Composição da receita total de {fmt_currency(METRICS['receita_total'])} por fonte: PJ (78%), CLT (8,6%), aluguel (8,4%), outras (5,1%)."
                ),
                "conclusion": (
                    f"Receita PJ de {fmt_currency(METRICS['receita_pj'])} mantém dominância (78%), mas diversificação aumentou com adição de CLT de Mariana ({fmt_currency(METRICS['receita_clt'])}, 8,6%) "
                    f"e captura correta de aluguel ({fmt_currency(METRICS['receita_aluguel'])} anual ou {fmt_currency(METRICS['receita_aluguel']/12)}/mês, 8,4% — triplicou com QuintoAndar em Bradesco). "
                    "Reduz risco de dependência única e expande base de renda recorrente."
                )
            },
            "receita_despesa_mensal": {
                "context": (
                    f"Série temporal mensal de receitas ({fmt_currency(METRICS['receita_total'])}/período) versus despesas ({fmt_currency(METRICS['despesa_total'])}/período), "
                    f"resultando em fluxo líquido de {fmt_currency(METRICS['fluxo_liquido'])}."
                ),
                "conclusion": (
                    f"Fluxo de caixa positivo em todos os meses, com receita recorrente mensalizada de {fmt_currency(METRICS['receita_recorrente_mensal'])}/mês e despesa média de {fmt_currency(METRICS['despesa_mensal_media'])}/mês. "
                    f"Taxa de poupança recorrente de {fmt_percent(METRICS['taxa_poupanca'])} valida a sustentabilidade do plano IF. Aumento de despesas reflete transferências para investimentos."
                )
            },
            "despesas_doughnut": {
                "context": (
                    f"Distribuição das despesas totais ({fmt_currency(METRICS['despesa_total'])}) entre 13 categorias, "
                    "destacando a composição de gastos e oportunidades de otimização."
                ),
                "conclusion": (
                    f"Categoria 'não identificado' lidera com {fmt_currency(METRICS['despesas_nao_id'])} (52%), seguida por impostos "
                    f"({fmt_currency(METRICS['despesas_impostos'])}), moradia ({fmt_currency(METRICS['despesas_moradia'])}) e serviços domésticos "
                    f"({fmt_currency(METRICS['despesas_serv_dom'])}). Prioridade: reclassificar e reduzir 'não identificado' via melhor rastreamento."
                )
            },
            "projecao_3cenarios": {
                "context": (
                    f"Projeção do patrimônio investível até atingir a meta de {fmt_currency(METRICS['if_meta'])}, "
                    f"considerando aportes mensais de {fmt_currency(METRICS['meta_aporte_mensal'])} e retorno real anual de 6%."
                ),
                "conclusion": (
                    f"Meta será atingida em {METRICS['if_ano']}, quando David terá {METRICS['david_idade_if']} anos. "
                    f"Renda passiva estimada será {fmt_currency(METRICS['renda_passiva_4pct'])}/mês (com 4% TRS), atingindo a meta de R$ 30k/mês. "
                    "Plano realista e alcançável com disciplina de aporte."
                )
            },
            "waterfall_if": {
                "context": (
                    f"Decomposição do gap de independência financeira ({fmt_currency(METRICS['if_gap'])}), mostrando componentes de patrimônio atual, "
                    f"aportes acumulados e rentabilidade esperada até {METRICS['if_ano']}."
                ),
                "conclusion": (
                    f"Gap total de {fmt_currency(METRICS['if_gap'])} será fechado por combinação de aportes disciplinados ({fmt_currency(METRICS['meta_aporte_mensal'])}/mês = R$ 4,92M em 20 anos) "
                    "e rentabilidade real de 6% a.a. sobre patrimônio acumulado. Cenário é resiliente a pequenas variações de aporte."
                )
            },
            "renda_passiva": {
                "context": (
                    f"Renda passiva estimada em diferentes cenários de patrimônio investível, assumindo TRS de 5% (alvo) e 4% (conservador)."
                ),
                "conclusion": (
                    f"Cenário atual ({fmt_currency(METRICS['patrimonio_investivel'])}): {fmt_currency(METRICS['renda_passiva_4pct'])}/mês (33,5% da meta). "
                    "Cenário 2035 (R$ 7,2M): R$ 30k/mês, atendendo exatamente a meta de TRS 5%. Diversidade de fontes (aluguel, dividendos, renda fixa) reduz risco."
                )
            },
            "yield_imoveis": {
                "context": (
                    f"Análise de yield bruto dos imóveis de investimento (valor total {fmt_currency(METRICS['imoveis_investimento'])}) "
                    "versus aluguel recebido mensalizado."
                ),
                "conclusion": (
                    f"Yield atual de {METRICS['yield_imoveis_pct']}% (conservador) com potencial de {METRICS['yield_imoveis_potencial_pct_min']}-{METRICS['yield_imoveis_potencial_pct_max']}% após venda do Living Concept e otimização de contratos. "
                    "Imóveis funcionam como hedge inflacionário e fonte de renda complementar."
                )
            },
            "top15_ativos": {
                "context": (
                    f"Ranking dos 15 maiores ativos financeiros individuais da família, totalizando {fmt_currency(METRICS['patrimonio_investivel'])} em investimentos."
                ),
                "conclusion": (
                    f"CDB Santander ({fmt_currency(METRICS['cdb_santander_david'])} de David) é o maior ativo individual, seguido por imóveis e fundos Rico. "
                    "Concentração em poucos ativos reforça importância de aportes contínuos para diversificação."
                )
            },
            "impostos_pj": {
                "context": (
                    f"Análise da carga tributária PJ de David (receita {fmt_currency(METRICS['receita_pj'])}), "
                    "estimando DAS mensal sob Simples Nacional Anexo V."
                ),
                "conclusion": (
                    f"DAS estimado em {fmt_currency(METRICS['das_mensal_estimado'])}/mês ({fmt_currency(METRICS['das_anual_estimado'])}/ano), representando ~6% da receita PJ. "
                    "Fator R favorável e contador AccountTech em funcionamento. Recomendação: avaliar holding patrimonial em T4/2026 para otimização."
                )
            },
            "mariana_cenarios": {
                "context": (
                    f"Cenários financeiros para Mariana pós-NCLEX, com projeções de renda americana como RN (US$ {METRICS['renda_mariana_eua_minima']//1000}k-{METRICS['renda_mariana_eua_maxima']//1000}k/mês) "
                    f"versus permanência no Brasil (CLT Einstein {fmt_currency(METRICS['salario_mariana'])}/mês)."
                ),
                "conclusion": (
                    f"Cenário EUA com US$ {METRICS['renda_mariana_eua_projetada']//1000}/mês = R$ 27,5k/mês (30% menor que CLT atual). "
                    "Compensado por: (1) integração com patrimônio de David, (2) renda PJ de David crescendo remotamente, "
                    "(3) renda de aluguel em BRL, (4) potencial de Green Card e crescimento salarial anual de 3-4%."
                )
            },
            "custos_f1f2": {
                "context": (
                    f"Estimativa de custos mensais na fase F1/F2 nos EUA: tuition + living + viagens BR = {fmt_currency(METRICS['custo_fase_f1f2'])}/mês."
                ),
                "conclusion": (
                    f"Sobra projetada: {fmt_currency(METRICS['sobra_mensal_f1f2'])}/mês ({fmt_currency(METRICS['receita_recorrente_mensal'])} - {fmt_currency(METRICS['custo_fase_f1f2'])}). "
                    "Permite acumular US$ 1,5k-2k/mês em Wise para precificação de propriedade americana, viabilizando compra de imóvel em 3-4 anos."
                )
            },
            "viagens": {
                "context": (
                    "Padrão de despesas com viagens identificado nos extratos, estimando frequência e custo médio."
                ),
                "conclusion": (
                    f"Viagens para EUA estimadas em {fmt_currency(METRICS['custo_viagem_minimo'])}-{fmt_currency(METRICS['custo_viagem_maximo'])} por viagem (passagens aéreas, hospedagem, vistos). "
                    f"Frequência média de {int(METRICS['viagens_anuais_estimadas'])}-3 viagens/ano para acompanhamento de processo F1/F2. Incluído em reserva específica."
                )
            },
            "cenarios_cambiais": {
                "context": (
                    f"Exposição cambial atual (US$ {int(METRICS['poupanca_cambial_actual_usd']/1000)},3k + EUR 9) e meta pré-EUA (US$ {int(METRICS['poupanca_cambial_meta_usd']/1000)}k), considerando desempenho do real."
                ),
                "conclusion": (
                    f"Gap de US$ {int(METRICS['poupanca_cambial_gap_usd']/1000)},6k com aporte atual de {fmt_currency(METRICS['aporte_cambial_mensal'])}/mês em Wise (R$ 360k/ano), atingindo meta em {METRICS['meses_para_cambial']} meses. "
                    "Risco cambial mitigado por (1) diversificação USD/EUR, (2) renda PJ em BRL compensando desvalorização, (3) flexibilidade de data de mudança."
                )
            },
            "bubble_riscos": {
                "context": (
                    "Identificação de 5 riscos críticos de compliance e proteção ao plano IF, com probabilidade e impacto."
                ),
                "conclusion": (
                    "Riscos prioritários: (1) FBAR/FATCA (alta prob., alto impacto), (2) Estate Tax non-resident (média prob., alto impacto), "
                    f"(3) Falta de seguro de vida (alta prob., crítico impacto). Ação: CPA expatriado + seguro term R$ {METRICS['seguro_vida_minimo']//1_000_000}-{METRICS['seguro_vida_maximo']//1_000_000}M em T2 2026."
                )
            },
            "top5_decisoes": {
                "context": (
                    "Cinco decisões estratégicas de curto prazo (6-12 meses) para otimizar a trajetória até IF."
                ),
                "conclusion": (
                    f"Prioridade 1: Aporte mensal {fmt_currency(METRICS['meta_aporte_mensal'])} com divisão ({fmt_currency(METRICS['aporte_cofrinhos'])} Cofrinhos, {fmt_currency(METRICS['aporte_ipca_plus'])} IPCA+, {fmt_currency(METRICS['aporte_ivvb11'])} IVVB11, {fmt_currency(METRICS['aporte_wise_usd'])} Wise USD). "
                    f"Prioridade 2: Seguro de vida termo R$ {METRICS['seguro_vida_minimo']//1_000_000}-{METRICS['seguro_vida_maximo']//1_000_000}M. Prioridade 3: NCLEX/OET para Mariana. Prioridade 4: CPA expatriado. "
                    "Prioridade 5: Advogado sucessório para planejamento de herança em cenário BR-EUA."
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
