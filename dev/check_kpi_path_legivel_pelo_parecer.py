#!/usr/bin/env python3
"""Todo ponteiro do catálogo de KPI é LEGÍVEL pelo resolver do parecer (A40.l93).

O que mede: a metade decidível **sem payload** — sintaxe do subset aceito
(``planner_drill_down._JSONPATH_RE``) e raiz na whitelist do manifest de **produção**
(``load_manifest().tools_section_whitelist``). Cobre ``observado_path`` sempre, e
``ref`` quando ele é JSONPath: ponteiro auditável que ninguém consegue seguir é a
mesma classe, um andar abaixo.

O que NÃO mede: ``value_absent`` — folha sintaticamente válida que não existe no
payload. Foi o caso de origem do invariante (``carteira_trs`` apontava para
``ratios.rentabilidade.trs_pct``, campo que nunca existiu), e **não é decidível
estaticamente**: ``ratios`` é objeto aberto no schema E5, ``ratios.rentabilidade``
fica atrás de combinator e ``protecao_patrimonial`` sai por ``$ref`` cross-file. O
dono dessa metade é
``tests/test_e5_golden_execution.py::test_todo_observado_path_do_catalogo_resolve_no_payload``,
que resolve contra o payload de um run real, pelo resolver de produção.

O nome declara a fronteira de propósito. ``check_kpi_observado_path`` prometeria a
classe inteira e viraria o gate em que se confia mais do que ele mede — a patologia
das três falsas-verdes da [[A40.l89]].

Premissa, asserida em teste próprio (``tests/unit/pipeline/test_kpi_target_catalog.py``):
o conjunto de ``observado_path`` é **invariante ao payload**, e por isso enumerá-lo com
payload vazio basta. Catálogo que escolhesse path por ramo faria este gate medir só um
lado, calado.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.services.parecer_manifest import load_manifest  # noqa: E402
from pipeline.domain.services.kpi_target_catalog import build_kpi_targets  # noqa: E402
from pipeline.llm.tools.planner_drill_down import _JSONPATH_RE, _parse_jsonpath  # noqa: E402

# Não sai de config: o gate não olha limiar, e depender do ConfigStore o tornaria
# sensível a override de workspace que nada tem a ver com a forma do path.
_ALERTA_IRRELEVANTE = 50.0


def _raiz(path: str) -> str | None:
    segments = _parse_jsonpath(path)
    return segments[0][0] if segments else None


def _erro_de(chave: str, campo: str, path: str, whitelist: frozenset[str]) -> str | None:
    """Mensagem se ``path`` não é legível pelo resolver de produção; None se é."""
    if not _JSONPATH_RE.match(path):
        return (
            f"kpi_targets[{chave!r}].{campo} = {path!r} não casa o subset de JSONPath "
            f"do `planner_drill_down` (sem filtro, sem recursive descent). O resolver "
            f"devolve `path_not_whitelisted` e o parecer NUNCA lê este valor. "
            f"Publique a folha em ponto fixo no E5 — não alargue o subset, que daria "
            f"capacidade de filtro ao modelo para servir um consumidor interno."
        )
    raiz = _raiz(path)
    if raiz not in whitelist:
        return (
            f"kpi_targets[{chave!r}].{campo} = {path!r} tem raiz {raiz!r} fora da "
            f"whitelist do manifest (`get_e5_section.args_schema.section.enum` em "
            f"config/prompts/parecer_planejador.yaml). O resolver devolve "
            f"`path_not_whitelisted`."
        )
    return None


def _ponteiros(alvo: dict) -> list[tuple[str, str]]:
    """(campo, path) de `observado_path` + `ref` quando o ref é JSONPath."""
    out = [("observado_path", alvo["observado_path"])]
    ref = alvo.get("ref")
    if isinstance(ref, str) and ref.startswith("$."):
        out.append(("ref", ref))
    return out


def _errors() -> list[str]:
    whitelist = load_manifest().tools_section_whitelist
    alvos = build_kpi_targets({}, scoring={}, concentracao_alerta_pct=_ALERTA_IRRELEVANTE)
    return [
        erro
        for chave, alvo in sorted(alvos.items())
        for campo, path in _ponteiros(alvo)
        if (erro := _erro_de(chave, campo, path, whitelist)) is not None
    ]


def main() -> int:
    errors = _errors()
    if not errors:
        return 0
    print("ERRO: ponteiro de kpi_targets ilegível pelo resolver do parecer:", file=sys.stderr)
    for e in errors:
        print(f"  • {e}", file=sys.stderr)
    print(
        "\nNão cobre `value_absent` (folha ausente do payload) — esse é o "
        "`test_todo_observado_path_do_catalogo_resolve_no_payload`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
