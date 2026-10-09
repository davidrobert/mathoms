"""O prompt renderizado do parecer é pinado no arquivo cuja versão governa (ADR-199 §Emenda 2026-10-09)."""

# Byte do prompt muda ⇒ pin muda ⇒ arquivo versionado muda ⇒ o gate W2-T05
# (dev/check_prompt_version_bumped.py, no pre-commit e no job Lint do CI) cobra o bump.
# O system é pinado em `SYSTEM_PROMPT_SHA256`, ao lado de `PROMPT_VERSION`: é a versão
# que separa a telemetria (drift monitor, `riscos_truncados`), e a persona abre o system.
# O user, por regime de eviction, em `user_prompt_sha256` do manifest. Refactor que não
# muda byte não toca pin nem cobra bump — bump sem necessidade zera a amostra do drift.
#
# Fixture CONGELADA: gerada uma vez de `make_dogfood_like_e5`, enriquecida até cobrir
# todo path do manifest (menos `AUSENTES_DELIBERADOS`) e já passada por
# `sanitize_e5_for_parecer(·, ())`. A factory viva é editada por outras lanes, e cada
# edição viraria bump forçado. Editar a fixture ou `_REGIMES` re-pina e cobra bump do
# manifest — cobertura nova entra junto de mudança de manifest que já bumpa.

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from backend.app.services import parecer_citation_catalog, parecer_distiller, parecer_manifest
from backend.app.services.parecer_distiller import declared_fields, surviving_sections, walk_path
from backend.app.services.parecer_manifest import load_manifest, load_persona
from backend.app.services.parecer_orchestrator import _build_prompts
from pipeline.llm.prompts.parecer_planejador import SYSTEM_PROMPT_SHA256

_REPO = Path(__file__).resolve().parents[1]
_FIXTURE = _REPO / "tests" / "fixtures" / "parecer_prompt_fingerprint" / "e5_sintetico.json"
_MANIFEST_YAML = Path("config/prompts/parecer_planejador.yaml")
_PROMPT_MODULE = Path("pipeline/llm/prompts/parecer_planejador.py")
_PERSONA = Path("config/agents/planner_persona.md")
_CI = _REPO / ".github" / "workflows" / "ci.yml"

# Regime → `max_exec_context_bytes` (None = o do manifest). Nome e cap compõem o pin. O
# dogfood alcança os dois cortes, e a fixture densa, sob o cap real, não: `evicao` remove
# seções inteiras (`_eviction_marker`); em `corte_duro` sobra uma seção que sozinha não
# cabe, e o corte por bytes cai no meio de um caractere multibyte (`errors="ignore"`).
_REGIMES: dict[str, int | None] = {"sem_evicao": None, "evicao": 6144, "corte_duro": 344}
_MARCADOR_EVICAO = "seções removidas por prioridade"

# Path que o manifest projeta e a fixture não tem, com o motivo. Igualdade de conjunto:
# path novo no manifest reprova até a fixture ganhá-lo, no mesmo PR que já bumpa.
_BLOCO_VAZIO = "key_value inteiro ausente — o bloco some junto com o título (509d8d0e)"
AUSENTES_DELIBERADOS: dict[str, str] = {
    "$.goals.alocacao_alvo.derived.renda_fixa_atual_pct": _BLOCO_VAZIO,
    "$.goals.alocacao_alvo.derived.carteira_liquida_brl": _BLOCO_VAZIO,
    "$.goals.alocacao_alvo.derived.desvio_max_pct": _BLOCO_VAZIO,
    "$.goals.alocacao_alvo.derived.next_aporte_classe": _BLOCO_VAZIO,
    "$.goals.alocacao_alvo.derived.motivo_supressao": _BLOCO_VAZIO,
    "$.goals.alocacao_alvo.derived.has_alvo": _BLOCO_VAZIO,
    "$.premissas_economicas.status": "escalar `on_null: skip` ausente — não rende linha",
}


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _manifest_do_regime(regime: str):
    cap = _REGIMES[regime]
    manifest = load_manifest()
    return manifest if cap is None else dataclasses.replace(manifest, max_exec_context_bytes=cap)


def _e5() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def renderizar() -> dict[str, tuple[str, str]]:
    """(system, user) por regime — manifest, persona e fixture relidos do disco."""
    persona_body, _hash = load_persona()
    return {
        regime: _build_prompts(
            manifest=_manifest_do_regime(regime), persona_body=persona_body, e5_data=_e5()
        )
        for regime in _REGIMES
    }


def digests() -> dict[str, str]:
    """O que os pins fixam: o system (o mesmo em todo regime) e o user de cada regime."""
    prompts = renderizar()
    systems = {_sha256(system) for system, _user in prompts.values()}
    assert len(systems) == 1, "o system variou com o regime, e ele não depende do E5"
    return {"system": systems.pop(), **{r: _sha256(user) for r, (_s, user) in prompts.items()}}


@pytest.fixture(scope="module")
def atuais() -> dict[str, str]:
    """Determinismo ANTES do pin: dois renders no mesmo processo têm de bater."""
    primeiro, segundo = digests(), digests()
    assert primeiro == segundo, "render não-determinístico no mesmo processo — pin inaplicável"
    return primeiro


@pytest.fixture(scope="module")
def pins_do_manifest() -> dict[str, str]:
    """Lido do YAML cru: `load_manifest` ignora a chave — o pin não tem leitor em runtime."""
    manifest = yaml.safe_load((_REPO / _MANIFEST_YAML).read_text(encoding="utf-8"))
    return manifest["user_prompt_sha256"]


# ---------------------------------------------------------------------------------------
# Precondição: byte-identidade entre runs (a da ADR-307 §7, nunca provada para o distiller)
# ---------------------------------------------------------------------------------------


def _digests_em_subprocesso(hash_seed: str) -> dict[str, str]:
    pythonpath = os.pathsep.join(filter(None, [str(_REPO), os.environ.get("PYTHONPATH")]))
    env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": pythonpath}
    codigo = "import json; from tests.test_parecer_prompt_fingerprint import digests; "
    codigo += "print(json.dumps(digests()))"
    saida = subprocess.run(
        [sys.executable, "-c", codigo], cwd=_REPO, env=env, capture_output=True, text=True
    )
    assert saida.returncode == 0, saida.stderr[-2000:]
    return json.loads(saida.stdout.strip().splitlines()[-1])


def test_render_e_byte_identico_entre_processos_com_hash_seeds_distintos(atuais):
    """A ordem de set/frozenset de str muda com PYTHONHASHSEED; o render não pode mudar."""
    por_seed = {seed: _digests_em_subprocesso(seed) for seed in ("0", "1")}
    assert por_seed["0"] == por_seed["1"] == atuais


# ---------------------------------------------------------------------------------------
# Os pins
# ---------------------------------------------------------------------------------------


def test_system_prompt_bate_com_o_pin_ao_lado_de_prompt_version(atuais):
    assert atuais["system"] == SYSTEM_PROMPT_SHA256, (
        f"o system prompt mudou de byte (SYSTEM_PROMPT_TEMPLATE, persona ou _build_prompts). "
        f"Em {_PROMPT_MODULE}: SYSTEM_PROMPT_SHA256 = {atuais['system']!r} E bump de "
        f"PROMPT_VERSION — o gate W2-T05 cobra o bump de qualquer edição do arquivo, e é o "
        f"bump que separa a janela do drift monitor."
    )


@pytest.mark.parametrize("regime", list(_REGIMES))
def test_user_prompt_bate_com_o_pin_do_manifest(atuais, pins_do_manifest, regime):
    assert atuais[regime] == pins_do_manifest.get(regime), (
        f"o user prompt do regime {regime!r} mudou de byte (distiller, catálogo, formatter, "
        f"manifest, _build_prompts ou USER_PROMPT_TEMPLATE). Em {_MANIFEST_YAML}: "
        f"user_prompt_sha256.{regime}: {atuais[regime]!r} E bump de `version:` — mais "
        f"PROMPT_VERSION se mudou o USER_PROMPT_TEMPLATE. Editar a fixture ou _REGIMES "
        f"também re-pina. Dois PRs que mudam o prompt: quem entra por último re-pina sobre "
        f"o main atualizado."
    )


def test_o_manifest_pina_exatamente_os_regimes_do_teste(pins_do_manifest):
    assert set(pins_do_manifest) == set(_REGIMES)


# ---------------------------------------------------------------------------------------
# O pin tem dente: a corrente até o gate de bump e até o job que roda este arquivo
# ---------------------------------------------------------------------------------------


def _ci() -> dict:
    return yaml.safe_load(_CI.read_text(encoding="utf-8"))


def _hook_de_bump() -> dict:
    config = yaml.safe_load((_REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hooks = [hook for repo in config["repos"] for hook in repo["hooks"]]
    return next(hook for hook in hooks if hook["id"] == "prompt-version-bumped")


def test_os_dois_arquivos_do_pin_estao_sob_o_gate_de_bump(monkeypatch):
    """Sem isto, tirar um arquivo do gate deixaria o pin mudar sem bump, calado."""
    from dev.check_prompt_version_bumped import YAML_VERSIONADO, _discover_prompts

    monkeypatch.chdir(_REPO)
    assert _MANIFEST_YAML in YAML_VERSIONADO
    assert _PROMPT_MODULE in _discover_prompts()


def test_o_gate_de_bump_roda_no_ci_sobre_os_dois_arquivos():
    arquivos = re.compile(_hook_de_bump()["files"])
    assert arquivos.search(str(_MANIFEST_YAML)) and arquivos.search(str(_PROMPT_MODULE))
    passo = next(
        p for p in _ci()["jobs"]["lint-all"]["steps"] if "pre-commit run" in p.get("run", "")
    )
    assert "prompt-version-bumped" not in passo.get("env", {}).get("SKIP", "").split(",")


def test_pr_que_so_edita_a_persona_roda_este_teste():
    """O caso do 27bcd6d7: sem o path no grupo `pipeline`, o PR roda só o Lint."""
    ci = _ci()
    filtro = next(p for p in ci["jobs"]["changes"]["steps"] if p.get("id") == "filter")
    assert str(_PERSONA) in yaml.safe_load(filtro["with"]["files_yaml"])["pipeline"]
    assert "outputs.pipeline == 'true'" in ci["jobs"]["pipeline-tests"]["if"]


def test_um_byte_na_persona_tira_o_system_do_pin(monkeypatch, tmp_path, atuais):
    persona = tmp_path / "planner_persona.md"
    persona.write_text(load_persona()[0] + "\n", encoding="utf-8")
    monkeypatch.setattr(parecer_manifest, "_PERSONA_PATH", str(persona))
    mutado = digests()
    assert mutado["system"] != atuais["system"]
    assert {r: mutado[r] for r in _REGIMES} == {r: atuais[r] for r in _REGIMES}


@pytest.mark.parametrize(
    ("modulo", "constante"),
    [(parecer_distiller, "_HINTS_HEADER"), (parecer_citation_catalog, "_CATALOG_HEADER")],
)
def test_um_byte_no_render_tira_o_user_do_pin(monkeypatch, atuais, modulo, constante):
    monkeypatch.setattr(modulo, constante, getattr(modulo, constante) + " ")
    mutado = digests()
    assert mutado["sem_evicao"] != atuais["sem_evicao"]
    assert mutado["system"] == atuais["system"]


# ---------------------------------------------------------------------------------------
# A fixture exercita o que o pin diz cobrir — senão ele passa por vacuidade
# ---------------------------------------------------------------------------------------


def _paths_do_bloco(bloco: dict) -> list[str]:
    if bloco.get("format") == "table":
        return [bloco["path"]]
    return [campo["path"] for campo in declared_fields(bloco)]


def test_a_fixture_tem_todo_path_do_manifest_menos_os_ausentes_deliberados():
    """Campo que a fixture não tem é campo cujo render o pin não vê."""
    e5, secoes = _e5(), load_manifest().sections
    declarados = {p for s in secoes for b in s.get("blocks", []) for p in _paths_do_bloco(b)}
    assert {p for p in declarados if walk_path(e5, p) is None} == set(AUSENTES_DELIBERADOS)


def test_sem_evicao_exercita_catalogo_hints_ausencias_e_strings():
    _system, user = renderizar()["sem_evicao"]
    assert _MARCADOR_EVICAO not in user
    assert "### Evidência citável" in user and "### Diretrizes de leitura" in user
    assert "rentabilidade.valor_pct" in user  # o dict achatado é renderizado…
    assert "rentabilidade.defasagem_meses" not in user  # …e a folha None é pulada (f19fe720)
    assert "rentabilidade_pct" not in user  # sentinela "N/D" achatada é ausência
    assert "Alocação atual vs. alvo" not in user  # key_value vazio some com o título
    assert "Receita one-time: N/D" in user  # string não numérica em campo `brl`
    assert "(12m, %): 38,50%" in user  # string numérica em campo `percent2`
    assert "valor_total_imoveis" not in user  # folha R$ fora da whitelist sai do catálogo


def _byte_logo_apos_o_corte(regime: str) -> int:
    """Primeiro byte que `_hard_cut` deixa de fora, pelo mesmo orçamento que ele usa."""
    manifest, e5 = _manifest_do_regime(regime), _e5()
    corpos = [parecer_distiller._render_section_body(s, e5) for s in manifest.sections]
    cap = manifest.max_exec_context_bytes
    mantidas, evictadas = parecer_distiller._evict_to_budget(manifest.sections, corpos, cap)
    bruto = "\n".join(corpos[i] for i in mantidas).encode("utf-8")
    orcamento = cap - len(parecer_distiller._eviction_marker(evictadas).encode("utf-8"))
    assert 0 < orcamento < len(bruto), f"o regime {regime!r} não corta dentro do corpo"
    return bruto[orcamento]


def test_evicao_e_corte_duro_exercitam_os_ramos_que_nomeiam():
    assert _MARCADOR_EVICAO in renderizar()["evicao"][1]
    assert surviving_sections(_manifest_do_regime("evicao"), _e5())[1] is False
    assert surviving_sections(_manifest_do_regime("corte_duro"), _e5())[1] is True
    continuacao = _byte_logo_apos_o_corte("corte_duro") & 0xC0 == 0x80
    assert continuacao, "o corte não cai no meio de um caractere multibyte"
