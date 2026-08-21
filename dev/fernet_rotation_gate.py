#!/usr/bin/env python3
"""Gate executável da rotação Fernet (A34.l3 · ADR-171 · runbook fernet_rotation.md): ``preflight`` recusa rodar com a janela fechada (onde um dry-run daria falso-limpo), ``rotate`` faz dry-run → confirmação → passe real, ``verify`` roda o 2º dry-run e avalia as duas condições do gate G0; nunca imprime material de chave — só contadores, o ``kid`` de 8 chars e nomes de coluna."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# `python3 dev/fernet_rotation_gate.py` põe `dev/` no sys.path, não a raiz —
# sem isto, `import backend.app...` quebra com ModuleNotFoundError (mesmo
# padrão de dev/drill_seed.py e dev/restore_drill.py).
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MIN_KEYS_FOR_WINDOW = 2

# O sentinel ADR-231 guarda um booleano JSON. `->>` devolve TEXTO 'true' no
# Postgres e o INTEIRO 1 no sqlite — comparar com o literal errado casa zero
# linhas e a auditoria sai "limpa" sem ter olhado nada. Medido em 2026-07-31:
# a forma Postgres contra o sqlite do dogfood devolvia vazio com 11.722
# artifacts cifrados presentes. Uma query por dialeto, não uma "portável".
_KID_AUDIT_SQL = {
    "sqlite": (
        "SELECT content_json->>'kid' AS kid, count(*) AS n\n"
        "FROM pipeline_artifacts\n"
        "WHERE content_json->>'_encrypted' = 1\n"
        "GROUP BY 1 ORDER BY n DESC;"
    ),
    "postgres": (
        "SELECT content_json->>'kid' AS kid, count(*) AS n\n"
        "FROM pipeline_artifacts\n"
        "WHERE content_json->>'_encrypted' = 'true'\n"
        "GROUP BY 1 ORDER BY n DESC;"
    ),
}


def kid_audit_sql(is_sqlite: bool) -> str:
    return _KID_AUDIT_SQL["sqlite" if is_sqlite else "postgres"]


class PreflightError(RuntimeError):
    """Janela de rotação fechada ou vault não configurado."""


# ─── introspecção (lazy: `--help` não pode exigir MATHOMS_FERNET_KEY) ───


def key_window() -> tuple[int, str]:
    """(nº de chaves ativas, kid da primária). O kid é sha256[:8] — fingerprint, não chave."""
    from backend.app.services.security.crypto import _key_id
    from backend.app.services.security.vault import resolve_fernet_keys

    return len(resolve_fernet_keys()), _key_id()


# Duplicada de propósito: `_key_id()` só sabe falar da primária, e o que
# interessa aqui é o `kid` da chave do FALLBACK. O teste
# `test_kid_of_bate_com_o_key_id_do_crypto` amarra as duas fórmulas.
def kid_of(key: str) -> str:
    """`kid` de uma chave qualquer — mesma fórmula de `crypto._key_id` (sha256[:8])."""
    return hashlib.sha256(key.encode()).hexdigest()[:8]


def fallback_kid() -> str:
    """`kid` de MATHOMS_FERNET_KEY (a singular), ou "" se não estiver setada."""
    from backend.app.core.config import settings

    single = (settings.FERNET_KEY or "").strip()
    return kid_of(single) if single else ""


def artifact_kid_inventory() -> dict[str, int]:
    """{kid: nº de artifacts cifrados}. Responde "a janela ainda serve para alguma coisa?"."""
    from sqlalchemy import text

    from backend.app.core.database import SyncSessionLocal

    _, sqlite_path = db_target()
    with SyncSessionLocal() as session:
        rows = session.execute(text(kid_audit_sql(is_sqlite=sqlite_path is not None))).all()
    return {(kid or "<sem kid>"): n for kid, n in rows}


def run_task(dry_run: bool) -> dict:
    """Chama a task em processo (não via broker): report determinístico, sem depender do worker."""
    from backend.app.tasks.rotate_fernet_secrets import rotate_fernet_secrets

    return rotate_fernet_secrets(dry_run=dry_run)


def db_target() -> tuple[str, Path | None]:
    """(alvo sem credencial, caminho do arquivo se sqlite) — absoluto de propósito."""
    # Com um `mathoms.db` na raiz e vários worktrees por perto, "qual arquivo?"
    # é a pergunta que importa; caminho relativo não responde.
    from urllib.parse import urlparse

    from backend.app.core.config import settings

    parsed = urlparse(settings.DATABASE_URL)
    if parsed.scheme.startswith("sqlite"):
        # `sqlite:////abs/path` → urlparse devolve `//abs/path`; tirar UMA barra
        # (lstrip("/") comeria as duas e transformaria o absoluto em relativo).
        raw = parsed.path or ""
        path = Path(raw[1:] if raw.startswith("//") else raw)
        return f"sqlite {path}", path
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.hostname or '?'}{port}/{(parsed.path or '/').lstrip('/') or '?'}", None


def sqlite_problem(path: Path | None) -> str | None:
    """Sqlite ausente ou vazio = quase sempre worktree/diretório errado."""
    # Sintoma traiçoeiro: `rotate` diria "nada a rotacionar" com total
    # confiança sobre um banco que não é o seu.
    if path is None:
        return None
    if not path.exists():
        return (
            f"o arquivo `{path}` NÃO existe. Você provavelmente está rodando de um "
            "worktree ou de outro diretório — rode da raiz do repo que hospeda o "
            "banco do dogfood."
        )
    if path.stat().st_size == 0:
        return f"o arquivo `{path}` está vazio (0 bytes) — não é o banco do dogfood."
    return None


# ─── avaliação pura (testável offline com report sintético) ───


def summarize(report: dict) -> dict[str, int]:
    totals = {"rotated": 0, "skipped": 0, "failed": 0, "plaintext": 0, "plaintext_after_cutover": 0}
    for counts in (report.get("targets") or {}).values():
        for key in totals:
            totals[key] += counts.get(key, 0)
    return totals


def _window_problem(keys_configured: int) -> str | None:
    if keys_configured >= MIN_KEYS_FOR_WINDOW:
        return None
    return (
        f"janela de rotação FECHADA ({keys_configured} chave ativa): com só a chave "
        "atual, valor cifrado com a chave antiga não decifra e é contado como "
        "`skipped` — o report sai limpo sem provar nada (falso-limpo)"
    )


def _failed_problem(totals: dict[str, int]) -> str | None:
    if totals["failed"] == 0:
        return None
    return (
        f"failed={totals['failed']}: há valor que não decifra com NENHUMA chave ativa. "
        "Investigue pelo log (`fernet rotation: artifact undecryptable`, com "
        "artifact_id/kid_stored) — não feche o gate"
    )


def _residue_problem(totals: dict[str, int]) -> str | None:
    if totals["rotated"] == 0:
        return None
    return (
        f"rotated={totals['rotated']} no 2º passe: sobrou coluna na chave antiga. "
        "A task é resumível — rode o passe real de novo até este número zerar"
    )


# `resolve_fernet_keys` é `FERNET_KEYS or FERNET_KEY`. Durante a janela o runbook
# manda deixar a singular intocada (passo 2), então ela guarda a chave VELHA.
# Enquanto a CSV existe ela mascara isso e tudo funciona; a ação intuitiva de
# "fechar a janela" apagando só a CSV torna a velha efetiva e nenhuma linha do
# corpus decifra mais.
def fallback_problem(primary_kid: str, fallback: str) -> str | None:
    """A armadilha do passo 7: esvaziar FERNET_KEYS cai no fallback, que é a chave ANTIGA."""
    if not fallback or fallback == primary_kid:
        return None
    return (
        f"ARMADILHA: MATHOMS_FERNET_KEY (kid {fallback}) NÃO é a chave primária "
        f"(kid {primary_kid}). Hoje MATHOMS_FERNET_KEYS a mascara. Apagar a CSV "
        "sem antes reescrever a singular faz o vault cair na chave ANTIGA e TODO "
        "o corpus cifrado fica ilegível. Feche a janela com as DUAS edições "
        "juntas (runbook fernet_rotation.md §7)"
    )


# Critério derivado de ESTADO, não de relógio: não há timestamp confiável de
# quando a janela abriu, mas "não sobrou linha para rotacionar" é medível.
def stale_window_problem(inventory: dict[str, int], primary_kid: str) -> str | None:
    """Janela aberta sem nada fora da primária = já cumpriu a função; deve fechar."""
    leftover = {kid: n for kid, n in inventory.items() if kid not in (primary_kid, "<sem kid>")}
    if leftover:
        return None
    total = inventory.get(primary_kid, 0)
    return (
        f"janela de rotação ABERTA sem função: {total} artifacts cifrados, todos já "
        f"na primária (kid {primary_kid}), zero na antiga. A rotação terminou — o "
        "passo 7 do runbook (fechar a janela) está pendente"
    )


# `evaluate` só lia `rotated`/`failed`; um DB com o schema e ZERO linhas (o que
# `alembic upgrade head` produz, e o que se pega ao rodar de um worktree) fechava
# com "GATE OK ... failed=0 rotated=0" e ainda imprimia a string de confirmação do
# G0 — indistinguível de um passe real, exceto pelo `skipped` que ninguém lia. O
# passe real de 2026-07-31 tinha skipped=12150; a isca tinha skipped=0.
def empty_corpus_problem(totals: dict[str, int]) -> str | None:
    """Report todo-zero = o gate não olhou nada. Medido em 2026-08-19."""
    if sum(totals.values()) > 0:
        return None
    return (
        "report todo-zero: nenhum valor cifrado foi sequer inspecionado. O alvo "
        "não tem material cifrado (banco errado, vazio, ou recém-migrado). O gate "
        "não fecha sobre um banco que ele não leu — confira `banco alvo` acima"
    )


# O absoluto (`plaintext`) fecha para sempre depois do backfill e viraria regra
# morta; o recorte de recência não fecha, porque 0 é o estado estacionário e
# qualquer não-zero é drift de config vivo. Gate no recorte, absoluto na métrica.
def plaintext_problem(totals: dict[str, int]) -> str | None:
    """Row em plaintext escrita DEPOIS do cutover de encryption não fecha o gate."""
    recentes = totals.get("plaintext_after_cutover", 0)
    if recentes == 0:
        return None
    return (
        f"plaintext_after_cutover={recentes}: há artifact gravado em claro DEPOIS do "
        "cutover de encryption. Não é resíduo histórico — é ENCRYPT_PIPELINE_ARTIFACTS "
        "desligada ou writer contornando DBArtifactStore.write (ADR-231)"
    )


def evaluate(report: dict, keys_configured: int, expect_idle: bool) -> list[str]:
    """Problemas que impedem o gate de fechar; lista vazia = passou."""
    totals = summarize(report)
    found = [
        _window_problem(keys_configured),
        empty_corpus_problem(totals),
        plaintext_problem(totals),
        _failed_problem(totals),
    ]
    if expect_idle:
        found.append(_residue_problem(totals))
    return [p for p in found if p]


def format_report(report: dict) -> str:
    lines = [f"{'target':<45}{'rotated':>9}{'skipped':>9}{'failed':>8}{'plain':>7}"]
    lines.append("-" * 78)
    for target, counts in sorted((report.get("targets") or {}).items()):
        lines.append(
            f"{target[:44]:<45}{counts.get('rotated', 0):>9}"
            f"{counts.get('skipped', 0):>9}{counts.get('failed', 0):>8}"
            f"{counts.get('plaintext', 0):>7}"
        )
    totals = summarize(report)
    lines.append("-" * 78)
    lines.append(
        f"{'TOTAL':<45}{totals['rotated']:>9}{totals['skipped']:>9}"
        f"{totals['failed']:>8}{totals['plaintext']:>7}"
    )
    return "\n".join(lines)


# ─── comandos ───


def _require_real_target() -> str:
    """Mostra QUAL banco será reescrito, antes de qualquer coisa."""
    # Sem gate "local × produção" de propósito: a única instância com dado real
    # é o dogfood local (prod owner-gated, ADR-228 G2/G3), então bloquear alvo
    # local barraria o uso legítimo — engano da 1ª versão deste guard (#1129).
    # O engano que importa é apontar para o banco ERRADO; é isso que se checa.
    target, sqlite_path = db_target()
    print(f"banco alvo:    {target}")
    if sqlite_path and sqlite_path.exists():
        print(f"tamanho:       {sqlite_path.stat().st_size / 1e6:.0f} MB")
    problem = sqlite_problem(sqlite_path)
    if problem:
        raise PreflightError(problem)
    return target


def _require_window() -> tuple[int, str]:
    _require_real_target()
    keys, kid = key_window()
    print(f"chaves ativas: {keys} · kid da primária: {kid}")
    if keys < MIN_KEYS_FOR_WINDOW:
        raise PreflightError(
            "janela FECHADA — abra antes de qualquer dry-run. No `.env`:\n"
            "  MATHOMS_FERNET_KEYS=<chave_nova>,<chave_antiga>\n"
            "(a nova PRIMEIRO), e reinicie o que estiver rodando — API e worker\n"
            "precisam ler o mesmo conjunto de chaves."
        )
    return keys, kid


def cmd_preflight(args) -> int:
    _require_window()
    print("OK — janela aberta. O dry-run agora é confiável.")
    return 0


def cmd_rotate(args) -> int:
    keys, _ = _require_window()
    print("\n── dry-run (nada é escrito) ──")
    report = run_task(dry_run=True)
    print(format_report(report))
    problems = evaluate(report, keys, expect_idle=False)
    if problems:
        return _fail(problems)
    if summarize(report)["rotated"] == 0:
        print("\nNada a rotacionar — tudo já está na chave primária.")
        return 0
    if not args.yes and not _confirm(summarize(report)["rotated"]):
        print("abortado pelo operador.")
        return 1
    print("\n── passe real ──")
    print(format_report(run_task(dry_run=False)))
    print("\nAgora rode `verify` para fechar o gate.")
    return 0


def cmd_verify(args) -> int:
    keys, kid = _require_window()
    _, sqlite_path = db_target()
    report = json.loads(args.report.read_text()) if args.report else run_task(dry_run=True)
    print("\n── 2º dry-run (prova de que nada ficou para trás) ──")
    print(format_report(report))
    problems = evaluate(report, keys, expect_idle=True)
    if problems:
        return _fail(problems)
    print(f"\nGATE OK — failed=0 e rotated=0 com a janela aberta (kid {kid}).")
    print("\nConfirmação para o gate G0 (cole só isto — sem chave, sem valor):")
    totals = summarize(report)
    print(
        f"  rotação Fernet: failed={totals['failed']} rotated={totals['rotated']} "
        f"skipped={totals['skipped']} · 2º passe · kid={kid}"
    )
    print(f"\nIntegridade dos artifacts — rode e confira que só aparece o kid {kid}:\n")
    print(kid_audit_sql(is_sqlite=sqlite_path is not None))
    return 0


def _print_inventory(inventory: dict[str, int], primary_kid: str) -> None:
    print(f"\n{'kid':<12}{'artifacts':>10}  papel")
    print("-" * 52)
    for kid, n in sorted(inventory.items(), key=lambda kv: -kv[1]):
        papel = "PRIMÁRIA (encrypt)" if kid == primary_kid else "CHAVE ANTIGA — re-encrypt pendente"
        print(f"{kid:<12}{n:>10}  {papel}")


# `_key_id()` hasheia a string vazia e devolve um kid de aparência legítima
# (e3b0c442); comparar qualquer coisa com ele é ruído, não diagnóstico.
def _require_any_key(keys: int) -> None:
    """Sem chave nenhuma configurada não há janela para auditar."""
    if keys:
        return
    raise PreflightError(
        "nenhuma chave Fernet configurada — MATHOMS_FERNET_KEY/KEYS ausentes "
        "no ambiente. Rode da raiz do repo que hospeda o `.env`"
    )


def window_problems(
    primary_kid: str, fallback: str, inventory: dict[str, int], keys: int
) -> list[str]:
    """Problemas do estado da janela; lista vazia = coerente. `stale` só faz sentido em janela."""
    found = [fallback_problem(primary_kid, fallback)]
    if keys >= MIN_KEYS_FOR_WINDOW:
        found.append(stale_window_problem(inventory, primary_kid))
    return [p for p in found if p]


def cmd_window(args) -> int:
    """Audita o estado da janela: a armadilha do fallback e se a janela ainda serve."""
    _require_real_target()
    keys, kid = key_window()
    _require_any_key(keys)
    fallback = fallback_kid()
    print(f"chaves ativas: {keys} · kid da primária: {kid}")
    print(f"MATHOMS_FERNET_KEY (fallback): {'não setada' if not fallback else 'kid ' + fallback}")
    inventory = artifact_kid_inventory()
    _print_inventory(inventory, kid)
    problems = window_problems(kid, fallback, inventory, keys)
    if problems:
        return _fail(problems)
    print("\nOK — sem armadilha de fallback e a janela está coerente com o corpus.")
    return 0


def _confirm(pending: int) -> bool:
    prompt = f"\nRotacionar {pending} valor(es) agora? Digite 'rotacionar' para confirmar: "
    return input(prompt).strip() == "rotacionar"


def _fail(problems: list[str]) -> int:
    print("\nGATE BLOQUEADO:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("preflight", help="a janela de rotação está aberta?")
    sub.add_parser("window", help="a janela deveria estar fechada? há armadilha de fallback?")
    rotate = sub.add_parser("rotate", help="dry-run → confirmação → passe real")
    rotate.add_argument("--yes", action="store_true", help="pula a confirmação interativa")
    verify = sub.add_parser("verify", help="2º dry-run + as duas condições do gate")
    verify.add_argument("--report", type=Path, help="avalia um report JSON já salvo")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    handler = {
        "preflight": cmd_preflight,
        "window": cmd_window,
        "rotate": cmd_rotate,
        "verify": cmd_verify,
    }[args.cmd]
    try:
        return handler(args)
    except PreflightError as exc:
        return _fail([str(exc)])


if __name__ == "__main__":
    raise SystemExit(main())
