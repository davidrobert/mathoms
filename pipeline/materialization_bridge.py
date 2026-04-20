"""MaterializationBridge — adapter temporário para scripts legados (ADR-086).

Durante a Fase 3, scripts legados (``e3_reconcile.py``, ``e4_categorize.py``,
``e5_analyze.py``, ``e5n_narrativas.py``, ``e7_review.py``) continuam lendo e
escrevendo em ``processed/*.json``. Quando o ``ArtifactStore`` ativo é um
:class:`DBArtifactStore`, o bridge:

1. **Hidrata** artefatos do DB para um diretório temporário antes do stage rodar
   (:meth:`hydrate_for_stage`, usa ``StageSpec.reads``).
2. **Persiste** os arquivos gerados do diretório temporário de volta para o DB
   (:meth:`persist_from_stage`, usa ``StageSpec.writes``).

Diretório efêmero: ``/tmp/fin_pipeline_{pipeline_run_id}/``. O bridge é um
context manager — limpa o diretório no ``__exit__``, inclusive em falhas.

A Fase 9 remove este módulo: todos os stages migram para Caminho B e usam
``ArtifactStore`` diretamente.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pipeline.artifact_store import stage_dir_name, stage_suffix
from pipeline.stage_spec import STAGE_REGISTRY, VIRTUAL_ARTIFACT_STAGES

if TYPE_CHECKING:
    from pipeline.artifact_store import ArtifactStore


class MaterializationBridge:
    """Adapter temporário DB ↔ tmp_dir para scripts legados."""

    def __init__(
        self,
        store: "ArtifactStore",
        *,
        pipeline_run_id: str,
        tmp_root: Optional[Path] = None,
    ) -> None:
        self._store = store
        self._pipeline_run_id = pipeline_run_id
        # ``tmp_root``: diretório base; o bridge cria um sub-diretório único.
        self._tmp_root = Path(tmp_root) if tmp_root else Path(tempfile.gettempdir())
        self._tmp_dir: Optional[Path] = None

    # -- Context manager --

    def __enter__(self) -> "MaterializationBridge":
        self._tmp_dir = self._tmp_root / f"fin_pipeline_{self._pipeline_run_id}"
        self._tmp_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._tmp_dir and self._tmp_dir.exists():
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        self._tmp_dir = None

    # -- Helpers --

    @property
    def tmp_dir(self) -> Path:
        if self._tmp_dir is None:
            raise RuntimeError(
                "MaterializationBridge usado fora de `with` block — "
                "chamar via `with MaterializationBridge(...) as bridge:`"
            )
        return self._tmp_dir

    def processed_dir(self) -> Path:
        return self.tmp_dir / "processed"

    # -- Hidratação (DB → disco) --

    def hydrate_for_stage(self, stage: str) -> Path:
        """Copia artefatos dos stages declarados em ``reads`` para ``tmp_dir``.

        Usa ``StageSpec.reads`` — não há lógica por stage hardcoded. Stages
        virtuais (``VIRTUAL_ARTIFACT_STAGES``) são lidos pelo mesmo
        ``ArtifactStore.read`` pois a coluna ``stage`` em ``pipeline_artifacts``
        aceita ambos.

        Retorna o path raiz hidratado (``tmp_dir``), que pode ser passado como
        ``root_dir=`` para scripts legados.
        """
        if stage not in STAGE_REGISTRY:
            raise KeyError(f"Stage '{stage}' não está no STAGE_REGISTRY")
        spec = STAGE_REGISTRY[stage]
        for input_stage in spec.reads:
            self._materialize_stage_to_disk(input_stage)
        return self.tmp_dir

    def _materialize_stage_to_disk(self, input_stage: str) -> None:
        if input_stage in VIRTUAL_ARTIFACT_STAGES:
            # Virtual stages (E5-revised) usam o mesmo layout do stage "real"
            # para efeito de disco (mesmo dir+suffix do E5).
            dir_name = stage_dir_name("E5")
            suffix = stage_suffix("E5")
        else:
            dir_name = stage_dir_name(input_stage)
            suffix = stage_suffix(input_stage)

        stage_disk_dir = self.processed_dir() / dir_name
        stage_disk_dir.mkdir(parents=True, exist_ok=True)
        for key in self._store.list_keys(input_stage):
            data = self._store.read(input_stage, key)
            if data is None:
                continue
            path = stage_disk_dir / f"{key}{suffix}"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # -- Persistência (disco → DB) --

    def persist_from_stage(self, stage: str, *, source_dir: Optional[Path] = None) -> int:
        """Lê arquivos escritos pelo script legado e persiste no ``store``.

        Usa ``StageSpec.writes``. Retorna a contagem de artefatos persistidos.
        Se ``source_dir`` for passado, lê de lá; senão usa ``tmp_dir/processed``.
        """
        if stage not in STAGE_REGISTRY:
            raise KeyError(f"Stage '{stage}' não está no STAGE_REGISTRY")
        spec = STAGE_REGISTRY[stage]
        base = Path(source_dir) if source_dir is not None else self.processed_dir()
        count = 0
        for out_stage in spec.writes:
            if out_stage in VIRTUAL_ARTIFACT_STAGES:
                dir_name = stage_dir_name("E5")
                suffix = stage_suffix("E5")
            else:
                dir_name = stage_dir_name(out_stage)
                suffix = stage_suffix(out_stage)
            stage_disk_dir = base / dir_name
            if not stage_disk_dir.exists():
                continue
            for f in sorted(stage_disk_dir.iterdir()):
                if not f.name.endswith(suffix):
                    continue
                key = f.name[: -len(suffix)]
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                self._store.write(out_stage, key, data)
                count += 1
        return count
