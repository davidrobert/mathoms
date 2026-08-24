"""Precisão dos predicados do `check_closure.py` (skill `lane-closeout`, #1343).

A primeira rodada completa da ferramenta — 33 lanes da A40, PR #1344 — mediu
**64% de falso-positivo** no `CLOSE-BLOCK-05`, contra o critério de ≤20% que o
próprio `SKILL.md` declara. Duas causas, ambas reproduzidas aqui: a palavra de
rota apenas coabitava a linha (não governava o wikilink), e texto aposentado por
emenda datada (`~~riscado~~`) continuava contando como rota viva.

Mesmo motivo do `test_run_provenance.py`: enquanto o código morar em
`.claude/skills/`, nenhuma suíte o alcança e a mutação sobrevive verde.

Os `lanes` são fabricados de propósito — teste que lê a vault viva vira vermelho
quando alguém shipa uma lane, que é ruído, não sinal.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / ".claude/skills/lane-closeout/references/check_closure.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("check_closure", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_closure"] = module
    spec.loader.exec_module(module)
    return module


cc = _load()


def _lane(lane_id: str, status: str, text: str = ""):
    path = Path("docs/sprint/A40/lanes/fabricada.md")
    return cc.Lane(lane_id, path, {"status": status, "sprint": "A40"}, text)


VIVA, MORTA = "A40.viva", "A40.morta"
LANES = {VIVA: _lane(VIVA, "in_progress"), MORTA: _lane(MORTA, "shipped")}


# --------------------------------------------------------------------------
# CLOSE-BLOCK-01 — deferimento órfão em lane fechada
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "texto", "status", "acende"),
    [
        ("órfão puro", "## Deferimento (2026-08-09)\n\n- Piso a aporte zero.\n", "shipped", True),
        (
            "roteado p/ lane viva",
            f"## Deferimento\n\nVira carga da [[{VIVA}]].\n",
            "shipped",
            False,
        ),
        ("roteado p/ lane morta", f"## Deferimento\n\nPassa para [[{MORTA}]].\n", "shipped", True),
        ("planejamento", "## Dependências e follow-up\n\n- Sem deps.\n", "shipped", False),
        (
            "meta sobre deferir",
            "## Por que existe uma lane e não só o §Deferimentos da ADR\n\n- x\n",
            "shipped",
            False,
        ),
        ("owner-gated", "## Fora de escopo\n\nReligar é owner-gated.\n", "shipped", False),
        ("lane ainda aberta", "## Deferimento\n\n- item solto\n", "in_progress", False),
    ],
)
def test_deferimento_orfao(nome: str, texto: str, status: str, acende: bool) -> None:
    """Mutação que mata: aceitar qualquer heading com `deferi`, ou ignorar a rota."""
    got = cc.check_orphan_deferral(_lane("A40.alvo", status, texto), LANES)
    assert bool(got) is acende, nome


# --------------------------------------------------------------------------
# CLOSE-BLOCK-05 — a palavra de rota precisa GOVERNAR o wikilink
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "linha", "roteia"),
    [
        ("dono explícito", f"   Dono: [[{MORTA}]] PR2.", True),
        ("candidato adjacente", f"candidato segue [[{MORTA}]].", True),
        (
            "termo técnico depois do link",
            f"**Equivalência com o carrier da [[{MORTA}]]:** todo candidato colapsável",
            False,
        ),
        (
            "owner depois do link",
            f"**7. Onde mora o tripwire de revert da [[{MORTA}]], e quem é o owner?**",
            False,
        ),
        (
            "proveniência com `pela`",
            f"Registrada na [[ADR-306]] pela [[{MORTA}]] para o próximo revisor",
            False,
        ),
        (
            "precedente citado",
            f"  [[{MORTA}]], que nasceu `A41.l1` e foi promovida por decisão do dono",
            False,
        ),
        (
            "relato de roteamento antigo",
            f"Roteado em **duas** lanes, com corte em **US$ 0 | US$ 26**: [[{MORTA}]] é",
            False,
        ),
        # Medido em 2026-08-17 no closeout da A40.l64: assim que a A40.l5 virou
        # `shipped`, estes 3 acenderam CLOSE-BLOCK-05 — 3 de 3, num código de
        # severidade ALTA. O gatilho é `dono` dentro de "§Decisão do dono", que
        # CITA uma decisão; "Dono: [[X]]" ATRIBUI. O caso "precedente citado"
        # acima não pegava porque põe a frase DEPOIS do wikilink, fora da janela.
        (
            "decisão do dono citada como precedente (_README A40)",
            f"nenhum filtro cobre as duas direções (precedente: §Decisão do dono da [[{MORTA}]]).",
            False,
        ),
        (
            "decisão do dono citada como precedente (lane A40.l25)",
            f"cobre as duas direções (precedente: a §Decisão do dono da [[{MORTA}]]). Custo",
            False,
        ),
        (
            "liberação histórica no mesmo par",
            f"🔓 **Liberada em 2026-08-07 (decisão do dono)**, no mesmo par que a [[{MORTA}]].",
            False,
        ),
        (
            "atribuição de dono continua sendo rota",
            f"O item fica sem destino até alguém assumir — dono: [[{MORTA}]]",
            True,
        ),
    ],
)
def test_rota_governa_o_wikilink(nome: str, linha: str, roteia: bool) -> None:
    """Mutação que mata: voltar a `ROUTE_WORD_RE.search(line)` sobre a linha inteira."""
    assert cc._routes_to(linha, MORTA) is roteia, nome


def test_texto_riscado_nao_e_rota_viva() -> None:
    """Mutação que mata: remover o strip de `~~…~~` antes de medir a rota."""
    riscada = f"~~Dono: [[{MORTA}]] PR2.~~ Órfã desde 2026-08-09: sem dono."
    assert cc._routes_to(riscada, MORTA) is True
    assert cc._routes_to(cc.STRIKETHROUGH_RE.sub("", riscada), MORTA) is False


def test_risco_multilinha_tambem_neutraliza() -> None:
    """Mutação que mata: `sub` linha-a-linha — o risco real da A40 cruza 3 linhas."""
    texto = f"~~Candidato natural a hospedar: [[{MORTA}]],\nque já é a lane de gate~~\nSem dono."
    masked = cc._mask_struck(texto)
    assert len(masked.splitlines()) == 3, "offsets e linhas têm de sobreviver ao mask"
    assert not any(cc._routes_to(line, MORTA) for line in masked.splitlines())


def test_paragrafo_que_declara_o_fechamento_nao_acusa() -> None:
    """Mutação que mata: medir só a linha — a honestidade mora no parágrafo."""
    linhas = [
        "- **Base da cascata** — residual da [[A40.l4]],",
        f"  fecha a Pendência 11. Dono do arquivo é a [[{MORTA}]]",
        "  (`shipped`). **Fora da A40 por falta de dono vivo.**",
    ]
    assert cc._routes_to(linhas[1], MORTA) is True, "a linha sozinha parece rota viva"
    assert cc.SELF_CLOSED_RE.search(cc._paragraph_at(linhas, 1)), "o parágrafo já declara"


def test_contador_de_lanes_extrai_o_numero_declarado() -> None:
    """Mutação que mata: regex que casa `## Lanes` sem capturar o grupo."""
    assert cc.LANE_COUNT_RE.search("## Lanes (32)\n").group(2) == "32"
    assert cc.LANE_COUNT_RE.search("## Lanes\n") is None


# A forma antiga (`\((\d+)\)`) exigia `)` logo após os dígitos e devolvia None no
# cabeçalho real da A40 — `match is None` faz `check_lane_counter` RETORNAR [], então
# o check falhava ABERTO. Medido em 2026-08-24: contador dizia 75 com 76 no disco e a
# camada 1 vinha verde. Este teste mata a volta dessa forma (A40.l59).
def test_contador_casa_cabecalho_com_texto_dentro_dos_parenteses() -> None:
    """Mutação que mata: exigir `)` colado ao número — o check passa a falhar aberto."""
    real = "## Lanes (76 no disco · 76 nesta tabela — ver nota ao fim)\n"
    match = cc.LANE_COUNT_RE.search(real)
    assert match is not None, "regex estrito aqui devolve None e o check passa calado"
    assert match.group(2) == "76"


# Incidente 2026-08-21: os 2 CLOSE-BLOCK reais moravam em linha de achado de
# `docs/_MOC/PIPELINE-REVIEWS-active.md` — fora do universo, a camada 3 nunca
# releu o registro e o closeout veio verde-falso.
def test_citers_of_enxerga_registro_moc(tmp_path, monkeypatch) -> None:
    """Mutação que mata: remover `MOC.glob('*-active.md')` do universo de citadores."""
    sprint = tmp_path / "docs" / "sprint" / "A40"
    moc = tmp_path / "docs" / "_MOC"
    sprint.mkdir(parents=True)
    moc.mkdir(parents=True)
    (sprint / "_README.md").write_text("tabela cita [[A40.l7]]\n", encoding="utf-8")
    (moc / "PIPELINE-REVIEWS-active.md").write_text(
        "| RV4-12 — defeito | procede-aberto | [[A40.l7]] |\n", encoding="utf-8"
    )
    (moc / "00-INDEX.md").write_text("[[A40.l7]] em MOC navegacional\n", encoding="utf-8")
    monkeypatch.setattr(cc, "SPRINT", tmp_path / "docs" / "sprint")
    monkeypatch.setattr(cc, "MOC", moc)
    citers = cc.citers_of("A40.l7")
    assert any("PIPELINE-REVIEWS-active" in c for c in citers), "registro MOC fora do universo"
    assert any("_README" in c for c in citers), "universo de sprint não pode regredir"
    assert not any("00-INDEX" in c for c in citers), "só *-active.md entra — índice não é registro"
