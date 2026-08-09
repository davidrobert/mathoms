"""ADR-362 — o que o `run_meta.md` AFIRMA sobre a proveniência do run.

Três critérios de aceite da A40.l32 falam do **entregável** ("reporta as duas
revisões", "diz `desconhecido` em destaque — nunca linha faltando", "nomeia o run
de origem"). Enquanto o bloco morou em `.claude/skills/`, as três mutações
correspondentes sobreviviam verdes: nenhuma suíte alcançava o arquivo.

`ancestry`/`commits_ahead_of` consultam o git com shas fabricados, que não
resolvem — daí `unreachable`/`None`, estável em qualquer checkout.
"""

from __future__ import annotations

from dev.run_provenance import (
    executor_line,
    partial_attribution_line,
    provenance_context,
    provenance_lines,
)

_A, _B = "aaaaaaaaaaaa", "bbbbbbbbbbbb"


def _row(stage: str, *, status: str = "completed", rev: str | None = _A) -> dict:
    return {"stage": stage, "status": status, "executor_revision": rev}


def test_execucao_mista_nomeia_as_duas_revisoes() -> None:
    """Mutação que mata: `executor_line` devolver só `revs[0]`."""
    linha = executor_line([_A, _B])

    assert _A in linha and _B in linha


def test_revisao_unica_nao_ganha_separador() -> None:
    assert executor_line([_A]) == f"- executor: `{_A}`"


def test_ausencia_e_linha_em_destaque_nunca_linha_faltando() -> None:
    """Mutação que mata: devolver `""` quando não há revisão — o bloco encolhe e
    o leitor lê "sem executor" como "não perguntamos", não como "não sabemos"."""
    linha = executor_line([])

    assert linha.strip()
    assert "desconhecido" in linha
    assert "MATHOMS_BUILD_SHA" in linha  # nomeia a causa acionável


def test_bloco_avisa_execucao_mista() -> None:
    """Mutação que mata: suprimir o aviso — duas revisões viram uma linha muda."""
    linhas = provenance_lines({}, [_row("reconcile"), _row("analyze", rev=_B)])

    assert any("execução mista" in ln for ln in linhas)


def test_bloco_nao_inventa_execucao_mista_com_revisao_unica() -> None:
    linhas = provenance_lines({}, [_row("reconcile"), _row("analyze")])

    assert not any("execução mista" in ln for ln in linhas)


def test_bloco_avisa_atribuicao_parcial_com_a_contagem() -> None:
    linhas = provenance_lines({}, [_row("a"), _row("b", rev=None)])

    parcial = [ln for ln in linhas if "atribuição parcial" in ln]
    assert parcial and "1 stage(s)" in parcial[0]


def test_bloco_nomeia_o_run_de_origem_sob_base_run_id() -> None:
    """Critério "escopo não mente" chegando ao entregável, não só à função pura."""
    linhas = provenance_lines({"base_run_id": "4b2c8e01-dead-beef"}, [_row("analyze")])

    assert any("herdado do run 4b2c8e01" in ln for ln in linhas)


def test_bloco_sempre_declara_que_reprodutibilidade_nao_e_garantida() -> None:
    """A cláusula de honestidade da ADR-362 não é condicional a nada."""
    for rows in ([], [_row("a")], [_row("a"), _row("b", rev=_B)]):
        assert any("NÃO garantida" in ln for ln in provenance_lines({}, rows))


def test_toda_linha_do_bloco_e_item_de_lista() -> None:
    """O bloco é colado num markdown existente; linha solta quebraria a lista."""
    linhas = provenance_lines({"incremental": True}, [_row("a"), _row("b", rev=None)])

    assert linhas and all(ln.startswith("- ") for ln in linhas)


def test_contexto_nao_colapsa_execucao_mista_num_escalar() -> None:
    """`executor_revision` singular é `None` sob mista — quem ler o escalar não
    pode receber uma das duas como se cobrisse o run."""
    ctx = provenance_context({}, [_row("a"), _row("b", rev=_B)])

    assert ctx["executor_revision"] is None
    assert ctx["executor_revisions"] == [_A, _B]
    assert ctx["execucao_mista"] is True


def test_contexto_conta_stages_terminais_sem_duplicar_reentrada() -> None:
    ctx = provenance_context({}, [_row("a"), _row("a"), _row("b")])

    assert ctx["escopo"]["stages_terminais"] == 2


def test_linha_de_atribuicao_parcial_conta_todos_os_ausentes() -> None:
    linha = partial_attribution_line([_row("a"), _row("b", rev=None), _row("c", rev=None)])

    assert "2 stage(s)" in linha
