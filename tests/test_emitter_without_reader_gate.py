"""Mutação nas duas direções para o gate de emissor sem leitor (A40.l88 · U1 RR5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dev.check_emitter_without_reader import (
    MissingConsumer,
    declared_custom_properties,
    dispatched_section_ids,
    find_inert_custom_properties,
    find_undispatched_sections,
    find_unrendered_parecer_fields,
    has_rendering_reader,
    parecer_content_fields,
    stale_waivers,
    strip_comments,
)

DTO = """\
export interface ParecerPlanejadorContent {
  diagnostico_geral: string;
  notas_metodologicas: NotaMetodologica[];
}
"""

DISPATCHER = """\
export const MIGRATED_SECTIONS: ReadonlySet<string> = new Set(["S1", "S_PROTECAO"]);
export function MigratedSection({ sectionId }: Props) {
  switch (sectionId) {
    case "S1":
      return <S1PatrimonioSection />;
    default:
      return null;
  }
}
"""


def _write(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_parecer_field_sem_renderer_fica_vermelho_e_com_renderer_fica_verde(
    tmp_path: Path,
) -> None:
    dto = _write(tmp_path, "planner-review.ts", DTO)
    components = tmp_path / "components" / "SParecer"

    _write(components, "Body.tsx", "<p>{content.diagnostico_geral}</p>")
    sem_leitor = find_unrendered_parecer_fields(dto, tmp_path / "components")

    _write(components, "Notas.tsx", "content.notas_metodologicas.map((n) => n.titulo)")
    com_leitor = find_unrendered_parecer_fields(dto, tmp_path / "components")

    assert [v.subject for v in sem_leitor] == ["notas_metodologicas"]
    assert com_leitor == []


def test_contabilidade_de_gated_counts_nao_conta_como_renderer() -> None:
    assert not has_rendering_reader("notas_metodologicas", "gated.notas_metodologicas")
    assert has_rendering_reader("notas_metodologicas", "content.notas_metodologicas")


def test_leitor_dentro_de_comentario_nao_conta() -> None:
    assert not has_rendering_reader("riscos", strip_comments("// content.riscos saiu daqui"))
    assert not has_rendering_reader("riscos", strip_comments("/* content.riscos */"))
    assert has_rendering_reader("riscos", strip_comments("const r = content.riscos;"))


def test_strip_comments_preserva_numero_de_linha() -> None:
    stripped = strip_comments("/* a\nb\nc */\nconst x = 1;")

    assert stripped.count("\n") == 3


def test_secao_sem_dispatch_fica_vermelha_e_com_case_fica_verde(tmp_path: Path) -> None:
    components = tmp_path / "components"
    dispatcher = _write(components, "MigratedSection.tsx", DISPATCHER)
    _write(components / "sections", "S_ProtecaoSection.tsx", '<ReportSection id="S_PROTECAO">')

    sem_case = find_undispatched_sections(components, dispatcher)

    dispatcher.write_text(
        DISPATCHER.replace(
            "    default:", '    case "S_PROTECAO":\n      return <P />;\n    default:'
        ),
        encoding="utf-8",
    )
    com_case = find_undispatched_sections(components, dispatcher)

    assert [v.subject for v in sem_case] == ["S_PROTECAO"]
    assert com_case == []


def test_estar_no_conjunto_sem_case_nao_e_dispatch() -> None:
    """`MIGRATED_SECTIONS` sem `case` renderiza `null` — inscrição não é entrega."""
    assert dispatched_section_ids(DISPATCHER) == {"S1"}


def test_secao_renderizada_pelo_shell_nao_e_violacao(tmp_path: Path) -> None:
    components = tmp_path / "components"
    dispatcher = _write(components, "MigratedSection.tsx", DISPATCHER)
    _write(components, "PerfilFamiliaSection.tsx", '<ReportSection id="perfil">')

    assert find_undispatched_sections(components, dispatcher) == []


def test_custom_property_inerte_fica_vermelha_e_com_var_fica_verde(tmp_path: Path) -> None:
    components = tmp_path / "components"
    _write(components, "x.print.css", "details {\n  --details-open: 1;\n}")

    inerte = find_inert_custom_properties(components, tmp_path)

    _write(components, "y.tsx", "const open = 'var(--details-open)';")
    lida = find_inert_custom_properties(components, tmp_path)

    assert [v.subject for v in inerte] == ["--details-open"]
    assert lida == []


@pytest.mark.parametrize(
    "source, esperado",
    [
        ("  --a: 1;\n  --b-c: 2;", ["--a", "--b-c"]),
        ("color: var(--nao-declarada);", []),
    ],
)
def test_declaracao_e_leitura_sao_lados_distintos(source: str, esperado: list[str]) -> None:
    assert declared_custom_properties(source) == esperado


def test_waiver_que_nao_corresponde_a_achado_vivo_falha() -> None:
    vivo = MissingConsumer("PARECER_FIELD", "version", "…")

    assert stale_waivers([vivo]) == []
    assert stale_waivers([]) == ["PARECER_FIELD:version"]


def test_contrato_real_declara_os_campos_do_parecer() -> None:
    """Sem isto o parser de interface poderia devolver [] e o gate afirmaria zero."""
    campos = parecer_content_fields(
        Path("frontend/src/lib/api/planner-review.ts").read_text(encoding="utf-8")
    )

    assert {"riscos", "notas_metodologicas", "metricas"} <= set(campos)
