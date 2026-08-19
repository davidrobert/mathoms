"""§r7 — testes do gate `dev/check_adr_id_unique.py` (id de ADR é recurso global)."""

from __future__ import annotations

from pathlib import Path

import dev.check_adr_id_unique as gate


def _adr(dir_: Path, filename: str, note_id: str, *, frontmatter_extra: str = "") -> Path:
    path = dir_ / filename
    path.write_text(
        f'---\nid: {note_id}\ntype: adr\ntitle: "T"\nstatus: Proposto\n'
        f'date: "2026-08-19"\n{frontmatter_extra}---\n\nCorpo.\n',
        encoding="utf-8",
    )
    return path


def test_ids_distintos_passam(tmp_path: Path, monkeypatch) -> None:
    _adr(tmp_path, "396-um.md", "ADR-396")
    _adr(tmp_path, "397-outro.md", "ADR-397")
    monkeypatch.setattr(gate, "ADR_DIR", tmp_path)
    assert gate.main() == 0


def test_mesmo_id_em_filenames_distintos_falha(tmp_path: Path, monkeypatch, capsys) -> None:
    """O caso real de 2026-08-19: filenames diferentes, mesmo id, nenhum conflito de merge."""
    _adr(tmp_path, "396-amostragem-declarada-no-call-site.md", "ADR-396")
    _adr(tmp_path, "396-eixo-de-fato-e-precondicao-de-mint.md", "ADR-396")
    monkeypatch.setattr(gate, "ADR_DIR", tmp_path)
    assert gate.main() == 1
    out = capsys.readouterr().out
    assert "ADR-396" in out
    assert "396-amostragem-declarada-no-call-site.md" in out
    assert "396-eixo-de-fato-e-precondicao-de-mint.md" in out


def test_tres_vias_lista_os_tres(tmp_path: Path, monkeypatch, capsys) -> None:
    for slug in ("a", "b", "c"):
        _adr(tmp_path, f"396-{slug}.md", "ADR-396")
    monkeypatch.setattr(gate, "ADR_DIR", tmp_path)
    assert gate.main() == 1
    assert "declarado por 3 arquivos" in capsys.readouterr().out


def test_id_fora_do_frontmatter_nao_conta(tmp_path: Path, monkeypatch) -> None:
    """`id:` citado no corpo é prosa, não declaração — senão exemplo em ADR vira duplicata."""
    _adr(tmp_path, "396-um.md", "ADR-396")
    (tmp_path / "397-outro.md").write_text(
        '---\nid: ADR-397\ntype: adr\ntitle: "T"\nstatus: Proposto\ndate: "2026-08-19"\n---\n\n'
        "Exemplo de frontmatter que uma nota futura teria:\n\n```yaml\nid: ADR-396\n```\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gate, "ADR_DIR", tmp_path)
    assert gate.main() == 0


def test_repo_real_nao_tem_duplicata() -> None:
    """Guarda viva: `main` entra e sai sem id repetido."""
    assert gate.main() == 0
