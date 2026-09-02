"""Controle positivo da guarda anti-vacuo dos cross-checks da rodada unificada.

A regra vem do §10 do `U2` (item 2) e reprovou de novo no `U3`: um check que
compara **zero** celulas e imprime ✅ — ou que imprime 647 divergencias sobre uma
intersecao vazia — nao e veredito. A guarda mora no FORMATO de saida, e um check
sem controle positivo que dispara nao pode ser confiado (§10 `U2`, item 1).
"""

from __future__ import annotations

import ast
import io
import pathlib
from contextlib import redirect_stdout

import pytest

from dev._unified_xchecks.base import _cents, veredito


def _saida(n_comparado: int, n_esperado: int, divergentes: int, n_falsificavel=None) -> str:
    """`n_falsificavel` default = `n_comparado`: o caso em que TODA a populacao
    examinada podia reprovar, que e o unico em que o par antigo bastava."""
    buf = io.StringIO()
    alvo = n_comparado if n_falsificavel is None else n_falsificavel
    with redirect_stdout(buf):
        veredito("CTRL", n_comparado, n_esperado, divergentes, n_falsificavel=alvo)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("n_comparado", "n_esperado", "divergentes", "esperado"),
    [
        (0, 10, 0, "INAPLICAVEL"),
        (3, 10, 0, "INAPLICAVEL"),
        (10, 10, 0, "FECHA"),
        (10, 10, 2, "DIVERGE"),
        (0, 10, 647, "INAPLICAVEL"),
    ],
)
def test_veredito_discrimina(n_comparado, n_esperado, divergentes, esperado):
    assert esperado in _saida(n_comparado, n_esperado, divergentes)


def test_vacuo_nunca_sai_verde():
    """O caso que enganou o `U3`: divergencia alta sobre populacao vazia."""
    saida = _saida(0, 1540, 647)
    assert "FECHA" not in saida and "DIVERGE" not in saida


def test_par_de_denominadores_sempre_publicado():
    """`n_comparado` e `n_esperado` na MESMA linha do veredito, em todo caso."""
    for args in ((0, 10, 0), (3, 10, 0), (10, 10, 0), (10, 10, 2)):
        saida = _saida(*args)
        assert f"n_comparado={args[0]}" in saida
        assert f"n_esperado={args[1]}" in saida


# ---------------------------------------------------------------------------
# Terceiro denominador (`LC9-04` · lane A42.l24)
#
# O par `(n_comparado, n_esperado)` responde COBERTURA e nao responde PODER. O
# `X4` do `U5` tinha cobertura cheia (10/10) e poder 1/10, e publicou ✅.
# ---------------------------------------------------------------------------


def test_populacao_sem_poder_discriminante_nunca_sai_verde():
    """CONTROLE POSITIVO do eixo da lane: cobertura cheia, zero falsificaveis."""
    saida = _saida(10, 10, 0, n_falsificavel=0)
    assert "INAPLICAVEL" in saida
    assert "FECHA" not in saida and "DIVERGE" not in saida


def test_um_unico_falsificavel_ainda_e_veredito():
    """`n=1` PODE reprovar, entao FECHA e verdadeiro — e a linha publica que a
    superficie com poder era 10% do examinado."""
    saida = _saida(10, 10, 0, n_falsificavel=1)
    assert "FECHA" in saida
    assert "n_falsificavel=1" in saida and "10% do examinado" in saida


def test_terceiro_denominador_sempre_publicado():
    for args in ((0, 10, 0, 0), (3, 10, 0, 3), (10, 10, 0, 10), (10, 10, 2, 2)):
        assert f"n_falsificavel={args[3]}" in _saida(*args)


def test_n_falsificavel_e_keyword_only_e_obrigatorio():
    """Guarda que fica opcional fica inerte: o autor do check TEM de responder."""
    with pytest.raises(TypeError):
        veredito("CTRL", 10, 10, 0)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        veredito("CTRL", 10, 10, 0, 10)  # type: ignore[misc]


def test_cents_nao_confunde_bool_com_numero():
    assert _cents(True) is None
    assert _cents(None) is None
    assert _cents("1.23") == 123
    assert _cents(0) == 0


# ---------------------------------------------------------------------------
# X5 — poder discriminante (`PV12-04`, lane A42.l21)
#
# O predicado antigo marcava os MESMOS 3 stages em `U2`/`U3`/`U4` sob o rotulo
# unico "contrato falso": nao podia ficar verde, logo nao informava nada. Estes
# controles cobrem os dois lados — o cenario saudavel PODE sair verde, e cada
# causa que sustenta o verde e falsificavel isoladamente.
# ---------------------------------------------------------------------------

_SKIP = {"skipped": True, "reason": "No unprocessed documents for LLM extraction"}


def _cenario_saudavel() -> tuple[list, dict]:
    """Reproduz o run 7d860f0b medido no `U4`: 3 causas benignas distintas."""
    logs = [
        ("unlock_documents", "completed", {"success": True}),
        ("extract_with_llm", "completed", dict(_SKIP)),
        ("analyze_finances", "completed", {"success": True}),
        ("generate_narratives", "completed", {"success": True}),
        ("validate_cross", "completed", {"success": True}),
    ]
    return logs, {"analyze_finances": 1}


def _classes(diag: dict) -> dict[str, str]:
    return {linha[0]: linha[4] for linha in diag["linhas"]}


def test_fixture_separa_as_tres_causas():
    """Antes do gate: a fixture DISCRIMINA. Colapsar estas 3 em 1 era o PV12-04."""
    from dev._unified_xchecks.execucao import classificar

    classes = _classes(classificar(*_cenario_saudavel()))
    tres = [classes[s] for s in ("extract_with_llm", "generate_narratives", "validate_cross")]
    assert len(set(tres)) == 3, tres


def test_cenario_saudavel_pode_sair_verde():
    """O que o check antigo nao conseguia: ausencia de ofensor."""
    from dev._unified_xchecks.execucao import classificar

    diag = classificar(*_cenario_saudavel())
    assert diag["ofensores"] == {} and diag["vencidas"] == {}
    assert diag["n_comparado"] == diag["n_esperado"] > 0
    assert "FECHA" in _saida(diag["n_comparado"], diag["n_esperado"], 0)


def test_quarto_ofensor_aparece_nomeado():
    """CONTROLE POSITIVO da lane: stage que promete artefato e nao entrega."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs.append(("extract_statements", "completed", {"success": True}))
    diag = classificar(logs, por_stage)
    assert "extract_statements" in diag["ofensores"]
    assert "DIVERGE" in _saida(diag["n_comparado"], diag["n_esperado"], len(diag["ofensores"]))


def test_sem_carimbo_de_skip_o_mesmo_stage_reprova():
    """O ramo do skip e load-bearing: tirar o carimbo vira ofensor."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[1] = ("extract_with_llm", "completed", {"success": True})
    assert "extract_with_llm" in classificar(logs, por_stage)["ofensores"]


def _ler_mutado(alvo: str, fonte: str):
    """Leitor que substitui a fonte de UM arquivo e delega o resto ao real."""
    from dev._unified_xchecks.execucao import _ler_fonte

    return lambda rel: fonte if alvo in rel else _ler_fonte(rel)


def test_read_only_com_write_na_fonte_vence_a_dispensa():
    """Se `validate_cross` ganhar writer, a dispensa deixa de valer."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    ler = _ler_mutado("validate_cross", "store.write('validate_cross', k, v)\n")
    assert "validate_cross" in classificar(logs, por_stage, ler=ler)["vencidas"]


def test_redirecao_para_outro_alvo_vence_a_dispensa():
    """A declaracao nomeia `analyze_finances`; fonte que escreve noutro lugar reprova."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    ler = _ler_mutado("generate_narratives", "store.write('outra_key', k, v)\n")
    assert "generate_narratives" in classificar(logs, por_stage, ler=ler)["vencidas"]


def test_redirecao_sem_artefato_no_alvo_vence_a_dispensa():
    """Fonte certa, run vazio: o merge nao aconteceu neste run."""
    from dev._unified_xchecks.execucao import classificar

    logs, _ = _cenario_saudavel()
    assert "generate_narratives" in classificar(logs, {})["vencidas"]


def test_dispensa_de_stage_que_produziu_artefato_proprio_esta_vencida():
    """Igualdade de conjunto no outro sentido: a dispensa deixou de ser necessaria."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    por_stage["validate_cross"] = 1
    assert "validate_cross" in classificar(logs, por_stage)["vencidas"]


def test_evidencia_ilegivel_nao_sai_verde():
    """Ausencia nao se prova com arquivo sumido — instrumento quebrado e INAPLICAVEL."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    diag = classificar(logs, por_stage, ler=lambda _rel: None)
    assert diag["n_comparado"] < diag["n_esperado"]
    assert "INAPLICAVEL" in _saida(diag["n_comparado"], diag["n_esperado"], 0)


def test_declaracao_bate_com_a_fonte_real():
    """`literal == sistema`: o ground truth e autorado, o cross-check e que mede."""
    from dev._unified_xchecks.execucao import DISPENSAS, _ler_fonte, _viola

    for stage, d in DISPENSAS.items():
        src = _ler_fonte(d.evidencia)
        assert src is not None, f"{stage}: evidencia sumiu ({d.evidencia})"
        alvo = {d.escreve_em: 1} if d.escreve_em else {}
        assert _viola(d, src, alvo) is None, f"{stage}: {_viola(d, src, alvo)}"


def test_fonte_sumida_le_None_e_nao_string_vazia():
    """A armadilha da dispensa READ-ONLY: ela afirma AUSENCIA de write, e ""
    tem zero writes. Arquivo sumido tem de virar `None` (⇒ INDETERMINADO),
    nunca fonte vazia que satisfaz a declaracao de graca."""
    from dev._unified_xchecks.execucao import _ler_fonte

    assert _ler_fonte("scripts/nao_existe_este_arquivo_xyz.py") is None
    assert _ler_fonte("scripts/validate_cross.py")


def test_zero_trabalho_na_outra_grafia_tambem_e_benigno():
    """5 dos 25 runs do dogfood saem por aqui: sem `skipped`, com `total_processed: 0`."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[1] = ("extract_with_llm", "completed", {"success": True, "total_processed": 0})
    diag = classificar(logs, por_stage)
    assert diag["ofensores"] == {}
    assert _classes(diag)["extract_with_llm"] == "SEM-TRABALHO"


def test_zero_processado_com_erro_nao_e_zero_trabalho():
    """`total_processed: 0` com erros nao e "nada a fazer" — e nao entregar."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[1] = ("extract_with_llm", "completed", {"total_processed": 0, "total_errors": 3})
    assert "extract_with_llm" in classificar(logs, por_stage)["ofensores"]


# ---------------------------------------------------------------------------
# X5 — o denominador esconde o stage sob suspeita (`LC9-05`, lane A42.l24)
#
# `n_esperado` saia de `len(completos)`: stage fora de `completed` sumia dos DOIS
# lados e o `U5` leu `17/17` num run de 18 — o excluido era `analyze_finances` em
# `needs_review`, dono do payload que carregava a regressao daquela rodada.
# ---------------------------------------------------------------------------


def test_stage_nao_completed_entra_no_denominador():
    """CONTROLE POSITIVO: o run do `U5`, com o stage sob suspeita fora do predicado."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    logs[2] = ("analyze_finances", "needs_review", {"success": False})
    diag = classificar(logs, por_stage)
    assert diag["n_esperado"] == len(logs), "o nao-completed tem de contar no esperado"
    assert diag["fora_do_predicado"] == ["analyze_finances"]


def test_exclusao_por_status_sai_no_veredito_nao_no_denominador():
    """A exclusao e legitima; escondida no denominador, nao."""
    from dev._unified_xchecks.execucao import _fora, classificar

    logs, por_stage = _cenario_saudavel()
    logs[2] = ("analyze_finances", "needs_review", {"success": False})
    nomeada = _fora(classificar(logs, por_stage))
    assert "analyze_finances" in nomeada and "needs_review" in nomeada


def test_sem_o_stage_suspeito_o_denominador_encolhe():
    """Falsifica o teste acima: tirar a linha do log muda `n_esperado`. Sem isto,
    `n_esperado == len(logs)` passaria sobre qualquer implementacao."""
    from dev._unified_xchecks.execucao import classificar

    logs, por_stage = _cenario_saudavel()
    completo = classificar(logs, por_stage)["n_esperado"]
    assert classificar(logs[:-1], por_stage)["n_esperado"] == completo - 1


def test_run_sem_stage_com_poder_e_inaplicavel():
    """Todo stage skipado ⇒ o predicado nao podia reprovar ninguem."""
    from dev._unified_xchecks.execucao import classificar

    logs = [("extract_with_llm", "completed", dict(_SKIP))]
    diag = classificar(logs, {})
    assert diag["n_falsificavel"] == 0
    assert "INAPLICAVEL" in _saida(
        diag["n_comparado"], diag["n_esperado"], 0, diag["n_falsificavel"]
    )


def test_stage_que_entregou_conta_como_falsificavel():
    """Simetria do teste acima: `OK` esteve em risco de ser ofensor, logo conta."""
    from dev._unified_xchecks.execucao import classificar

    diag = classificar(*_cenario_saudavel())
    assert diag["n_falsificavel"] > 0


# ---------------------------------------------------------------------------
# X4 — a superficie carimbada pelo backend nao podia reprovar (`LC9-04`)
# ---------------------------------------------------------------------------


def _parecer_com_ancora(valor: str = "R$ 83.869,92") -> dict:
    return {
        "riscos": [
            {
                "evidencia": f"exposicao_cambial.total_brl={valor}; tier=indeterminado.",
                "ancoras": [{"path": "$.exposicao_cambial.total_brl", "valor_renderizado": valor}],
            }
        ]
    }


def test_carimbado_sai_do_denominador_e_autoral_fica():
    """A repartição do `U5`: 2 ocorrências do MESMO valor, 1 carimbada, 1 autoral."""
    from dev._unified_xchecks.ancoragem import _paths_carimbados, _walk_literais

    par = _parecer_com_ancora()
    ocorrencias = _walk_literais(par)
    carimbados = _paths_carimbados(par, lambda _p: True)
    autorais = [p for p, _c in ocorrencias if p not in carimbados]
    assert len(ocorrencias) == 2, ocorrencias
    assert autorais == [".riscos[0].evidencia"]


def test_ancora_cujo_path_nao_resolve_continua_autoral():
    """`_resolve_ancora` so sobrescreve quando `found`; sem isso o numero e do
    MODELO (`valor_renderizado` nao e `SkipJsonSchema`) e tem de ser julgado."""
    from dev._unified_xchecks.ancoragem import _paths_carimbados

    assert _paths_carimbados(_parecer_com_ancora(), lambda _p: False) == set()


def test_subtracao_e_por_ocorrencia_nao_por_valor():
    """CONTROLE POSITIVO: subtrair por valor apagaria a copia autoral do mesmo numero."""
    from dev._unified_xchecks.ancoragem import _paths_carimbados, _walk_literais

    par = _parecer_com_ancora()
    cents = {c for _p, c in _walk_literais(par)}
    assert len(cents) == 1, "os dois literais SAO o mesmo valor — e por isso o teste existe"
    carimbados = _paths_carimbados(par, lambda _p: True)
    assert len([p for p, _c in _walk_literais(par) if p not in carimbados]) == 1


def test_horizontes_com_ancora_cobrem_o_produtor():
    """Paridade com `stamp_ancora_values`: horizonte novo com ancora que o check
    nao conheca voltaria a inflar o denominador em silencio."""
    from dev._unified_xchecks.ancoragem import _HORIZONTES_COM_ANCORA

    fonte = (
        pathlib.Path(__file__).resolve().parent.parent
        / "backend/app/services/parecer_finalization.py"
    ).read_text(encoding="utf-8")
    trecho = fonte.split("def stamp_ancora_values")[1].split("\ndef ")[0]
    for horizonte in _HORIZONTES_COM_ANCORA:
        assert horizonte in trecho, f"{horizonte} nao aparece no estampador"


# ---------------------------------------------------------------------------
# X7 — teto e emissor contam populacoes distintas (`PV13-10`)
# ---------------------------------------------------------------------------


def test_teto_do_schema_nao_governa_o_campo_do_emissor():
    """CONTROLE POSITIVO: o `maximum: 6` sobre `_meta.tool_iterations` era a
    declaracao errada — o campo conta invocacoes, o cap conta round-trips. Um run
    real publicou 19 sem defeito nenhum."""
    import json

    schema = json.loads(
        (
            pathlib.Path(__file__).resolve().parent.parent
            / "config/schemas/parecer_planejador.schema.json"
        ).read_text(encoding="utf-8")
    )
    campo = schema["properties"]["_meta"]["properties"]["tool_iterations"]
    assert "maximum" not in campo, "teto sobre populacao que o emissor nao conta"
    assert "TELEMETRIA" in campo["description"]


def test_modelo_sem_tools_torna_a_populacao_do_teto_vazia():
    """Oraculo por ASSINATURA: `LLMService.call` nao aceita `tools`, entao
    round-trip iniciado pelo modelo e estruturalmente 0. Ligar tools inverte isto
    sozinho — foi inferir afordance de docstring que produziu o `RV4-43`."""
    from dev._unified_xchecks.teto import _modelo_tem_tools

    assert _modelo_tem_tools() is False


def _nome_chamado(no) -> str | None:
    alvo = no.func
    return alvo.id if isinstance(alvo, ast.Name) else getattr(alvo, "attr", None)


def _sem_n_falsificavel(arquivo: pathlib.Path) -> list[str]:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    chamadas = [n for n in ast.walk(arvore) if isinstance(n, ast.Call)]
    return [
        f"{arquivo.name}:{n.lineno}"
        for n in chamadas
        if _nome_chamado(n) == "veredito" and not any(k.arg == "n_falsificavel" for k in n.keywords)
    ]


# CONTROLE ESTATICO — o que faltava quando o guard ganhou o 3o denominador.
# X2/X3/X3b vivem em `razao.py` e NAO tem teste de execucao (precisam de DB e de
# um run real), entao o `TypeError` da assinatura so apareceria no meio da
# rodada, DEPOIS da tabela impressa e antes do veredito. Foi assim que os tres
# quebraram em `main` (achado do closeout da A42.l24). Keyword-only obriga o
# AUTOR a responder; este teste obriga o REPO a nao esquecer call-site.
def test_todo_call_site_de_veredito_declara_n_falsificavel():
    """Nenhum call-site de `veredito(` no pacote omite `n_falsificavel`."""
    raiz = pathlib.Path(__file__).resolve().parent.parent / "dev/_unified_xchecks"
    faltando = [alvo for arq in sorted(raiz.glob("*.py")) for alvo in _sem_n_falsificavel(arq)]
    assert not faltando, f"call-site de veredito sem n_falsificavel: {faltando}"


def test_o_controle_estatico_pega_o_call_site_que_quebrou():
    """Falsificador do teste acima: sobre a forma que estava em `main`, ele acusa."""
    quebrado = ast.parse('veredito("X3", total, esperado, len(div))\n')
    chamada = next(n for n in ast.walk(quebrado) if isinstance(n, ast.Call))
    assert not any(k.arg == "n_falsificavel" for k in chamada.keywords)


def test_razao_impossivel_sai_nomeada_e_nao_como_porcentagem():
    """CONTROLE POSITIVO: o `X2` passou célula (2289) contra denominador de balde
    (3) e imprimiu `76300% do examinado` — número absurdo é lido como ruído e some."""
    saida = _saida(3, 3, 0, n_falsificavel=2289)
    assert "UNIDADE DIVERGE" in saida and "%" not in saida.split("n_falsificavel=")[1]
