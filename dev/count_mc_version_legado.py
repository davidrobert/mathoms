#!/usr/bin/env python3
"""Conta artefatos ``analyze_finances`` alcançáveis com ``mc_version`` anterior ao rename do cone (ADR-369 D3)."""

# Gatilho de remoção do compat de leitura em ``scripts/generate_narratives.py``:
# zero alcançáveis abaixo de ``--minimo`` ⇒ o ramo legado pode sair. É contador,
# não calendário — janela datada sem medição é dívida eterna com validade
# decorativa.
#
# "Alcançável" = o que o read path realmente devolve: o artefato **mais recente**
# por workspace para ``(analyze_finances, analise_financeira)``, pela mesma query
# de ``read_latest_artifact`` (aliases legado↔descritivo da ADR-093). Row antiga
# que nenhum leitor alcança não sustenta compat — só as vivas contam.
#
# Uso: ``python3 dev/count_mc_version_legado.py [--minimo 4] [--verbose]``
# Exit 0 quando zero legados (compat removível); 1 caso contrário.

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.database import SyncSessionLocal  # noqa: E402
from backend.app.models.workspace import Workspace  # noqa: E402
from backend.app.repositories.pipeline_artifact_repository import (  # noqa: E402
    PipelineArtifactRepository,
)
from backend.app.services.security.crypto import read_artifact_content  # noqa: E402

_STAGE = "analyze_finances"
_KEY = "analise_financeira"
# Payload existe mas não decifra (key rotation incompleta, ADR-171): não prova
# versão nenhuma, e derrubar a varredura inteira num workspace tornaria o
# gatilho não-medível justamente onde ele decide.
_ILEGIVEL = -1


def _mc_major(payload: dict) -> int:
    """Major de ``mc_version``; ausente = 1 (artefato pré-ADR-360)."""
    bloco = payload.get("if_monte_carlo") or {}
    cabeca = str(bloco.get("mc_version") or "1.0").split(".", 1)[0]
    return int(cabeca) if cabeca.isdigit() else 1


def _versao_alcancavel(repo: PipelineArtifactRepository, workspace_id: str) -> int | None:
    """Major do artefato que o read path devolve hoje; ``None`` se não há artefato."""
    art = repo.get_latest_for_workspace(workspace_id, stage=_STAGE, artifact_key=_KEY)
    if art is None or art.content_json is None:
        return None
    try:
        return _mc_major(read_artifact_content(art.content_json))
    except Exception:
        return _ILEGIVEL


def _workspace_ids(db) -> list[str]:
    """Ids de todos os workspaces (só a coluna — o payload é lido um a um)."""
    rows = db.execute(Workspace.__table__.select().with_only_columns(Workspace.id))
    return [row[0] for row in rows]


class _Contagem:
    """Acumulador da varredura — total com artefato, legados e ilegíveis."""

    def __init__(self, minimo: int) -> None:
        self.minimo = minimo
        self.total = 0
        self.ilegiveis = 0
        self.legados: list[tuple[str, int]] = []

    def registrar(self, workspace_id: str, major: int) -> None:
        self.total += 1
        if major == _ILEGIVEL:
            self.ilegiveis += 1
        elif major < self.minimo:
            self.legados.append((workspace_id, major))

    @property
    def pendentes(self) -> int:
        return len(self.legados) + self.ilegiveis


def _varrer(minimo: int) -> _Contagem:
    """Percorre os workspaces e classifica o artefato alcançável de cada um."""
    contagem = _Contagem(minimo)
    with SyncSessionLocal() as db:
        repo = PipelineArtifactRepository(db)
        for workspace_id in _workspace_ids(db):
            major = _versao_alcancavel(repo, workspace_id)
            if major is not None:
                contagem.registrar(workspace_id, major)
    return contagem


def _reportar(contagem: _Contagem, verbose: bool) -> None:
    """Imprime o resultado da varredura."""
    print(f"artefatos {_STAGE}/{_KEY} alcançáveis: {contagem.total}")
    print(f"com mc_version major < {contagem.minimo}: {len(contagem.legados)}")
    if contagem.ilegiveis:
        print(f"ilegíveis (não decifram — key rotation? ADR-171): {contagem.ilegiveis}")
    if not verbose:
        return
    for workspace_id, major in contagem.legados:
        print(f"  {workspace_id}  major={major}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gatilho de remoção do compat do cone (ADR-369 D3)."
    )
    parser.add_argument("--minimo", type=int, default=4, help="major mínimo aceito (default: 4)")
    parser.add_argument("--verbose", action="store_true", help="lista os workspaces legados")
    args = parser.parse_args()

    contagem = _varrer(args.minimo)
    _reportar(contagem, args.verbose)
    if contagem.pendentes:
        print(f"compat de leitura do cone AINDA NECESSÁRIO ({contagem.pendentes} workspace(s)).")
        return 1
    print("zero legados — o ramo de compat em generate_narratives pode ser removido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
