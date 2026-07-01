"""Identidade determinística de transações K4 versionada (ADR-255 + ADR-278 B3):
``_hash_v1`` é o contrato congelado com o DB histórico (abs sem moeda/direction,
float); ``_hash_v2`` é o novo (moeda+direction, cents int via Decimal, sem drift);
``compute_natural_key`` é a API de contrato. O dispatch flag-aware v2/v1 vive em
``compute_identity_hash`` (fallback v1 sob flag-OFF)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_WHITESPACE_RE = re.compile(r"\s+")

# ADR-255 iteração 2-3 — sufixos de roteamento que o mesmo banco emite de
# forma inconsistente entre PDFs (extratos cumulativos do C6 omitem ou incluem
# o tag conforme a versão). Strip antes do hash para que extratos sobrepostos
# colapsem corretamente. Whitelist conservadora — só remove o segmento FINAL
# após ` — ` (em-dash com espaços) ou ` - ` (hífen com espaços), preservando
# descrições legítimas com em-dash no meio (ex.: "Aluguel apto 12").
#
# Iteração 3 (2026-05-24, ADR-255 it.3): observação em prod do report
# b042c210 mostrou 3 novos padrões não-cobertos pela it.2:
# (a) CPF/CNPJ + nome remetente em TED inbound (` — 27788253634-JAIR DE SOUZA`)
# (b) Placa Mercosul/legacy + local em C6TAG (` — GDK6A27-AEROPORTO DE...`)
# (c) Descritor cliente livre tipo `— Salários PJ` extendido (` — mentoria 4Valor unitário...`)
# (a) e (b) têm pattern estável; (c) ficou fora (texto livre cliente é frágil).
_ROUTING_SUFFIX_RE = re.compile(
    r"""
    \s*[—-]\s*           # separador ` — ` ou ` - ` (com whitespace ao redor)
    (?:
        TRANSF\ ENVIADA\ PIX            # C6 — débito PIX outbound
        | SAL[ÁA]RIOS?\ PJ              # C6 — receita PJ recorrente
        | 13\ SAL[ÁA]RIO                # C6 — décimo terceiro
        | BOLETO                        # C6 — pagamento boleto
        | NFS?\s+\d+                    # C6 — NF/NFS numerada (NFS 25, NF 26)
        # ADR-255 it.3: CPF (11 dígitos) ou CNPJ (14) + traço + nome PF/PJ.
        # Pattern restrito: começa com dígitos, traço, depois nome em maiúsculas.
        | \d{11,14}-[A-Z][A-Z\s]*[A-Z]
        # ADR-255 it.3: placa brasileira (Mercosul ABC1D23 ou legacy ABC1234)
        # + traço + local em maiúsculas (C6TAG ESTACIONAMENTO).
        | [A-Z]{3}\d[A-Z\d]\d{2}-[A-Z][A-Z\s]*[A-Z]
    )
    \s*$                  # opcional trailing whitespace + fim de string
    """,
    re.IGNORECASE | re.VERBOSE,
)

# DARF detalhada — C6 às vezes anexa "SIMPLES NACIONAL" no fim sem separador.
# Trato à parte porque não casa o padrão ` — sufixo` (sem em-dash).
_DARF_DETAIL_RE = re.compile(r"\s+SIMPLES\s+NACIONAL\s*$", re.IGNORECASE)


def _strip_accents(text: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )


def _strip_routing_suffixes(text: str) -> str:
    """Remove sufixos de roteamento bancário do final da descrição (ADR-255 it.2)."""
    # Aplicado antes do lowercase+whitespace-collapse: preserva conteúdo de
    # negócio (remetente/destinatário, parcela N/M, nome próprio).
    text = _ROUTING_SUFFIX_RE.sub("", text)
    text = _DARF_DETAIL_RE.sub("", text)
    return text


def normalize_banco(value: str | None) -> str:
    """Robust contra drift de casing/espacing (`"C6Bank"` vs `"C6 Bank"`)."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_titular(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_tipo_conta(value: str | None) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub("", _strip_accents(value).lower())


def normalize_descricao(value: str | None) -> str:
    """Lowercase + strip + collapse whitespace + strip sufixos PIX (ADR-255 it.2)."""
    if not value:
        return ""
    # ADR-255 it.2: strip sufixos de roteamento ANTES do lowercase para que
    # extratos sobrepostos do C6 (mesma tx com/sem " — Salários PJ" / etc.)
    # produzam o mesmo hash. Lista finita em _ROUTING_SUFFIX_RE.
    stripped = _strip_routing_suffixes(value.strip())
    return _WHITESPACE_RE.sub(" ", stripped.lower())


def cents_int(valor: float | int) -> int:
    """Converte ``valor`` para int em centavos (evita float drift, ADR-090 §wire)."""
    return int(round(float(valor) * 100))


def decimal_cents(valor: float | int | str | Decimal) -> int:
    """Magnitude em centavos via ``Decimal(str(v))`` (ADR-090; rounding inline, ADR-111)."""
    # str() (não Decimal(float)) torna a borda determinística: 0.575→58 ROUND_HALF_UP,
    # corrige o int(round(0.575*100))==57 do cents_int legado.
    dec = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    return int(abs(dec).scaleb(2).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def to_amount_string(valor: float | int | str | Decimal | None) -> str | None:
    """Espelho decimal-string de ``valor`` (ADR-278 B5; wire decimal, ADR-090): ponto-fixo via ``format(dec,"f")`` (mata notação científica), sem quantizar (preserva FX 3+ casas), sinal preservado; ``None`` se ausente/não-numérico (stamp omite a chave)."""
    if valor is None:
        return None
    try:
        dec = valor if isinstance(valor, Decimal) else Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
    return format(dec, "f")


def _infer_tipo(valor: float | int, tipo_conta: str) -> str | None:
    # Espelho EXATO da inferência por sinal de _normalize_tipo (E4): fatura com
    # valor<0 é crédito (estorno); fatura positivo sem tipo → None. Drift travado
    # por test_derive_direction_matches_normalize_tipo.
    is_fatura = (tipo_conta or "").lower().startswith("fatura")
    if not is_fatura:
        return "credito" if valor > 0 else "debito"
    if valor < 0:
        return "credito"
    return None


def derive_direction(*, tipo: str | None, valor: float | int, tipo_conta: str | None) -> str:
    """``credit``/``debit`` — ``tipo`` vence (ADR-278 D2); ausente infere por sinal."""
    # NÃO derivar do sinal cru: fatura inverte (estorno) e quebraria o dedup.
    norm = _strip_accents(tipo).strip().lower() if tipo else _infer_tipo(valor, tipo_conta or "")
    return "credit" if norm == "credito" else "debit"


@dataclass(frozen=True)
class HashInputs:
    """Inputs normalizados do hash K4 v2 (ADR-278 D3); ``valor_cents`` é magnitude."""

    data: str
    banco: str
    titular: str
    tipo_conta: str
    valor_cents: int
    moeda: str
    direction: str
    descricao: str


@dataclass(frozen=True)
class NaturalKey:
    """Chave natural versionada — campo de contrato E2 (ADR-278 §38)."""

    hash: str
    hash_version: int

    def to_dict(self) -> dict:
        return {"hash": self.hash, "hash_version": self.hash_version}


def _has_discriminants(banco: str | None, titular: str | None, tipo_conta: str | None) -> bool:
    """Gate classe-c do K4 (ADR-278): sem os três, ``natural_key=None`` (nunca hash degenerado)."""
    return bool((banco or "").strip() and (titular or "").strip() and (tipo_conta or "").strip())


# Construtor canônico de HashInputs — ponto único de mapeamento emit↔recompute (ADR-278 D3).
def build_hash_inputs(
    data: str | None,
    banco: str | None,
    titular: str | None,
    tipo_conta: str | None,
    valor: float | int | str | Decimal,
    moeda: str | None,
    descricao: str | None,
    tipo: str | None = None,
) -> HashInputs:
    return HashInputs(
        data=data or "",
        banco=banco or "",
        titular=titular or "",
        tipo_conta=tipo_conta or "",
        valor_cents=decimal_cents(valor),
        moeda=(moeda or "").strip().upper(),
        direction=derive_direction(tipo=tipo, valor=_coerce_signed(valor), tipo_conta=tipo_conta),
        descricao=descricao or "",
    )


def _coerce_signed(valor: float | int | str | Decimal) -> float:
    """Sinal preservado para inferência de direction (não para o cents)."""
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return float(Decimal(str(valor)))
    except Exception:
        return 0.0


def _hash_v1(
    *,
    data: str | None,
    banco: str | None,
    titular: str | None,
    tipo_conta: str | None,
    valor: float | int,
    descricao: str | None,
) -> str:
    # CONGELADO (ADR-278 D1): abs(valor) sem moeda/direction, ingere float (bug de
    # arredondamento de propósito) — mudar invalida hashes gravados em pipeline_artifacts.
    parts = (
        data or "",
        normalize_banco(banco),
        normalize_titular(titular),
        normalize_tipo_conta(tipo_conta),
        str(cents_int(abs(valor))),
        normalize_descricao(descricao),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def _hash_v2(inputs: HashInputs) -> str:
    """Hash K4 v2 — moeda + direction discriminam; cents int (ADR-278 B3)."""
    parts = (
        inputs.data,
        normalize_banco(inputs.banco),
        normalize_titular(inputs.titular),
        normalize_tipo_conta(inputs.tipo_conta),
        str(inputs.valor_cents),
        inputs.moeda,
        inputs.direction,
        normalize_descricao(inputs.descricao),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def compute_natural_key(inputs: HashInputs) -> NaturalKey:
    """API de contrato — sempre v2 (moeda+direction). Puro/stateless (ADR-111)."""
    return NaturalKey(hash=_hash_v2(inputs), hash_version=2)


def compute_identity_hash(inputs: HashInputs, *, valor: float | int, natural_key_v2: bool) -> str:
    """Dispatch do recompute E3→E4 (ADR-287): v2 sob flag; v1 ingere ``valor`` float cru."""
    if natural_key_v2:
        return _hash_v2(inputs)
    return _hash_v1(
        data=inputs.data,
        banco=inputs.banco,
        titular=inputs.titular,
        tipo_conta=inputs.tipo_conta,
        valor=valor,
        descricao=inputs.descricao,
    )


def build_item_identity(
    inputs: HashInputs, *, valor: float | int, natural_key_v2: bool
) -> tuple[str, dict | None]:
    """Identidade do item E4: ``transaction_hash`` (dedup, ADR-287) + ``natural_key``
    estruturado (K4 do lineage, ADR-279) só sob v2 + discriminantes (gate classe-c
    ADR-278, nunca hash degenerado). ``natural_key.hash == transaction_hash`` quando v2."""
    tx_hash = compute_identity_hash(inputs, valor=valor, natural_key_v2=natural_key_v2)
    natural_key = (
        compute_natural_key(inputs).to_dict()
        if natural_key_v2 and _has_discriminants(inputs.banco, inputs.titular, inputs.tipo_conta)
        else None
    )
    return tx_hash, natural_key
