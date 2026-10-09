"""PR do Dependabot parado — idade da cadeia de substituição.

O incidente que motiva: isento do stale (fechar PR do Dependabot vira ignore da
release), PR que ninguém mergeia ocupa o `open-pull-requests-limit` para sempre e
trava calado os version updates da entrada. O Dependabot substitui o PR a cada release
nova, então a idade do PR zera e só a cadeia envelhece."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from dev import ci_dependabot_health as health
from dev import ci_dependabot_stuck_prs as mod

DIRS = {
    "pip": ["/", "/backend"],
    "npm_and_yarn": ["/frontend", "/frontend-ops"],
    "docker": [
        "/",
        "/pipeline-service",
        "/frontend",
        "/frontend-ops",
        "/services/pipeline-service-go",
    ],
    "github_actions": ["/"],
}
X = health.STUCK_PR_AGE


def _raw(number: int, branch: str, created: str, closed: str | None = None, merged=False):
    return {
        "number": number,
        "url": f"https://github.com/davidrobert/mathoms/pull/{number}",
        "headRefName": f"dependabot/{branch}",
        "createdAt": created,
        "closedAt": closed,
        "mergedAt": closed if merged else None,
    }


def _prs(*raws: dict) -> list[mod.DependabotPr]:
    return [mod.parse_pr(r, DIRS) for r in raws]


def _now(stamp: str) -> datetime:
    return datetime.fromisoformat(stamp)


# Cadeia REAL do `next` em /frontend (medida em 2026-10-09): cada release nova fecha o PR
# e abre outro — #2025 → #2037 → #2039 —, e nenhum passa de 7,4 dias de idade própria.
NEXT_CHAIN = (
    _raw(2025, "npm_and_yarn/frontend/next-16.3.6", "2026-09-29T00:12:00Z", "2026-10-06T09:23:31Z"),
    _raw(2037, "npm_and_yarn/frontend/next-16.3.8", "2026-10-06T09:23:26Z", "2026-10-08T00:10:57Z"),
    _raw(2039, "npm_and_yarn/frontend/next-16.4.0", "2026-10-08T00:10:53Z"),
)


@pytest.mark.parametrize(
    ("branch", "expected"),
    [
        ("npm_and_yarn/frontend/next-16.4.0", ("npm_and_yarn", "/frontend", "next")),
        (
            "npm_and_yarn/frontend-ops/ops-patch-and-minor-4c9780600f",
            ("npm_and_yarn", "/frontend-ops", "ops-patch-and-minor"),
        ),  # fmt: skip
        ("pip/litellm-gte-1.104.0", ("pip", "/", "litellm-gte")),
        ("pip/backend/httpx-gte-0.28.1", ("pip", "/backend", "httpx-gte")),
        ("github_actions/astral-sh/setup-uv-10.2.0", ("github_actions", "/", "astral-sh/setup-uv")),
        (
            "docker/services/pipeline-service-go/docker-version-6dafb4a59b",
            ("docker", "/services/pipeline-service-go", "docker-version"),
        ),  # fmt: skip
        (
            "npm_and_yarn/frontend/hono/node-server-1.19.17",
            ("npm_and_yarn", "/frontend", "hono/node-server"),
        ),
        (
            "docker/pipeline-service/docker-version-6dafb4a59b",
            ("docker", "/pipeline-service", "docker-version"),
        ),
        (
            "docker/services/pipeline-service-go/docker-version-6dafb4a59b",
            ("docker", "/services/pipeline-service-go", "docker-version"),
        ),
        (
            "npm_and_yarn/frontend/multi-04e1cc7ff2",
            ("npm_and_yarn", "/frontend", "multi-04e1cc7ff2"),
        ),
        (
            "go_modules/services/pipeline-service-go/go_modules-ab12cd34ef",
            ("go_modules", None, "services/pipeline-service-go/go_modules"),
        ),  # fmt: skip
    ],
)
def test_branch_resolve_entrada_por_maior_prefixo_e_chave_sem_versao(branch, expected):
    pr = _prs(_raw(1, branch, "2026-10-09T11:00:00Z"))[0]
    assert (pr.ecosystem, pr.directory, pr.key) == expected


def test_contrafactual_cadeia_real_do_next_envelhece_onde_o_pr_nao():
    prs = _prs(*NEXT_CHAIN)
    stuck = mod.stuck_prs(prs, _now("2026-10-08T12:00:00+00:00"), X)
    assert [(s.pr.number, s.since) for s in stuck] == [(2039, _now("2026-09-29T00:12:00+00:00"))]


def test_controle_negativo_sem_os_elos_o_mesmo_pr_e_jovem():
    prs = _prs(NEXT_CHAIN[2])
    assert mod.stuck_prs(prs, _now("2026-10-08T12:00:00+00:00"), X) == []


def test_contrafactual_lote_de_09_07_avisa_no_domingo_antes_da_run_seguinte():
    """#2006–#2010 (pip `/`) nasceram na run de segunda 09-07 e o stale os fechou em 09-29,
    a 21,9 dias. O cron das 02:00 UTC de domingo 09-13 avisa antes da run de 09-14."""
    raws = [_raw(n, f"pip/dep{n}-gte-1.0.0", "2026-09-07T09:17:00Z") for n in range(2006, 2011)]
    assert mod.stuck_prs(_prs(*raws), _now("2026-09-12T02:00:00+00:00"), X) == []
    stuck = mod.stuck_prs(_prs(*raws), _now("2026-09-13T02:00:00+00:00"), X)
    assert [s.pr.number for s in stuck] == [2006, 2007, 2008, 2009, 2010]


def test_merge_interrompe_a_cadeia():
    prs = _prs(
        _raw(
            1978,
            "npm_and_yarn/frontend/fast-uri-3.1.6",
            "2026-08-20T09:00:00Z",
            "2026-09-02T18:21:00Z",
            merged=True,
        ),  # fmt: skip
        _raw(1997, "npm_and_yarn/frontend/fast-uri-3.1.7", "2026-09-02T18:21:02Z"),
    )
    assert mod.stuck_prs(prs, _now("2026-09-05T00:00:00+00:00"), X) == []


def test_fechamento_longe_da_criacao_nao_e_substituicao():
    """#2012 (jsdom) fechado pelo stale em 09-29; #2133 só nasceu em 10-09: cadeia nova."""
    prs = _prs(
        _raw(
            2012,
            "npm_and_yarn/frontend/jsdom-30.0.1",
            "2026-09-07T09:00:00Z",
            "2026-09-29T06:53:15Z",
        ),
        _raw(2133, "npm_and_yarn/frontend/jsdom-30.1.2", "2026-10-09T11:09:50Z"),
    )
    assert mod.stuck_prs(prs, _now("2026-10-12T00:00:00+00:00"), X) == []


@pytest.mark.parametrize(
    "other",
    [
        "npm_and_yarn/frontend/vitest-5.0.3",  # outra dep, mesma entrada, mesmo minuto
        "npm_and_yarn/frontend-ops/next-16.3.8",  # mesma dep, outra entrada
    ],
)
def test_elo_exige_mesma_entrada_e_mesma_dep(other):
    prs = _prs(
        _raw(1, other, "2026-09-01T00:00:00Z", "2026-10-06T09:23:00Z"),
        _raw(2, "npm_and_yarn/frontend/next-16.3.8", "2026-10-06T09:23:26Z"),
    )
    assert mod.stuck_prs(prs, _now("2026-10-08T00:00:00+00:00"), X) == []


@pytest.mark.parametrize(("gap_s", "linked"), [(-50, True), (6, True), (300, True), (301, False)])
def test_folga_da_substituicao_cobre_o_medido_e_para_em_5_min(gap_s, linked):
    created = _now("2026-10-06T09:23:26+00:00")
    closed = created + timedelta(seconds=gap_s)
    prs = _prs(
        _raw(1, "npm_and_yarn/frontend/next-16.3.6", "2026-09-20T00:00:00Z", closed.isoformat()),
        _raw(2, "npm_and_yarn/frontend/next-16.3.8", created.isoformat()),
    )
    stuck = mod.stuck_prs(prs, _now("2026-10-08T00:00:00+00:00"), X)
    assert bool(stuck) is linked


class FakePrList:
    """Responde `gh pr list` por `--state`, sem rede; registra as chamadas."""

    def __init__(self, opened: list[dict], closed: list[dict]) -> None:
        self.by_state = {"open": opened, "closed": closed}
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, *args: str) -> str:
        self.calls.append(args)
        return json.dumps(self.by_state[args[args.index("--state") + 1]])


def test_fetch_le_abertos_de_qualquer_idade_e_fechados_da_janela():
    """Filtrar por `created:` tiraria da lista o PR aberto mais velho — o pior caso."""
    gh = FakePrList([_raw(1, "pip/x-1.0", "2026-01-01T00:00:00Z")], [])
    mod.fetch_dependabot_prs(gh, _now("2026-07-11T00:00:00+00:00"))
    opened, closed = gh.calls
    assert "--search" not in opened and opened[opened.index("--state") + 1] == "open"
    assert closed[closed.index("--search") + 1] == "closed:>=2026-07-11"
    assert all(c[c.index("--author") + 1] == "app/dependabot" for c in gh.calls)


def test_zero_prs_na_janela_e_instrumento_cego_nao_zero_achados():
    with pytest.raises(ValueError, match="0 PRs do Dependabot"):
        mod.fetch_dependabot_prs(FakePrList([], []), _now("2026-07-11T00:00:00+00:00"))


def test_lista_do_tamanho_do_limite_foi_cortada_e_nao_mede(monkeypatch):
    monkeypatch.setattr(mod, "PR_LIST_LIMIT", 2)
    full = [_raw(n, "pip/x-1.0", "2026-10-01T00:00:00Z") for n in (1, 2)]
    with pytest.raises(ValueError, match="cortada em 2"):
        mod.fetch_dependabot_prs(FakePrList([], full), _now("2026-07-11T00:00:00+00:00"))


def test_multi_com_hash_nao_vira_cadeia_de_deps_diferentes():
    """Sem o hash, `multi` juntaria deps distintas fechadas e abertas na mesma run."""
    prs = _prs(
        _raw(
            1,
            "npm_and_yarn/frontend/multi-04e1cc7ff2",
            "2026-09-01T00:00:00Z",
            "2026-10-06T09:23:00Z",
        ),  # fmt: skip
        _raw(2, "npm_and_yarn/frontend/multi-9a8b7c6d5e", "2026-10-06T09:23:10Z"),
    )
    assert mod.stuck_prs(prs, _now("2026-10-08T00:00:00+00:00"), X) == []


def _occupancy(still_open: int, opened_after: int, closed_after: int) -> mod.Occupancy:
    """Triagem em 10-01: abertos desde antes e ainda abertos; abertos depois; abertos na
    triagem e fechados depois (contam na triagem, não agora)."""
    raws = [_raw(n, f"pip/a{n}-1.0", "2026-09-20T00:00:00Z") for n in range(still_open)]
    raws += [_raw(10 + n, f"pip/b{n}-1.0", "2026-10-05T00:00:00Z") for n in range(opened_after)]
    raws += [
        _raw(20 + n, f"pip/c{n}-1.0", "2026-09-20T00:00:00Z", "2026-10-03T00:00:00Z")
        for n in range(closed_after)
    ]
    return mod.Occupancy(5, tuple(_prs(*raws)))


@pytest.mark.parametrize(
    ("still", "after", "closed", "rearms"),
    [
        (4, 1, 0, True),  # encheu depois da triagem
        (5, 0, 0, False),  # já lotada na triagem: a triagem cobriu
        (3, 1, 0, False),  # não lotou
        (2, 3, 2, True),  # 4 na triagem (2 fecharam depois), 5 agora
        (3, 2, 2, False),  # 5 na triagem, composição mudou, lotação não é fato novo
    ],
)
def test_lotacao_re_arma_so_quando_a_entrada_enche_depois_da_triagem(still, after, closed, rearms):
    occupancy = _occupancy(still, after, closed)
    assert occupancy.filled_since(_now("2026-10-01T00:00:00+00:00")) is rearms
