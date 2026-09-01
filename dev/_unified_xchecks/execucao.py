"""X5 — proveniencia declarada: stage `completed` sem artefato do run."""

# `PV12-04` (`U4`): o predicado antigo — `completed` + 0 artefatos + `writes`
# declarados — marcava os MESMOS 3 stages em `U2`/`U3`/`U4`, por 3 razoes
# diferentes, sob o rotulo unico "contrato falso". Poder discriminante zero: o
# check nao podia ficar verde, logo nao informava nada. `StageSpec.writes` nao
# serve de discriminador (a propria docstring dele chama o campo de ficcao, e o
# `PV10-10` mediu que `writes=()` e `writes=("xpto",)` passam igual na validacao
# de ordem). Aqui as causas benignas sao SEPARADAS: duas se computam da
# evidencia do run, duas se declaram por igualdade de conjunto e sao
# cross-checadas contra a fonte.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from dev._unified_xchecks.base import _db, veredito

_RAIZ = Path(__file__).resolve().parent.parent.parent
_WRITE_ALVO = re.compile(r"\.write\(\s*[\"']([A-Za-z_][A-Za-z_0-9]*)[\"']")
_WRITE_QUALQUER = re.compile(r"\.write\(")


@dataclass(frozen=True)
class Dispensa:
    """Motivo declarado LITERALMENTE para um stage nao produzir artefato proprio."""

    # `escreve_em=None` afirma ausencia de writer; qualquer outro valor afirma
    # redirecao para a chave de outro stage. Os dois sao cross-checados contra
    # `evidencia` a cada execucao — declaracao que a fonte desmente REPROVA.

    causa: str
    porque: str
    evidencia: str
    escreve_em: str | None = None


# Declaracao por IGUALDADE DE CONJUNTO, nao isencao por arquivo: um 4o stage
# nesta condicao sai `OFENSOR`, e um destes que deixe de estar nela sai
# `VENCIDA`. As duas causas ficam nomeadas separadamente — `PV12-04` nasceu de
# chamar estas duas (e o skip, que nem declaracao precisa) de "contrato falso".
DISPENSAS: dict[str, Dispensa] = {
    "generate_narratives": Dispensa(
        causa="ESCREVE-EM-OUTRA-KEY",
        porque="faz merge das narrativas no payload do E5, por desenho (CLAUDE.md)",
        evidencia="scripts/generate_narratives.py",
        escreve_em="analyze_finances",
    ),
    "validate_cross": Dispensa(
        causa="READ-ONLY",
        porque="crossval le o E5 e emite veredito; nao ha call-site de write",
        evidencia="scripts/validate_cross.py",
    ),
}

# Classes que pedem acao. `INDETERMINADO` nao conta como divergencia — encolhe
# `n_comparado` e derruba o veredito para INAPLICAVEL, que e o certo para
# instrumento quebrado. Marcador e veredito saem desta MESMA fonte para nao
# poderem discordar.
_ATENCAO = ("OFENSOR", "VENCIDA", "INDETERMINADO")
_DIVERGENTES = ("OFENSOR", "VENCIDA")

# `LC9-05`: classes em que a linha NAO podia sair ofensora, qualquer que fosse o
# run. Stage que nao chegou a `completed` esta fora do predicado; stage que
# declarou zero trabalho sai pela escada antes do ramo de ofensa; stage que nao
# promete artefato nao pode faltar com ele. Todas legitimas — e nenhuma e
# evidencia de proveniencia sa, entao nenhuma pode contar como cobertura.
_SEM_PODER = ("NAO-COMPLETED", "SEM-TRABALHO", "SEM-WRITES-DECLARADOS", "INDETERMINADO")


def _ler_fonte(rel: str) -> str | None:
    """``None`` ≡ ilegivel. Nunca confundir com "zero writes encontrados": a
    dispensa READ-ONLY afirma AUSENCIA, e arquivo sumido a satisfaria de graca."""
    alvo = _RAIZ / rel
    return alvo.read_text(encoding="utf-8") if alvo.is_file() else None


def _viola(d: Dispensa, src: str, por_stage: dict) -> str | None:
    """Mensagem de violacao da declaracao, ou ``None`` se ela se sustenta."""
    if d.escreve_em is None:
        n = len(_WRITE_QUALQUER.findall(src))
        return f"declarada READ-ONLY mas a fonte tem {n} call-site(s) de write" if n else None
    if d.escreve_em not in _WRITE_ALVO.findall(src):
        return f"a fonte nao escreve em `{d.escreve_em}`"
    if por_stage.get(d.escreve_em, 0) == 0:
        return f"alvo `{d.escreve_em}` sem artefato neste run"
    return None


def _como_dict(summary):
    if isinstance(summary, str):
        try:
            return json.loads(summary)
        except ValueError:
            return None
    return summary if isinstance(summary, dict) else None


def _sem_trabalho(summary) -> str | None:
    """Zero trabalho DECLARADO pelo proprio stage, em qualquer das duas grafias."""
    # O repo carimba "nao havia o que fazer" de dois jeitos — `skipped: true` (8
    # stages) e `total_processed: 0` (4 stages) — e os MESMOS stages usam os dois
    # conforme a saida que tomam. Tratar so o primeiro como benigno reprovava
    # `extract_with_llm` em 5 dos 25 runs do dogfood: a classe de falso-positivo
    # que o `PV10-10` deu por conhecida e NAO codificada. As duas grafias carregam
    # a mesma informacao (o stage nao diz se DEVIA ter tido trabalho), entao valem
    # o mesmo veredito — e a divergencia de grafia fica nomeada, nao escondida.
    s = _como_dict(summary)
    if s is None:
        return None
    if s.get("skipped") is True:
        return f"skipped: {s.get('reason') or 'sem reason'}"
    if s.get("total_processed") == 0 and not s.get("total_errors"):
        return "total_processed=0 — nao carimbou `skipped` (grafia divergente)"
    return None


def _sem_artefato(stage: str, summary, writes: tuple, por_stage: dict, ler) -> tuple[str, str]:
    """Escada de causas para `completed` + 0 artefatos. Primeira que casa vence."""
    motivo = _sem_trabalho(summary)
    if motivo:
        return "SEM-TRABALHO", motivo
    if not writes:
        return "SEM-WRITES-DECLARADOS", "nao promete artefato"
    d = DISPENSAS.get(stage)
    if d is None:
        return "OFENSOR", "completed, promete artefato, nao declarou zero trabalho, sem dispensa"
    src = ler(d.evidencia)
    if src is None:
        return "INDETERMINADO", f"evidencia ilegivel: {d.evidencia}"
    msg = _viola(d, src, por_stage)
    return (d.causa, d.porque) if msg is None else ("VENCIDA", msg)


def _classe(stage: str, status: str, n: int, summary, writes: tuple, por_stage, ler):
    """(classe, detalhe) de uma linha de log."""
    if status != "completed":
        return "NAO-COMPLETED", ""
    if n > 0:
        if stage in DISPENSAS:
            return "VENCIDA", "produziu artefato proprio — a dispensa nao se aplica mais"
        return "OK", ""
    return _sem_artefato(stage, summary, writes, por_stage, ler)


def _spec_writes(stage: str, canon: str) -> tuple[str, ...]:
    from pipeline.stage_spec import STAGE_REGISTRY

    spec = STAGE_REGISTRY.get(canon) or STAGE_REGISTRY.get(stage)
    return tuple(getattr(spec, "writes", ()) or ()) if spec else ()


def classificar(logs: list, por_stage: dict, ler=_ler_fonte) -> dict:
    """Puro: (logs, artefatos por stage) → diagnostico. Testavel sem DB."""
    from pipeline.stage_spec import resolve_stage_name

    linhas, por_classe, completos = [], {}, set()
    for stage, status, summary in logs:
        canon = resolve_stage_name(stage)
        n, writes = por_stage.get(canon, 0), _spec_writes(stage, canon)
        classe, detalhe = _classe(canon, status, n, summary, writes, por_stage, ler)
        linhas.append((canon, status, n, writes, classe, detalhe))
        por_classe.setdefault(classe, {})[canon] = detalhe
        if status == "completed":
            completos.add(canon)
    return _diagnostico(linhas, por_classe, completos)


# `LC9-05`: `n_esperado` conta TODOS os stages logados, nao so os `completed`. O
# predicado antigo derivava o denominador da propria populacao que ele sabia
# julgar, entao stage fora de `completed` sumia dos DOIS lados e o leitor via
# `17/17` num run de 18 — com o excluido sendo `analyze_finances` em
# `needs_review`, o stage que construia o payload sob suspeita naquela rodada. A
# exclusao agora desloca `n_esperado` e sai nomeada no veredito.
def _diagnostico(linhas: list, por_classe: dict, completos: set) -> dict:
    """Denominadores + os dois lados da igualdade de conjunto."""
    indet = por_classe.get("INDETERMINADO", {})
    fora = dict(por_classe.get("NAO-COMPLETED", {}))
    sem_poder = sum(len(por_classe.get(c, {})) for c in _SEM_PODER)
    return {
        "linhas": linhas,
        "por_classe": por_classe,
        "ofensores": por_classe.get("OFENSOR", {}),
        "vencidas": por_classe.get("VENCIDA", {}),
        "indeterminados": indet,
        # Dispensa cujo stage nao rodou nao e vencida — e nao exercitada. Nao
        # entra na populacao, e por isso nao encolhe `n_comparado`.
        "ociosas": sorted(set(DISPENSAS) - completos),
        "fora_do_predicado": sorted(fora),
        "n_esperado": len(linhas),
        "n_comparado": len(linhas) - len(indet),
        # Quantos stages o predicado podia ter reprovado neste run.
        "n_falsificavel": len(linhas) - sem_poder,
    }


def _consulta(ws: str, run: str) -> tuple:
    text, SyncSessionLocal, _r, _d, _l = _db()
    logs_sql = (
        "SELECT stage, status, output_summary FROM pipeline_stage_logs "
        "WHERE pipeline_run_id=:r ORDER BY started_at"
    )
    art_sql = (
        "SELECT stage, COUNT(*) FROM pipeline_artifacts "
        "WHERE workspace_id=:w AND pipeline_run_id=:r GROUP BY stage"
    )
    outros_sql = (
        "SELECT COUNT(*), COUNT(DISTINCT pipeline_run_id) FROM pipeline_artifacts "
        "WHERE workspace_id=:w AND pipeline_run_id IS NOT NULL AND pipeline_run_id<>:r"
    )
    with SyncSessionLocal() as s:
        logs = [tuple(r) for r in s.execute(text(logs_sql), {"r": run}).fetchall()]
        rows = s.execute(text(art_sql), {"w": ws, "r": run}).fetchall()
        outros = s.execute(text(outros_sql), {"w": ws, "r": run}).first()
    return logs, rows, outros


def _por_stage(rows: list) -> dict[str, int]:
    from pipeline.stage_spec import resolve_stage_name

    acc: dict[str, int] = {}
    for st, n in rows:
        canon = resolve_stage_name(st)
        acc[canon] = acc.get(canon, 0) + n
    return acc


def _tabela(linhas: list) -> None:
    print("| stage | status log | artefatos deste run | StageSpec.writes | classe |")
    print("|---|---|---|---|---|")
    for canon, status, n, writes, classe, _det in linhas:
        marca = " ⚠️" if classe in _ATENCAO else ""
        print(f"| {canon} | {status} | {n} | {list(writes)} | {classe}{marca} |")


def _causas(diag: dict) -> None:
    """Cada causa nomeada SEPARADAMENTE — o rotulo unico era metade do PV12-04."""
    for classe in sorted(diag["por_classe"]):
        if classe in ("OK", "NAO-COMPLETED"):
            continue
        print(f"\n**{classe}** ({len(diag['por_classe'][classe])})")
        for stage, detalhe in sorted(diag["por_classe"][classe].items()):
            print(f"- `{stage}` — {detalhe}")
    if diag["ociosas"]:
        print(f"\ndispensas nao exercitadas neste run: {diag['ociosas']}")


def _x5_rodape(diag: dict, outros) -> None:
    print(
        f"\nartefatos do workspace de OUTROS runs: {outros[0]} em {outros[1]} runs "
        f"(substrato workspace-latest pode alcanca-los — ver PV9-01)"
    )
    veredito(
        "X5",
        diag["n_comparado"],
        diag["n_esperado"],
        sum(len(diag["por_classe"].get(c, {})) for c in _DIVERGENTES),
        n_falsificavel=diag["n_falsificavel"],
        nota=(
            "ofensor = completed + 0 artefatos, sem skip carimbado e sem dispensa "
            f"sustentada · fora do predicado por status: {_fora(diag)}"
        ),
    )


def x5(ws: str, run: str) -> None:
    logs, rows, outros = _consulta(ws, run)
    por_stage = _por_stage(rows)
    diag = classificar(logs, por_stage)
    print(f"## X5 — stage `completed` sem artefato do run  (run {run[:8]})")
    print(f"stages logados: {len(logs)} · stages com artefato deste run: {len(por_stage)}\n")
    _tabela(diag["linhas"])
    _causas(diag)
    _x5_rodape(diag, outros)


def _fora(diag: dict) -> str:
    """Nomeia no VEREDITO o stage que o predicado nao alcanca — nunca no denominador."""
    if not diag["fora_do_predicado"]:
        return "nenhum"
    status = {canon: st for canon, st, *_r in diag["linhas"]}
    return ", ".join(f"`{s}` ({status.get(s, '?')})" for s in diag["fora_do_predicado"])
