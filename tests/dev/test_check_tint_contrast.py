"""Gate de contraste texto-sobre-tint (dev/check_tint_contrast.py).

Trava: (a) o repo real passa; (b) a aritmética WCAG bate com valores de
referência conhecidos; (c) alias (`warning`↔`alert`) não escapa do pareamento;
(d) o par `-on-tint` não é confundido com "cores diferentes"; (e) um par que
reprova é de fato reportado; (f) as três sintaxes de tint são pareadas.

Os itens (c) e (f) são o que o teste existe para proteger, e pelo mesmo motivo:
os dois modos de ficar verde **por não olhar** — o caro, porque (a) continua
passando. (c) foi hipótese; (f) foi medido — o ataque de 2026-08-13 achou 7
call-sites reprovando (1,86:1 entre eles) que só escreviam o tint como
`bg-[var(--X)]/15` em vez de `bg-[color-mix(…)]`.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ctc", _REPO / "dev" / "check_tint_contrast.py")
assert _spec and _spec.loader
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)


def test_repo_real_passa_sob_o_gate() -> None:
    assert ctc.main() == 0


@pytest.mark.parametrize(
    ("fg", "bg", "esperado"),
    [
        ("#FFFFFF", "#000000", 21.0),
        ("#000000", "#FFFFFF", 21.0),
        ("#FFFFFF", "#FFFFFF", 1.0),
    ],
)
def test_contraste_bate_com_referencia(fg: str, bg: str, esperado: float) -> None:
    assert ctc.contrast_ratio(fg, bg) == pytest.approx(esperado, abs=0.01)


def test_composite_em_0_e_100_pct() -> None:
    assert ctc.composite("#FF0000", "#FFFFFF", 100) == "#FF0000"
    assert ctc.composite("#FF0000", "#FFFFFF", 0) == "#FFFFFF"


@pytest.mark.parametrize(
    ("fg", "bg"),
    [
        ("semantic-warning", "semantic-alert"),
        ("semantic-danger", "semantic-loss"),
        ("semantic-success", "semantic-gain"),
        ("semantic-alert-on-tint", "semantic-alert"),
        ("semantic-alert-on-tint", "semantic-warning"),
    ],
)
def test_alias_e_on_tint_continuam_no_conjunto_medido(fg: str, bg: str) -> None:
    """Alias e par corrigido continuam sendo MEDIDOS — sair do conjunto seria
    ficar verde por não olhar."""
    assert ctc.is_same_color_pair(fg, bg)


def test_cores_genuinamente_diferentes_ficam_de_fora() -> None:
    assert not ctc.is_same_color_pair("semantic-gain", "semantic-loss")
    assert not ctc.is_same_color_pair("surface-foreground", "surface-border")


@pytest.mark.parametrize(
    ("forma", "linha"),
    [
        (
            "arbitrary/transparent",
            'className="bg-[color-mix(in_srgb,var(--semantic-alert)_15%,transparent)]'
            ' text-[var(--semantic-alert)]"',
        ),
        (
            "substrato declarado",
            'className="bg-[color-mix(in_srgb,var(--semantic-alert)_15%,var(--surface-muted))]'
            ' text-[var(--semantic-alert)]"',
        ),
        (
            "opacity modifier",
            'amarelo: "bg-[var(--semantic-alert)]/15 text-[var(--semantic-alert)]",',
        ),
    ],
)
def test_as_tres_sintaxes_de_tint_sao_pareadas(forma: str, linha: str) -> None:
    """Sintaxe nova é o modo de falha desta classe: a mesma cor, o mesmo pixel e
    o mesmo defeito, escritos de outro jeito, saíam do conjunto medido."""
    pares = ctc._pairs_in_line("fake.tsx:1", linha)
    assert [(p.fg_token, p.bg_token, p.pct) for p in pares] == [
        ("semantic-alert", "semantic-alert", 15)
    ], forma


def test_substrato_declarado_e_usado_no_lugar_do_card() -> None:
    """`color-mix(…, var(--Y))` é opaco: compõe contra `--Y`, não contra o card
    nem contra o fundo do pai."""
    linha = 'className="bg-[color-mix(in_srgb,var(--semantic-gain)_8%,var(--surface-muted))]"'
    assert ctc._tints_in_line(linha) == [("semantic-gain", 8, "surface-muted")]


def test_pares_nomeados_cobrem_o_que_o_pareamento_por_linha_nao_alcanca() -> None:
    """Duas famílias entram como par nomeado: ícone em elemento filho (1.4.11 =
    3:1) e tint no pai com o texto num filho (texto = 4,5:1)."""
    pares = ctc.named_pairs()
    assert len(pares) == len(ctc.NAMED_PAIRS)
    limiares = {p.min_ratio for p in pares}
    assert limiares == {ctc.AA_NAO_TEXTO, ctc.AA_TEXTO_PEQUENO}


def test_entrada_nomeada_com_texto_stale_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Par nomeado cujo call-site trocou de token tem de falhar, não medir
    fantasma — allowlist que sobrevive ao próprio motivo é fail-open."""
    monkeypatch.setattr(
        ctc,
        "NAMED_PAIRS",
        [
            (
                "components/report/provenance/ProvenancePopover.tsx",
                "semantic-gain-on-tint",
                "semantic-alert",
                15,
                "surface-card",
                3.0,
            )
        ],
    )
    with pytest.raises(SystemExit, match="não usa mais"):
        ctc.named_pairs()


def test_entrada_nomeada_com_percentual_stale_falha(monkeypatch: pytest.MonkeyPatch) -> None:
    """Checar só a cor do texto deixava o percentual apodrecer: o call-site vira
    30% e o gate segue reportando o contraste de 15%, que ninguém pinta."""
    monkeypatch.setattr(
        ctc,
        "NAMED_PAIRS",
        [
            (
                "components/report/provenance/ProvenancePopover.tsx",
                "semantic-alert-on-tint",
                "semantic-alert",
                30,
                "surface-card",
                3.0,
            )
        ],
    )
    with pytest.raises(SystemExit, match="não declara tint"):
        ctc.named_pairs()


def test_par_que_reprova_e_reportado() -> None:
    """Cor base sobre o próprio tint de 15% — o defeito que criou o gate."""
    pair = ctc.TintPair("fake.tsx:1", "semantic-alert", "semantic-alert", 15)
    tokens = {"semantic-alert": "#F4A261", "surface-card": "#FFFFFF"}
    msg = ctc._violation(pair, "light", tokens)
    assert msg is not None
    assert "1.86:1" in msg
    assert "--semantic-alert-on-tint" in msg


def test_par_corrigido_nao_e_reportado() -> None:
    pair = ctc.TintPair("fake.tsx:1", "semantic-alert-on-tint", "semantic-alert", 15)
    tokens = {
        "semantic-alert": "#F4A261",
        "semantic-alert-on-tint": "#984C11",
        "surface-card": "#FFFFFF",
    }
    assert ctc._violation(pair, "light", tokens) is None


def test_token_sem_hex_falha_em_vez_de_passar_calado() -> None:
    """Token ausente do tema tem de virar falha: silenciar seria fail-open."""
    pair = ctc.TintPair("fake.tsx:1", "inexistente", "semantic-alert", 15)
    msg = ctc._violation(pair, "dark", {"semantic-alert": "#FDBA74", "surface-card": "#1E293B"})
    assert msg is not None
    assert "não consegue medir" in msg
