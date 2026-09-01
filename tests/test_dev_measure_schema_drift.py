"""Gate do flip warn→strict: o instrumento mede pela chave do gate e não chama GO sem massa (ADR-284 · A40.l58)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from dev.measure_schema_drift import SchemaDrift, _measure, _window_start

SCHEMA_OF = {"E2": "e2_extract.schema.json"}


def _resolve(stage: str, key: str):
    """Resolver por `(stage, key)` — a assinatura que o instrumento usa (A42.l19)."""
    return SCHEMA_OF.get(stage)


def _measure_r(rows):
    return _measure(rows, _resolve)


def _row(payload: dict, *, run: str = "run-1", key: str = "art-1", created: str = "2026-08-18"):
    return SimpleNamespace(
        stage="E2",
        content_json=json.dumps(payload),
        created_at=created,
        pipeline_run_id=run,
        document_id=None,
        artifact_key=key,
    )


def _e2_payload(**overrides) -> dict:
    """Shape mínimo que o `e2_extract.schema.json` aceita; `overrides` remove/força campo."""
    payload = {"banco": "itau", "tipo": "extrato", "moeda": "BRL", "transacoes": []}
    payload.update(overrides)
    for field, value in list(overrides.items()):
        if value is None:
            payload.pop(field, None)
    return payload


class TestVeredito:
    def test_schema_sem_massa_nao_e_go(self):
        """Zero artefato não é 'zero WARN' — é ausência de medição (a janela de 7d pode não ter run)."""
        assert SchemaDrift().is_go is False

    def test_massa_sem_drift_e_go(self):
        stats = SchemaDrift()
        stats.artifacts = 5
        assert stats.is_go is True

    def test_um_drift_derruba_o_go(self):
        stats = SchemaDrift()
        stats.artifacts, stats.drifted = 5, 1
        assert stats.is_go is False


class TestJanela:
    def test_since_explicito_vence_days(self):
        assert _window_start(7, "2026-01-01", "2026-08-18") == "2026-01-01"

    def test_days_conta_do_write_mais_recente_e_inclui_o_dia(self):
        assert _window_start(7, None, "2026-08-18") == "2026-08-12"

    def test_sem_corpus_nao_ha_janela(self):
        assert _window_start(7, None, None) is None


class TestMedicao:
    def test_payload_valido_nao_drifta(self):
        results = _measure_r([_row(_e2_payload())])
        assert results["e2_extract.schema.json"].is_go is True

    @pytest.mark.parametrize("faltante", ["banco", "moeda"])
    def test_path_emitido_e_o_mesmo_da_telemetria(self, faltante: str):
        """Regressão do drift real medido em 2026-08-24: o stub de `generate_llm_fallback`
        entra sem `banco`/`moeda`. O path tem de ser o campo, não a raiz `$` — é a chave
        que o go/no-go do runbook agrega."""
        results = _measure_r([_row(_e2_payload(**{faltante: None}))])
        stats = results["e2_extract.schema.json"]
        assert stats.drifted == 1
        assert (f"$.{faltante}", "required") in stats.paths

    def test_conta_run_e_payload_distintos(self):
        """Separa massa real de repetição por run (cláusula do §B da [[ADR-409]])."""
        # A versão anterior media `documents` e passava SÓ porque a `artifact_key` era
        # a mesma: `document_id` é NULL em 100% do corpus. Terceira instância, nesta
        # sprint, de teste que concorda com a crença errada do código.
        rows = [_row(_e2_payload(), run=f"run-{i}", key="mesmo-doc") for i in range(3)]
        stats = _measure_r(rows)["e2_extract.schema.json"]
        assert (stats.artifacts, len(stats.runs), len(stats.payloads)) == (3, 3, 1)

    def test_payload_ilegivel_conta_separado_e_nao_vira_drift(self):
        row = _row(_e2_payload())
        row.content_json = "{nao é json"
        stats = _measure_r([row])["e2_extract.schema.json"]
        assert (stats.unreadable, stats.drifted) == (1, 0)
        assert stats.is_go is False

    def test_stage_sem_schema_mapeado_e_ignorado(self):
        """Passthrough (E6-parecer, extract_members) não entra na conta — não há contrato a medir."""
        row = _row(_e2_payload())
        row.stage = "review_finances_holistic"
        assert _measure_r([row]) == {}


class TestResolucaoPorChave:
    """A42.l19 — o instrumento mede pelo schema que o guard de escrita aplicaria."""

    # Com resolução por stage, os 7 baldes do E4 bateriam contra o backstop `anyOf` e
    # sairiam `GO` sem nenhum contrato ter sido checado: falso-verde no próprio
    # instrumento que gateia a fila do flip `warn→strict` (ADR-409).

    def test_baldes_do_mesmo_stage_vao_para_schemas_diferentes(self):
        from backend.app.services.storage.db_artifact_store import resolve_schema_name

        rows = [
            _row(_e2_payload(), key="receitas"),
            _row(_e2_payload(), key="patrimonio"),
        ]
        for row in rows:
            row.stage = "E4"

        medido = _measure(rows, resolve_schema_name)

        assert set(medido) == {
            "e4_cashflow.schema.json",
            "baseline_patrimonial.schema.json",
        }, "instrumento colapsou baldes distintos num schema só"

    def test_resolucao_por_stage_colapsaria_os_dois(self):
        """Controle: a assinatura antiga (por stage) não discrimina — é o defeito."""
        rows = [
            _row(_e2_payload(), key="receitas"),
            _row(_e2_payload(), key="patrimonio"),
        ]
        for row in rows:
            row.stage = "E4"

        medido = _measure(rows, lambda stage, key: "e4_unified.schema.json")

        assert set(medido) == {"e4_unified.schema.json"}
        assert medido["e4_unified.schema.json"].artifacts == 2


class TestMassaPorPayloadDistinto:
    """A42.l19 — `documents` degenerava para `artifact_key` (document_id NULL em 100%)."""

    def test_copias_identicas_contam_como_uma_evidencia(self):
        rows = [_row(_e2_payload(), key="pontos_milhas", run=f"run-{i}") for i in range(9)]

        stats = _measure_r(rows)["e2_extract.schema.json"]

        assert stats.artifacts == 9
        assert len(stats.payloads) == 1, "9 cópias byte-idênticas não são 9 evidências"

    def test_massa_trivial_nao_muda_o_go_nem_o_exit(self):
        """Massa é insumo de decisão, não gate de drift — trocar por vermelho trocaria
        falso-verde por falso-vermelho no CI."""
        rows = [_row(_e2_payload(), key="k", run=f"run-{i}") for i in range(9)]

        stats = _measure_r(rows)["e2_extract.schema.json"]

        assert stats.is_go is True
        assert stats.mass_trivial is True

    def test_payloads_distintos_contam_separado(self):
        rows = [_row(_e2_payload(banco=f"b{i}"), key="k", run=f"run-{i}") for i in range(4)]

        stats = _measure_r(rows)["e2_extract.schema.json"]

        assert len(stats.payloads) == 4
        assert stats.mass_trivial is False

    def test_documents_sumiu_da_saida(self):
        """Não basta parar de usar: parar de reportar. Campo que sobrevive na saída é
        campo que a próxima pessoa cita."""
        stats = _measure_r([_row(_e2_payload())])["e2_extract.schema.json"]

        assert not hasattr(stats, "documents")


# O §F recusa promover schema cujo contrato descreve 5/13 do payload, mas a
# elegibilidade é só a medição: bastava o drift ir a 0 para o predicado dizer `GO`.
# O PR-A levou `baseline_patrimonial` de 59,8% a 3,6%, e o resto é defeito de dado
# de outra lane — o número fica verde antes de o contrato ficar real.
class TestContratoNaoDerivado:
    """A40.l110 — drift zero sobre contrato irreal é o falso-verde da [[ADR-409]] §F."""

    def test_schema_listado_nunca_e_go_mesmo_sem_drift(self):
        from dev.measure_schema_drift import _CONTRATO_NAO_DERIVADO, SchemaDrift

        alvo = next(iter(_CONTRATO_NAO_DERIVADO))
        stats = SchemaDrift(nome=alvo)
        stats.artifacts, stats.drifted, stats.unreadable = 10, 0, 0

        assert stats.is_go is False
        assert stats.contrato_nao_derivado

    def test_o_bloqueio_e_o_que_derruba_o_go_e_nao_outra_coisa(self):
        # Sem este par, o teste acima passaria por qualquer razão — massa zero,
        # ilegível, drift — e não provaria que a lista é o que decide.
        """Não-inércia: o MESMO contador, sem o nome listado, é `GO`."""
        from dev.measure_schema_drift import SchemaDrift

        stats = SchemaDrift(nome="schema-que-ninguem-bloqueou.schema.json")
        stats.artifacts, stats.drifted, stats.unreadable = 10, 0, 0

        assert stats.is_go is True

    # A40.l110 closeout — a 1ª versão deste teste fazia `stats.drifted = 0` e depois
    # `assert stats.drifted == 0`: afirmava a própria atribuição, nunca chamava `main`.
    # O exit code é do `main`, então é o `main` que tem de ser medido.
    def test_bloqueio_nao_muda_o_exit_code_do_gate(self, monkeypatch, capsys):
        """Contrato incompleto é insumo de decisão, não drift (idem `mass_trivial`)."""
        from dev import measure_schema_drift as m

        alvo = next(iter(m._CONTRATO_NAO_DERIVADO))
        stats = m.SchemaDrift(nome=alvo)
        stats.artifacts, stats.drifted, stats.unreadable = 10, 0, 0
        self._stub_corpus(monkeypatch, m, {alvo: stats})

        assert m.main(["--gate"]) == 0, "veredito de contrato não pode pintar o CI de vermelho"
        assert "NO-GO (contrato)" in capsys.readouterr().out

    def test_drift_de_verdade_ainda_derruba_o_exit_code(self, monkeypatch, capsys):
        """Não-inércia do teste acima: com `drifted` > 0 o mesmo caminho sai 1."""
        from dev import measure_schema_drift as m

        alvo = next(iter(m._CONTRATO_NAO_DERIVADO))
        stats = m.SchemaDrift(nome=alvo)
        stats.artifacts, stats.drifted, stats.unreadable = 10, 1, 0
        self._stub_corpus(monkeypatch, m, {alvo: stats})

        assert m.main(["--gate"]) == 1

    def test_toda_chave_bloqueada_e_um_schema_que_existe(self):
        """Rename/typo na chave torna o bloqueio inerte, e o veredito volta a `GO` calado."""
        import scripts.pipeline_common as pipeline_common
        from dev.measure_schema_drift import _CONTRATO_NAO_DERIVADO

        for nome in _CONTRATO_NAO_DERIVADO:
            caminho = pipeline_common.CONFIG_DIR / "schemas" / nome
            assert caminho.exists(), f"{nome} não casa arquivo em config/schemas/"

    @staticmethod
    def _stub_corpus(monkeypatch, modulo, resultados):
        """Isola `main` do DB: o que se mede aqui é o exit code, não a leitura do corpus."""
        monkeypatch.setattr(modulo, "_collect", lambda args: (resultados, None, None))

    def test_toda_razao_nomeia_quem_levanta_o_bloqueio(self):
        """Bloqueio sem condição de retomada apodrece: vira 'sempre foi assim'."""
        from dev.measure_schema_drift import _CONTRATO_NAO_DERIVADO

        assert _CONTRATO_NAO_DERIVADO
        for nome, razao in _CONTRATO_NAO_DERIVADO.items():
            assert "[[" in razao, f"{nome}: a razão precisa apontar a lane/ADR que levanta"
