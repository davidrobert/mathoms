"""Detector de duplicação cross-grupo ([[A40.l1]] · [[ADR-354]]) — chave, casos e partição."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from dev.ledger_cross_group import (  # noqa: E402
    _TX_BUCKET_DIRECTION,
    CrossGroupCollision,
    _cross_group_key,
    _fill_states,
    _row_moeda,
    _row_provenance,
    _unkeyable_reason,
    cross_group_coverage,
    cross_group_double_count,
    cross_group_numerator,
    cross_group_unkeyable,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    buckets as _buckets,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    carrier_adr354 as _carrier_adr354,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    coincidencia_cross_conta as _coincidencia_cross_conta,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    par_divergente as _par_divergente,
)
from tests.unit.pipeline._cross_group_builders import (  # noqa: E402
    tx as _tx,
)

# ───────── os 4 casos do critério de aceite + guardas anti-regressão ─────────


def test_pernas_do_mesmo_evento_com_tipo_conta_variante_detecta() -> None:
    # ADR-354 §Contexto carrier 1: normalize_tipo_conta só ajusta casing/acento,
    # não colapsa vocabulário ("extrato" != "extratoconta") ⇒ triplas distintas.
    hits = cross_group_double_count(_par_divergente(valor=100.0, descricao="compra mercado"))
    assert len(hits) == 1
    assert isinstance(hits[0], CrossGroupCollision)
    assert hits[0].divergence == "tipo_conta"
    assert hits[0].n_provenances == 2
    assert hits[0].n_rows == 2
    assert hits[0].whitelisted is False
    assert hits[0].excess_cents == 10000


def test_transferencia_interna_direction_oposto_nao_detecta() -> None:
    # GUARD: os bancos divergem DE PROPÓSITO. Se fossem iguais, remover `direction`
    # da chave ainda não flagaria (1 tripla) e a guarda seria vacuosa. O valor é
    # 300.0 nas DUAS pernas — a despesa vem de abs(), a receita é positiva —, logo
    # `direction` (derivado do BALDE) é o único discriminador possível aqui.
    buckets = _buckets(
        despesas=[_tx(valor=300.0, descricao="transferencia entre contas", banco="banco a")],
        receitas=[_tx(valor=300.0, descricao="transferencia entre contas", banco="banco b")],
    )
    assert cross_group_double_count(buckets) == []


def test_duas_compras_identicas_mesma_conta_nao_detecta() -> None:
    # GUARD: mesma conta ⇒ mesma tripla de proveniência ⇒ 1 < 2, fora do critério.
    # A fixture é sintética por necessidade: vindo do pipeline real esse par NEM
    # CHEGA ao balde — mesma chave + mesma tripla ⇒ mesmo transaction_hash ⇒ o
    # dedup K4 colapsa. Não existe caminho de produção que produza este payload.
    row = _tx(valor=100.0, descricao="compra mercado")
    assert cross_group_double_count(_buckets(despesas=[dict(row), dict(row)])) == []


def test_mesmo_valor_moedas_distintas_nao_detecta() -> None:
    # GUARD: o `tipo_conta` diverge DE PROPÓSITO. Sem essa divergência, remover
    # `moeda` da chave ainda não flagaria (1 tripla) e a guarda seria vacuosa.
    buckets = _buckets(
        despesas=[
            _tx(valor=100.0, tipo_conta="extrato", moeda="BRL"),
            _tx(valor=100.0, tipo_conta="extratoconta", moeda="USD"),
        ]
    )
    assert cross_group_double_count(buckets) == []


def test_direction_e_o_unico_discriminante_da_transferencia_interna() -> None:
    # GUARD: as chaves das duas pernas diferem SÓ na posição 3 (`direction`) ⇒
    # remover o campo colapsa o par e toda transferência interna vira ocorrência.
    despesa = _tx(valor=300.0, descricao="transferencia entre contas", banco="banco a")
    receita = _tx(valor=300.0, descricao="transferencia entre contas", banco="banco b")
    k_dep = _cross_group_key("debit", despesa)
    k_rec = _cross_group_key("credit", receita)
    msg = "se a chave mudou intencionalmente, revise A40.l1 §Guarda anti-regressão"
    assert k_dep != k_rec, msg
    assert k_dep[0:3] == k_rec[0:3], msg
    assert k_dep[4] == k_rec[4], msg


def test_moeda_e_o_unico_discriminante_do_par_multimoeda() -> None:
    # GUARD: as chaves diferem SÓ na posição 2 (`moeda`).
    k_brl = _cross_group_key("debit", _tx(valor=100.0, moeda="BRL"))
    k_usd = _cross_group_key("debit", _tx(valor=100.0, moeda="USD"))
    msg = "se a chave mudou intencionalmente, revise A40.l1 §Guarda anti-regressão"
    assert k_brl != k_usd, msg
    assert k_brl[0:2] == k_usd[0:2], msg
    assert k_brl[3:] == k_usd[3:], msg


def test_chave_ignora_proveniencia() -> None:
    esquerda = _tx(valor=100.0, banco="banco a", tipo_conta="extrato")
    direita = _tx(
        valor=100.0, banco="banco b", titular="titular exemplo", tipo_conta="faturacartao"
    )
    assert _cross_group_key("debit", esquerda) == _cross_group_key("debit", direita)


def test_chave_muda_com_data_valor_e_descricao() -> None:
    chave = _cross_group_key("debit", _tx(valor=100.0, descricao="compra mercado"))
    assert _cross_group_key("debit", _tx(valor=100.0, data="2026-03-29")) != chave
    assert _cross_group_key("debit", _tx(valor=100.01)) != chave
    assert _cross_group_key("debit", _tx(valor=100.0, descricao="compra farmacia")) != chave


def test_row_moeda_espelha_build_hash_inputs() -> None:
    # RATCHET: o comentário «espelha build_hash_inputs» era afirmação NÃO-verificada —
    # remover `.strip().upper()` mantinha a suíte verde e faria `" usd "` deixar de
    # casar com `"USD"` na mesma chave (sub-detecção silenciosa).
    from pipeline.domain.services._tx_identity import build_hash_inputs

    for bruto in (" usd ", "brl", "BRL", "", None, "eur", "Usd\t"):
        inputs = build_hash_inputs("2026-03-30", "b", "t", "extratoconta", 1.0, bruto, "d")
        assert _row_moeda({"moeda": bruto}) == inputs.moeda, bruto


def test_proveniencia_e_normalizada_antes_de_contar_triplas() -> None:
    # `normalize_*` só ajusta casing/espaço/acento: drift de formatação NÃO cria
    # tripla nova (senão toda conta viraria "grupo-fonte" novo e o numerador
    # inflaria).
    row = {"banco": "C6 Bank", "titular": "Ana", "tipo_conta": "ExtratoConta"}
    assert _row_provenance(row) == ("c6bank", "ana", "extratoconta")


def test_sufixo_de_roteamento_colapsa_as_pernas() -> None:
    # GUARD: prova que a `normalize_descricao` canônica (ADR-255 it.2/it.3) foi
    # usada, não o `_norm` local — que não remove sufixo de roteamento e faria as
    # pernas C6 com sufixo variante deixarem de agrupar (sub-reporte silencioso).
    buckets = _buckets(
        despesas=[
            _tx(valor=100.0, descricao="compra mercado", tipo_conta="extrato"),
            _tx(valor=100.0, descricao="compra mercado - BOLETO", tipo_conta="extratoconta"),
        ]
    )
    assert len(cross_group_double_count(buckets)) == 1


def test_detector_nao_muta_o_payload() -> None:
    # GUARD: "zero mudança de comportamento" — o harness reusa os MESMOS dicts nos
    # vereditos de balde; injetar campo no item (antipadrão de `_flatten_e4_payload`)
    # contaminaria o resto do relatório.
    buckets = _par_divergente(valor=100.0)
    snap = copy.deepcopy(buckets)
    cross_group_double_count(buckets)
    cross_group_unkeyable(buckets)
    cross_group_coverage(buckets, particionadas=1)
    assert snap == buckets


def test_baldes_ausentes_ou_ilegiveis_nao_estouram() -> None:
    # GUARD: `patrimonio` é omitido quando o baseline está vazio (ADR-132) e o
    # `dados` de `investimentos` é LISTA — o detector varre só os baldes
    # transacionais e degrada para [] em vez de estourar a certificação. A
    # degradação é NOMEADA por `cross_group_coverage` (ver o teste de cobertura).
    assert cross_group_double_count({}) == []
    assert cross_group_double_count({"despesas": {"dados": []}}) == []
    assert cross_group_double_count({"despesas": None}) == []


# ───────── exclusões declaradas da chave (anti-silêncio ADR-342) ─────────


def _skipped(reason: str, n: int) -> dict:
    return {**{k: 0 for k in ("sem_data", "valor_zero", "valor_nao_monetario")}, reason: n}


def test_valor_nao_monetario_e_contado_e_nao_flagado() -> None:
    # GUARD anti-silêncio: a exclusão da chave é CONTADA por razão, nunca muda.
    # Proveniência divergente de propósito — só a não-chaveabilidade barra.
    buckets = _par_divergente(valor="N/D")
    assert cross_group_double_count(buckets) == []
    assert cross_group_unkeyable(buckets) == _skipped("valor_nao_monetario", 2)


def test_valor_zero_e_contado_e_nao_flagado() -> None:
    # Excesso zero ⇒ materialidade zero: fora da chave, dentro da contagem.
    buckets = _par_divergente(valor=0.0)
    assert cross_group_double_count(buckets) == []
    assert cross_group_unkeyable(buckets) == _skipped("valor_zero", 2)


def test_row_sem_data_e_contada_e_nao_flagada() -> None:
    # Sem data não se afirma co-evento (mesmo fail-safe de `_cross_period`).
    buckets = _par_divergente(data="")
    assert cross_group_double_count(buckets) == []
    assert cross_group_unkeyable(buckets) == _skipped("sem_data", 2)


def test_so_valor_exatamente_zero_e_excluido_por_valor() -> None:
    # RATCHET BILATERAL do PREDICADO, não da identidade: um piso OU um cap dentro de
    # `_unkeyable_reason` derruba o numerador em silêncio E a identidade
    # `rows_scanned − rows_keyed == Σ unkeyable` CONTINUA fechando, porque é
    # auto-consistente (toda row excluída é contada como excluída). A versão anterior
    # fixava 4 valores, todos PISO — `cents > 499_999` passava com a suíte verde.
    # Aqui o predicado é fixado nos DOIS lados: exclusão por valor ⟺ cents == 0.
    for valor in (0.01, 1.0, 49.99, 4999.99, 100_000.0, 98_765_432.10):
        assert _unkeyable_reason(_tx(valor=valor)) is None, valor
        buckets = _par_divergente(valor=valor)
        assert cross_group_unkeyable(buckets)["valor_zero"] == 0, valor
        assert len(cross_group_double_count(buckets)) == 1, valor
    for zero in (0.0, -0.0, "0.00"):
        assert _unkeyable_reason(_tx(valor=zero)) == "valor_zero", zero


def test_descricao_vazia_segue_chaveavel_e_sai_rotulada() -> None:
    # Decisão A40.l1: manter CHAVEÁVEL (excluir compraria certeza de SUB-detecção —
    # esconderia dup real de row sem descrição) + rotular. Sob ADR-342, over-detecção
    # rotulada > sub-detecção silenciosa. A classe NÃO é exclusão: fica fora de
    # `cross_group_unkeyable` para não quebrar a invariante de cobertura.
    buckets = _buckets(
        despesas=[
            _tx(descricao="", tipo_conta="extrato"),
            _tx(descricao=None, tipo_conta="extratoconta"),
        ]
    )
    hits = cross_group_double_count(buckets)
    assert len(hits) == 1 and hits[0].descricao_vazia is True
    assert cross_group_unkeyable(buckets) == _skipped("valor_zero", 0)
    assert cross_group_coverage(buckets, particionadas=1)["keyed_sem_descricao"] == 2


# ───────── baldes varridos: alavanca silenciosa de massa ─────────


def test_baldes_transacionais_varridos_congelados() -> None:
    # RATCHET: encolher `_TX_BUCKET_DIRECTION` tira metade da massa da varredura sem
    # tocar em nenhuma identidade de cobertura (elas se fecham sobre o que sobrou).
    assert _TX_BUCKET_DIRECTION == {"despesas": "debit", "receitas": "credit"}


def test_colisao_no_balde_receitas_tambem_e_detectada() -> None:
    # RATCHET com dente para o mesmo lever: se `receitas` sair do mapping, este par
    # deixa de ser visto e o numerador cai sem que nada mais quebre.
    buckets = _buckets(
        receitas=[
            _tx(valor=100.0, descricao="rendimento", tipo_conta="extrato"),
            _tx(valor=100.0, descricao="rendimento", tipo_conta="extratopoupanca"),
        ]
    )
    hits = cross_group_double_count(buckets)
    assert len(hits) == 1 and hits[0].direction == "credit"


# ───────── partição defeito × coincidência (fill-state por campo) ─────────


def test_fill_state_particiona_os_tres_estados() -> None:
    # A partição correta é por fill-state POR CAMPO. "vazio em ≥1 perna" mistura
    # `parcial` (assimétrico — assinatura do carrier) com `vazio` total (simétrico —
    # nada a canonicalizar) e rotula falso-positivo como defeito.
    provenances = {("itau", "", "extratoconta"), ("c6bank", "titular", "extratoconta")}
    assert _fill_states(provenances) == {
        "banco": "preenchido",
        "titular": "parcial",
        "tipo_conta": "preenchido",
    }
    ambos_vazios = {("itau", "", "extratoconta"), ("c6bank", "", "extratoconta")}
    assert _fill_states(ambos_vazios)["titular"] == "vazio"


def test_carrier_da_adr354_sai_rotulado_defect_shaped() -> None:
    hits = cross_group_double_count(_carrier_adr354())
    assert len(hits) == 1
    assert hits[0].divergence == "titular+tipo_conta"
    assert hits[0].parciais == "titular"
    assert hits[0].vazios_totais == ""
    assert hits[0].defect_shaped is True
    assert hits[0].descricao_vazia is False


def test_parcial_implica_divergente_no_mesmo_eixo() -> None:
    # A invariante que faz `defect_shaped` significar "assimetria NO eixo
    # divergente" sem precisar de um segundo predicado: um campo vazio numa perna e
    # preenchido noutra TEM 2 valores distintos, logo está sempre no `divergence`.
    hits = cross_group_double_count(_carrier_adr354())
    assert set(hits[0].parciais.split("+")) <= set(hits[0].divergence.split("+"))


def test_vazio_nas_duas_pernas_nao_e_defeito() -> None:
    # Classe de falso-positivo MEDIDA na r1: dois saques REAIS em bancos distintos,
    # `titular` vazio nos DOIS lados. Sob a partição antiga (vazio em ≥1 perna) saía
    # `defect_shaped=True` — o eixo vazio não era o eixo divergente. `titular` é
    # simétrico aqui: não há nada a canonicalizar, é coincidência.
    buckets = _buckets(
        despesas=[
            _tx(descricao="saque", banco="banco a", titular=""),
            _tx(descricao="saque", banco="banco b", titular=""),
        ]
    )
    hits = cross_group_double_count(buckets)
    assert len(hits) == 1
    assert hits[0].divergence == "banco"
    assert hits[0].parciais == ""
    assert hits[0].vazios_totais == "titular"
    assert hits[0].defect_shaped is False


def test_coincidencia_cross_conta_entra_no_numerador_rotulada() -> None:
    # SOBRE-detecção DECLARADA: duas contas genuinamente distintas, AMBAS as pernas
    # preenchidas, mesma assinatura no mesmo dia e valor. ENTRA no numerador —
    # filtrar por assinatura derivada do corpus cegaria o detector para o PRÓXIMO
    # carrier — e sai rotulada coincidence-shaped.
    hits = cross_group_double_count(_coincidencia_cross_conta())
    assert len(cross_group_numerator(hits)) == 1
    assert hits[0].parciais == "" and hits[0].vazios_totais == ""
    assert hits[0].defect_shaped is False
    assert hits[0].divergence == "banco+titular"


def test_excess_conta_proveniencias_e_nao_rows() -> None:
    # 3 rows em 2 proveniências ⇒ 1 duplicata cross-grupo, não 2. A row extra DENTRO
    # da mesma proveniência é o caso (c) (repetição legítima) ou miss do dedup K4:
    # achado distinto, fora do Σ headline e da chave de ordenação.
    buckets = _buckets(
        despesas=[
            _tx(tipo_conta="extrato"),
            _tx(tipo_conta="extrato"),
            _tx(tipo_conta="extratoconta"),
        ]
    )
    hits = cross_group_double_count(buckets)
    assert len(hits) == 1
    assert (hits[0].n_rows, hits[0].n_provenances) == (3, 2)
    assert hits[0].excess_cents == 10000


def test_excess_escala_com_o_numero_de_proveniencias() -> None:
    # TRIPWIRE: `excess_cents` só era pinado com `n_provenances == 2`, onde (P−1) == 1 e
    # `valor_cents` sozinho dá o MESMO número — o fator nunca era exercitado. 3 pernas do
    # mesmo evento ⇒ 2 duplicatas cross-grupo, não 1 nem 3.
    buckets = _buckets(
        despesas=[
            _tx(tipo_conta="extrato"),
            _tx(tipo_conta="extratoconta"),
            _tx(tipo_conta="extratopoupanca"),
        ]
    )
    hits = cross_group_double_count(buckets)
    assert len(hits) == 1
    assert (hits[0].n_rows, hits[0].n_provenances) == (3, 3)
    assert hits[0].valor_cents == 10000
    assert hits[0].excess_cents == 2 * hits[0].valor_cents == 20000
