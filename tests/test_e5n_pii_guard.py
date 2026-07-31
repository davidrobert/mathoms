"""PII no texto entregue das narrativas E5.N (A40.l4 · ADR-319 · ADR-355)."""

from __future__ import annotations

# O relatório é o artefato que a família guarda e mostra a terceiros (contador,
# corretor, banco). Antes desta guarda o card de perfil publicava
# `nome_completo` de adultos E de menor, o `s4` citava a residência por
# logradouro e o `s8` nomeava o contador — todos PII dura pela regra do repo.
#
# Três braços, do mais preciso ao mais amplo:
#
# A — sentinela por campo. A família de teste carrega um valor inventado e
#     inconfundível em cada campo PII; nenhum pode aparecer no texto emitido.
#     Campo novo que vaze fica vermelho sem ninguém editar o teste.
# B — forma de nome completo. Sequência de 2+ palavras capitalizadas é padrão
#     de nome próprio; a allowlist é de termos de domínio, com razão escrita.
# C — regra estática. Nenhum módulo de narrativa LÊ campo PII da família. Pega
#     o vazamento antes de existir output (o gate de pre-commit
#     `dev/check_pipeline_log_pii.py` cobre log, não texto renderizado).
import re
from pathlib import Path
from typing import Any

import pytest

import scripts.generate_narratives as e5n
from pipeline.domain.services.narrativas import E5NarrativasBuilder

_NARRATIVAS_DIR = Path(e5n.__file__).resolve().parents[1] / "pipeline/domain/services/narrativas"

# Sentinelas: PII-shaped, impossíveis de aparecer em copy de domínio. Cada
# entrada é `(rótulo do campo, valor)` — o rótulo entra na mensagem de falha.
_SENTINELAS: dict[str, str] = {
    "membros.titular.nome_completo": "Zebedeu Quirinovaldo Xisto",
    "membros.conjuge.nome_completo": "Zulmira Quaresmeira Ypsilon",
    "membros.filho.nome_completo": "Zezinho Quirinovaldo Xisto",
    "membros.filho.local_nascimento": "Quixabeirópolis",
    "membros.titular.cpf": "123.456.789-09",
    # Nome civil anterior (`extra.nome_nascimento`, `member_name_resolver`):
    # PII da mesma classe de `nome_completo` e faltava na família-sentinela.
    # Aparece nos dois paths que o resolver aceita — raiz e `extra`.
    "membros.conjuge.nome_nascimento": "Zulmira Quaresmeira Zabumba",
    "membros.conjuge.extra.nome_nascimento": "Zulmira Quinquagesima Zabumba",
    "endereco.rua": "Travessa Zorobabel Quintanilha",
    "endereco.bairro": "Vila Quimbanda",
    "endereco.cidade": "Quixabeirópolis do Norte",
    "tributario.contador_nome": "Zyxwv Quokka Contabilidade",
}

# `nome_curto` de DUAS palavras é caso legítimo e comum ("Ana Clara", "João
# Pedro") — e é o substituto SANCIONADO pela §D9. O braço B precisa distingui-lo
# de nome completo, senão a única saída de quem vê a falha é pôr nome de pessoa
# na allowlist de termos de domínio, exatamente o que a §D9 proíbe. A família de
# teste carrega um desses de propósito.
_NOME_CURTO_TITULAR = "Alex Zé"
_NOME_CURTO_CONJUGE = "Bia"

_FAMILY: dict[str, Any] = {
    "titular": "alex",
    "endereco": {
        "rua": _SENTINELAS["endereco.rua"],
        "bairro": _SENTINELAS["endereco.bairro"],
        "cidade": _SENTINELAS["endereco.cidade"],
    },
    "pets": ["Mingau"],
    "membros": {
        "alex": {
            "papel": "titular",
            "nome_curto": _NOME_CURTO_TITULAR,
            "nome_completo": _SENTINELAS["membros.titular.nome_completo"],
            "cpf": _SENTINELAS["membros.titular.cpf"],
            "data_nascimento": "1985-06-15",
            "regime": "PJ Simples",
        },
        "bia": {
            "papel": "conjuge",
            "nome_curto": _NOME_CURTO_CONJUGE,
            "nome_completo": _SENTINELAS["membros.conjuge.nome_completo"],
            "nome_nascimento": _SENTINELAS["membros.conjuge.nome_nascimento"],
            "extra": {"nome_nascimento": _SENTINELAS["membros.conjuge.extra.nome_nascimento"]},
            "data_nascimento": "1987-03-20",
        },
        "kim": {
            "papel": "filho",
            "nome_curto": "Kim",
            "nome_completo": _SENTINELAS["membros.filho.nome_completo"],
            "local_nascimento": _SENTINELAS["membros.filho.local_nascimento"],
            "cidadania": ["brasileira", "portuguesa"],
        },
    },
}

_GOALS: dict[str, Any] = {
    "independencia_financeira": {
        "if_meta": 5_000_000.0,
        "trs_pct": 5.0,
        "taxa_retirada_segura_pct": 4.0,
        "renda_passiva_meta_mensal": 16_000.0,
    },
    "aportes": {"meta_aporte_mensal": 20_000.0},
    "dolarizacao": {"meta_usd": 100_000.0, "aporte_mensal_brl": 2_000.0},
    "seguros": {"vida_term_minimo": 2_000_000, "vida_term_maximo": 4_000_000},
    "tributario": {
        "regime": "simples",
        "regime_label": "Simples Nacional — Anexo III",
        "contador_nome": _SENTINELAS["tributario.contador_nome"],
        "holding_prazo_meses": 12,
    },
    "risks_projection": [
        {"name": "Cobertura de vida abaixo do recomendado", "probability": "média"},
    ],
    "top5_decisoes_projection": [{"title": "Iniciar aporte mensal recorrente"}],
}


def _patrimonio() -> dict[str, Any]:
    return {
        "bruto": 2_500_000.0,
        "investivel_efetivo": 1_500_000.0,
        "residencia": 800_000.0,
        "imoveis_investimento": 400_000.0,
        "composicao": [{"categoria": "imoveis", "valor": 1_200_000.0}],
    }


def _fluxo() -> dict[str, Any]:
    return {
        "receita_total": 480_000.0,
        "receita_recorrente_mensal": 40_000.0,
        "despesa_mensal_media": 25_000.0,
        "despesa_total": 300_000.0,
        "por_fonte": {},
        "despesas_por_categoria": {"moradia": 1_000.0, "das_simples": 9_600.0},
    }


# A varredura só vale sobre o vocabulário que produção emite. Sem
# `alocacao_alvo.derived` o narrador do chart cai no "sem alvo" e os labels de
# classe de ativo ("Renda Fixa", "Ações Int.") nunca aparecem — foi por isso que
# o braço B ficava verde com termos de domínio fora da allowlist. Com o bloco, a
# allowlist é exercitada em vez de declarada no vácuo.
def _alocacao_alvo_derived() -> dict[str, Any]:
    return {
        "derived": {
            "has_alvo": True,
            "carteira_liquida_brl": 1_500_000.0,
            "imoveis_fisicos_brl": 400_000.0,
            "caixa": {"valor_brl": 50_000.0},
            "desvio_max_pct": 7.4,
            "next_aporte_classe": "acoes_int",
            "comparaveis": [
                {"classe": "renda_fixa", "atual_pct": 48.0, "alvo_pct": 40.0},
                {"classe": "acoes_br", "atual_pct": 22.0, "alvo_pct": 25.0},
                {"classe": "acoes_int", "atual_pct": 12.0, "alvo_pct": 20.0},
                {"classe": "fiis", "atual_pct": 18.0, "alvo_pct": 15.0},
            ],
        }
    }


def _e5_payload() -> dict[str, Any]:
    return {
        "patrimonio": _patrimonio(),
        "goals": {
            "if_meta": 5_000_000.0,
            "ano_if": 2039,
            "if_gap": 3_500_000.0,
            "alocacao_alvo": _alocacao_alvo_derived(),
        },
        "fluxo_caixa": _fluxo(),
        "ratios": {"taxa_poupanca_recorrente_pct": 35.0, "taxa_endividamento_pct": 8.0},
        "score": {"valor": 7.5, "classificacao": "Saudável"},
        "reserva_emergencia": {"cobertura_meses": 12.0},
    }


# O blob era ENUMERADO à mão (`perfil.left` + `perfil.right` + `summaries.*` +
# `charts[*].context/conclusion`). Campo de texto novo — um `charts[*].caption`,
# um `perfil_familia.footer`, uma chave nova no artefato — nascia fora da varredura
# e vazava sem deixar o teste vermelho. A varredura passa a ser do ARTEFATO
# INTEIRO: toda string alcançável a partir do que o builder devolve.
def _strings_do_artefato(node: Any) -> list[str]:
    """Todas as strings alcançáveis — chaves de dict incluídas."""
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [
            s for chave, valor in node.items() for s in ([str(chave)] + _strings_do_artefato(valor))
        ]
    if isinstance(node, (list, tuple)):
        return [s for item in node for s in _strings_do_artefato(item)]
    return []


@pytest.fixture(scope="module")
def texto_emitido(tmp_path_factory: pytest.TempPathFactory) -> str:
    """Todo texto do artefato ``narrativas`` num único blob (varredura recursiva)."""
    e5n._init_config(tmp_path_factory.mktemp("pii_guard"))
    metrics = e5n.load_metrics_from_e5(_e5_payload(), goals_cfg=_GOALS)
    out = E5NarrativasBuilder.from_family_config(_FAMILY).build(metrics, _FAMILY)
    return "\n".join(_strings_do_artefato(out))


# ───────────────────── Braço A — sentinela por campo ─────────────────────


@pytest.mark.parametrize("campo,valor", sorted(_SENTINELAS.items()))
def test_campo_pii_nao_chega_ao_texto_entregue(campo: str, valor: str, texto_emitido: str) -> None:
    """Nenhum campo PII da família aparece no texto que a família recebe."""
    assert valor not in texto_emitido, (
        f"`{campo}` vazou para o texto entregue das narrativas. Nome completo, "
        "CPF e endereço não vão ao relatório (ADR-319): use primeiro nome, "
        f"papel ou contagem. Valor ofensor: {valor!r}"
    )


def test_primeiro_nome_continua_disponivel(texto_emitido: str) -> None:
    """A guarda não é 'sem nome nenhum' — primeiro nome serve ao leitor."""
    assert _NOME_CURTO_TITULAR in texto_emitido, texto_emitido[:400]


# ─────────────────── Braço B — forma de nome completo ────────────────────

# Palavra capitalizada com ≥3 letras (exclui "IF", "PJ", "R$", "US$", ordinais).
_CAPITALIZADA = r"[A-ZÁÂÃÀÉÊÍÓÔÕÚÇ][a-záâãàéêíóôõúç]{2,}"
_SEQUENCIA_RE = re.compile(rf"{_CAPITALIZADA}(?:\s+{_CAPITALIZADA})+")

# Termos de domínio que legitimamente são multi-palavra capitalizada. Duas
# famílias, uma razão cada — nome de pessoa NUNCA entra aqui:
#
# - rótulos de regime tributário (`_REGIME_LABELS` do pipeline_adapter):
#   vocabulário público, um campo, um dono;
# - labels de classe de ativo da taxonomia canônica de 8 buckets (ADR-193,
#   `asset_classifier` / `alocacao_narrator._ALOC_CLASSE_LABELS`): entram no
#   texto do chart `alocacao_atual_vs_alvo`. Medido: rodar o braço B contra o
#   texto real (não contra a fixture antiga, que não produzia esse chart) acha
#   "Renda Fixa" e "Ações Int" — dois termos de domínio fora da allowlist. O
#   furo não era o texto; era a fixture não exercitar o vocabulário.
_TERMOS_DE_DOMINIO: frozenset[str] = frozenset(
    {
        # `regime_label` — a fixture emite "Simples Nacional"; os outros dois são
        # valores alternativos do MESMO campo.
        "Simples Nacional",
        "Lucro Presumido",
        "Lucro Real",
        # `_ALOC_CLASSE_LABELS` — a fixture emite os dois que a regra alcança.
        # `Ações BR`, `Fora do alvo` e `FIIs` ficam fora de propósito: a regra de
        # 2+ palavras capitalizadas não casa sigla nem preposição minúscula, e
        # entrada que a regra nunca acusaria é entrada morta (teste abaixo).
        "Renda Fixa",
        "Ações Int",
    }
)


# `nome_curto` de 2+ palavras ("Ana Clara") tem a MESMA forma de nome completo. É
# o substituto sancionado pela §D9, então é subtraído dinamicamente da varredura
# — nunca declarado em `_TERMOS_DE_DOMINIO`, que é vocabulário de domínio. Sem
# isso a única saída de quem vê a falha seria pôr nome de pessoa na allowlist.
def _nomes_curtos_da_familia() -> frozenset[str]:
    membros = _FAMILY.get("membros", {}).values()
    return frozenset(m["nome_curto"] for m in membros if m.get("nome_curto"))


def _sequencias_suspeitas(texto: str) -> list[str]:
    """Sequências de 2+ capitalizadas que não são termo de domínio nem `nome_curto`."""
    permitido = _TERMOS_DE_DOMINIO | _nomes_curtos_da_familia()
    return [s for s in _SEQUENCIA_RE.findall(texto) if s not in permitido]


@pytest.mark.parametrize("termo", sorted(_TERMOS_DE_DOMINIO))
def test_allowlist_so_tem_termo_que_a_regra_poderia_acusar(termo: str) -> None:
    """Entrada que o regex nunca casaria é entrada morta — engorda a allowlist e
    dá a impressão de que a guarda cobre mais do que cobre."""
    assert _SEQUENCIA_RE.fullmatch(termo), (
        f"`{termo}` não tem forma de 2+ palavras capitalizadas — a regra nunca o "
        "acusaria. Remova da allowlist."
    )


# A fixture tem de EXERCITAR o vocabulário, senão a allowlist é declarada no
# vácuo: foi assim que "Renda Fixa"/"Ações Int" ficaram fora dela por tanto
# tempo. Este teste exige ao menos um termo de cada família de campo no texto.
@pytest.mark.parametrize("termo", ["Simples Nacional", "Renda Fixa", "Ações Int"])
def test_fixture_exercita_o_vocabulario_de_dominio(termo: str, texto_emitido: str) -> None:
    """Cada família da allowlist tem representante no texto emitido."""
    assert termo in texto_emitido, (
        f"`{termo}` não aparece no texto emitido — a fixture deixou de produzir o "
        "campo, e a allowlist correspondente virou declaração sem teste."
    )


def test_texto_entregue_nao_tem_forma_de_nome_completo(texto_emitido: str) -> None:
    """2+ palavras capitalizadas em sequência é padrão de nome próprio."""
    suspeitas = _sequencias_suspeitas(texto_emitido)
    assert not suspeitas, (
        "sequência de palavras capitalizadas com forma de nome completo no "
        f"texto entregue: {sorted(set(suspeitas))}. Se for termo de domínio, "
        "declare em _TERMOS_DE_DOMINIO com a razão; se for nome de pessoa, "
        "troque por primeiro nome ou papel (ADR-319)."
    )


# ───────────────────── Braço C — regra estática ──────────────────────────

# Prosa cita em backticks (``nome_completo``) — o gate mede código, não
# documentação sobre o código; sem essa distinção o comentário que registra a
# remoção do padrão proibido dispara a própria regra (mesma armadilha da regra
# 5 de `dev/check_chart_conclusion_parity.py`).
#
# Campos PII da família que narrador nenhum pode ler. `nome_curto` NÃO está
# aqui: primeiro nome é o substituto sancionado. `nome_nascimento` (nome civil
# anterior, `member_name_resolver`) entra em A40.l4 — é da mesma classe de
# `nome_completo` e estava fora da lista e da família-sentinela.
_CAMPOS_PII_PROIBIDOS = (
    "nome_completo",
    "nome_nascimento",
    "local_nascimento",
    "cpf",
    "endereco",
)


def _leituras_do_campo(campo: str) -> list[str]:
    """Linhas que LEEM o campo (``"x"`` / ``'x'`` / ``.x``), não que o mencionam."""
    padrao = re.compile(rf"""(["']){campo}\1|\.{campo}\b""")
    return [
        f"{path.name}:{i}"
        for path in sorted(_NARRATIVAS_DIR.glob("*.py"))
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if padrao.search(line.split("#")[0])
    ]


@pytest.mark.parametrize("campo", _CAMPOS_PII_PROIBIDOS)
def test_nenhum_narrador_le_campo_pii(campo: str) -> None:
    """Regra estática: `pipeline/.../narrativas/*.py` não referencia campo PII."""
    ofensores = _leituras_do_campo(campo)
    assert not ofensores, (
        f"campo PII `{campo}` referenciado em narrador: {ofensores}. O texto "
        "entregue não cita nome completo, CPF, endereço nem local de "
        "nascimento (ADR-319)."
    )
