"""E5.N re-resolve a seção tributária em stage-time (RV3-11 · A40.l9 PR2)."""

from __future__ import annotations

from scripts.generate_narratives import _e5n_refresh_tributario


class _Ctx:
    def __init__(self, resolver, workspace_id="ws-1"):
        self.tributario_section_resolver = resolver
        self.workspace_id = workspace_id


class _Resolver:
    def __init__(self, section):
        self._section = section
        self.calls: list[str] = []

    def resolve(self, workspace_id):
        self.calls.append(workspace_id)
        return self._section


def test_resolver_presente_sobrescreve_o_materializado():
    goals = {"tributario": {"cascata": {"receita_bruta": 0.0}}, "aportes": {"x": 1}}
    fresh = {"cascata": {"receita_bruta": 240000.0}}
    resolver = _Resolver(fresh)

    _e5n_refresh_tributario(_Ctx(resolver), goals)

    assert goals["tributario"] == fresh, "o t=0 materializado deveria ceder ao stage-time"
    assert goals["aportes"] == {"x": 1}, "só a seção tributária muda"
    assert resolver.calls == ["ws-1"]


def test_resolver_ausente_preserva_o_materializado():
    goals = {"tributario": {"cascata": {"receita_bruta": 1.0}}}
    _e5n_refresh_tributario(_Ctx(None), goals)
    assert goals["tributario"] == {"cascata": {"receita_bruta": 1.0}}


def test_resolver_indisponivel_preserva_o_materializado():
    goals = {"tributario": {"cascata": {"receita_bruta": 1.0}}}
    _e5n_refresh_tributario(_Ctx(_Resolver(None)), goals)
    assert goals["tributario"] == {"cascata": {"receita_bruta": 1.0}}


def test_sem_workspace_id_nao_chama_o_resolver():
    resolver = _Resolver({"cascata": {}})
    _e5n_refresh_tributario(_Ctx(resolver, workspace_id=None), {"tributario": {}})
    assert resolver.calls == []
