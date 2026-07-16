"""Red lines do parecer (ADR-300): 4ª camada determinística que barra conselho
financeiro irresponsável. Opera sobre o dict do output + o E5 (zero LLM); ≥1
hard-block → ``needs_review`` global. Predicados reconciliados contra campos reais
do E5 (financial-planner 2026-06-26). Lemmas e tabela tema→fonte versionados sob
``RED_LINES_VERSION`` — bump invalida cache (ver compute_cache_key).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

RED_LINES_VERSION = "1.4"

# Lemmas (radicais, sem acento, lowercase) — lista controlada, não NLP.
# RL1 (ADR-300, calibração financial-planner 2026-06-30): "reserva antes de risco"
# proíbe DEPLOY de capital, não planejamento de arcabouço (definir política/alocação-
# alvo é o núcleo do método AUVP). Execução inequívoca sempre dispara; verbo ambíguo
# só dispara em P0/P1; planejamento puro de arcabouço não dispara.
# RL1 1.2 (dogfood 2026-06-30): "aport" cru casava "rebalanceamento por APORTE"
# (substantivo de método AUVP/Perini). Só verbo CONJUGADO de deploy de capital novo.
_EXEC_INEQUIVOCA = (
    "aportar",
    "aporte de",
    "aporte em",
    "aporte inicial",
    "aporte r$",
    "comprar",
    "adquirir cota",
    "montar posic",
    "aumentar exposic",
    "elevar exposic",
    "destinar a",
)
_APORTE_AMBIGUO = ("investir em", "alocar em")
# Rebalanceamento / de-risking / aporte-como-método: conselho prudente, NÃO deploy de
# novo risco (AUVP rebalanceia por aporte; reduzir/revisar peso é de-risking). Curto-
# circuita RL1 antes de avaliar execução (financial-planner + senior-cto, dogfood).
_DERISK_REBALANCE = (
    "rebalanc",
    "por aporte",
    "aportes mensais",
    "via aporte",
    "revisar o peso",
    "revisar a alocac",
    "revisar a carteira",
    "reduzir",
    "diminuir",
    "realocar",
    "redistribuir",
    "ajustar a carteira",
)
_PLANEJAMENTO_ARCABOUCO = (
    "definir politica",
    "politica de investiment",
    "alocacao-alvo",
    "alocacao alvo",
    "desvio maximo",
    "arcabouco",
    "diretriz",
    "estrategia de alocac",
    "plano de",
    "estabelecer meta",
    "revisar a carteira",
    "mapear",
)
_OBJETO_RISCO = ("acoes", "acao", "fii", "fiis", "renda variavel", "bolsa", "cripto", "rv")
_PRO_RESERVA = ("reserva", "caixa", "tesouro selic", "rf pos", "pos-fixad", "liquidez")
_QUITACAO = (
    "quitar",
    "amortizar",
    "liquidar divida",
    "antecipar parcela",
    "abater saldo",
    "renegociar",
)
_SAQUE_RESERVA = (
    "sacar",
    "resgatar",
    "usar a reserva",
    "reduzir reserva",
    "diminuir reserva",
    "mover reserva",
    "realocar reserva",
    "migrar reserva",
)
_CORTE_VERBO = ("cancelar", "cortar", "dispensar", "suspender", "encerrar")
_PROTECAO_OBJ = ("seguro", "cobertura", "protec")
_MOTIVO_RENDIMENTO = ("rentabili", "retorno", "render mais", "melhor rendimento", "yield")
_EXCEDENTE = ("excedente", "sobra", "acima de", "parte que excede", "superdimension")
_RECOMENDA = (
    "comprar",
    "adquirir",
    "contratar",
    "aportar em",
    "alocar em",
    "migrar para",
    "abrir conta em",
    "abrir posic",
    "escolher",
)

# RL3 (ADR-300): promessa de retorno = garantia PRÓXIMA de objeto-de-retorno (spec
# financial-planner). Genérico "garant\w+" isolado é falso-positivo em massa
# ("garante capacidade de aporte", FGC "fundo garantidor", "garantir a reserva").
_PROMESSA_FORTE = re.compile(  # promessa inequívoca — dispara mesmo com hedge
    r"(rentabilidade garantida|retorno garantido|ganho garantido|lucro garantido"
    r"|rentabilidade certa|sem risco de perda)"
)
_RENDER_PROMESSA = re.compile(r"(vai render|rendera|rende \d)")  # render+futuro/figura
# \b evita substring-FP (dogfood 1.3): "comPROMETam/comPROMETE" (comprometer ≠ prometer),
# "inCERTEZA" (≠ certeza). Exige objeto-de-retorno por perto (ver _promete_retorno).
_GARANTIA_GEN = re.compile(r"\b(garant\w+|assegur\w+|promet\w+|certeza)")
_RETORNO_OBJ = re.compile(
    r"(retorno|rentabili|lucro|ganho|valoriz|render|dividend|% ?a\.?\s?a|ao ano)"
)
_PROX = 45
_HEDGE = re.compile(r"(pode render|historicamente|busca rentabili|tende a|pode valoriz)")
_TICKER = re.compile(r"\b[A-Z]{4}\d{1,2}\b")

# RL-7: só o sinal ESTRUTURADO de real_estate vira hard-block — tema inequívoco.
# pontos_urgentes/alertas top-level são texto livre (sem tema mapeável
# deterministicamente) → fora do hard-block (follow-up: tag de tema por item).
_TEMA_CONCENTRACAO = {"Alocação", "Saúde de balanço"}
_SEVERIDADE_ALTA = {"Crítica", "Alta"}
# RL7 graduado (1.4, financial-planner 2026-06-30): em 40–60% Cerbasi (estabilidade)
# e AUVP (diversificar) legitimamente divergem → Média basta (abordar ≠ silenciar);
# >60% mesmo Cerbasi não sustenta → exige Alta; alerta estruturado do E5 → exige Alta.
_SEVERIDADE_MEDIA_MAIS = {"Crítica", "Alta", "Média"}


@dataclass(frozen=True)
class RedLineViolation:
    rl_id: str
    severity: str  # "block" | "warning"
    detail: str


@dataclass(frozen=True)
class RedLinesResult:
    violations: tuple[RedLineViolation, ...] = ()
    version: str = RED_LINES_VERSION

    @property
    def blocked(self) -> bool:
        return any(v.severity == "block" for v in self.violations)

    def block_reason(self) -> str | None:
        ids = [v.rl_id for v in self.violations if v.severity == "block"]
        return f"red lines (v{self.version}): {ids}" if ids else None

    def summary(self, *, needs_review_triggered: bool) -> dict:
        return {
            "version": self.version,
            "triggered": [v.rl_id for v in self.violations],
            "blocked": [v.rl_id for v in self.violations if v.severity == "block"],
            "warnings": [v.rl_id for v in self.violations if v.severity == "warning"],
            "needs_review_triggered": needs_review_triggered,
        }


def _norm(text: Any) -> str:
    s = str(text or "")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _has_any(text: str, lemmas: Sequence[str]) -> bool:
    return any(lemma in text for lemma in lemmas)


def _all_sugestoes(out: Mapping[str, Any]) -> list[dict]:
    keys = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")
    return [s for k in keys for s in (out.get(k) or []) if isinstance(s, dict)]


def _is_aporte_risco(sug: Mapping[str, Any]) -> bool:
    acao = _norm(sug.get("acao"))
    if sug.get("tema_canonico") not in {"Alocação", "Renda passiva"}:
        return False
    if _has_any(acao, _PRO_RESERVA):
        return False
    if _has_any(acao, _DERISK_REBALANCE):
        return False  # rebalance/de-risking/aporte-método — conselho prudente, não deploy
    exec_imediata = _has_any(acao, _EXEC_INEQUIVOCA)
    if _has_any(acao, _PLANEJAMENTO_ARCABOUCO) and not exec_imediata:
        return False  # planejamento de arcabouço (AUVP/Cerbasi) — não é deploy de risco
    if not _has_any(acao, _OBJETO_RISCO):
        return False
    if exec_imediata:
        return True
    return _has_any(acao, _APORTE_AMBIGUO) and sug.get("prioridade") in {"P0", "P1"}


def _has_quitacao(out: Mapping[str, Any]) -> bool:
    return any(_has_any(_norm(s.get("acao")), _QUITACAO) for s in _all_sugestoes(out))


def _prose_blobs(out: Mapping[str, Any]) -> list[str]:
    blobs = [out.get("diagnostico_geral")]
    for s in _all_sugestoes(out):
        blobs += [s.get("acao"), s.get("impacto_qualitativo")]
    for r in out.get("riscos") or []:
        if isinstance(r, dict):
            blobs.append(r.get("descricao"))
    for p in out.get("pontos_fortes") or []:
        if isinstance(p, dict):
            blobs.append(p.get("descricao"))
    return [b for b in blobs if b]


def _avaliacao_insuficiente(res: Mapping[str, Any]) -> bool:
    # E5 emite "insuficiente" (minúsculo); case-insensitive p/ não morrer o branch.
    return (res.get("avaliacao_liquidity") or "").strip().lower() == "insuficiente"


def _reserva_sub_meta(e5: Mapping[str, Any]) -> bool:
    res = e5.get("reserva_emergencia") or {}
    if _avaliacao_insuficiente(res):
        return True
    cob = res.get("cobertura_meses")
    return isinstance(cob, (int, float)) and cob == cob and cob < 6.0  # NaN-safe


def _rl1_reserva_antes_risco(out, e5) -> list[RedLineViolation]:
    if not _reserva_sub_meta(e5) or not any(_is_aporte_risco(s) for s in _all_sugestoes(out)):
        return []
    return [RedLineViolation("RL1", "block", "aporte em risco com reserva abaixo da meta")]


def _rl2_divida_cara_precede_risco(out, e5) -> list[RedLineViolation]:
    if not any(_is_aporte_risco(s) for s in _all_sugestoes(out)) or _has_quitacao(out):
        return []
    if _divida_cara_conhecida(e5):
        return [RedLineViolation("RL2", "block", "aporte em risco com dívida cara conhecida")]
    ratios = e5.get("ratios") or {}
    taxa = ratios.get("taxa_endividamento_pct")
    if isinstance(taxa, (int, float)) and taxa >= 40.0:
        return [
            RedLineViolation("RL2", "warning", "aporte em risco com endividamento alto (proxy)")
        ]
    return []


def _divida_cara_conhecida(e5: Mapping[str, Any]) -> bool:
    for div in (e5.get("endividamento") or {}).get("dividas") or []:
        taxa_mensal = _parse_taxa_mensal(div.get("taxa_juros") if isinstance(div, dict) else None)
        if taxa_mensal is not None and taxa_mensal > 1.5:
            return True
    return False


def _parse_taxa_mensal(raw: Any) -> float | None:
    m = re.search(r"(\d+[.,]?\d*)\s*%", str(raw or ""))
    return float(m.group(1).replace(",", ".")) if m else None


def _promete_retorno(n: str) -> bool:
    if _PROMESSA_FORTE.search(n):
        return True
    if _HEDGE.search(n):
        return False
    if _RENDER_PROMESSA.search(n):
        return True
    for m in _GARANTIA_GEN.finditer(n):  # garantia genérica só com obj-retorno por perto
        if _RETORNO_OBJ.search(n[max(0, m.start() - _PROX) : m.end() + _PROX]):
            return True
    return False


def _rl3_promessa_retorno(out, e5) -> list[RedLineViolation]:
    for blob in _prose_blobs(out):
        if _promete_retorno(_norm(blob)):
            return [RedLineViolation("RL3", "block", "promessa/garantia de retorno (CVM)")]
    return []


def _rl4_ativo_especifico(out, e5, institutions: Sequence[str]) -> list[RedLineViolation]:
    inst_norm = [i for i in (_norm(x) for x in institutions) if i]
    for sug in _all_sugestoes(out):
        acao_raw, acao = sug.get("acao") or "", _norm(sug.get("acao"))
        if _TICKER.search(str(acao_raw)):
            return [RedLineViolation("RL4", "block", "ticker específico recomendado")]
        if _has_any(acao, _RECOMENDA) and _has_any(acao, inst_norm):
            return [RedLineViolation("RL4", "block", "instituição/produto nominado recomendado")]
    return []


def _rl5_p0_sem_fonte(out, e5) -> list[RedLineViolation]:
    for sug in _all_sugestoes(out):
        if sug.get("prioridade") == "P0" and not (sug.get("ancoras") or []):
            return [RedLineViolation("RL5", "warning", "sugestão P0 sem âncora de evidência")]
    return []


def _corta_protecao(n: str) -> bool:
    if _has_any(n, _CORTE_VERBO) and _has_any(n, _PROTECAO_OBJ):
        return True
    return "reduzir cobertura" in n or "reduzir protec" in n


def _saca_reserva(n: str, insuficiente: bool) -> bool:
    if not _has_any(n, _SAQUE_RESERVA) or _has_any(n, _EXCEDENTE):
        return False
    return insuficiente or _has_any(n, _MOTIVO_RENDIMENTO)


def _rl6_blob_violation(n: str, insuficiente: bool) -> RedLineViolation | None:
    if _corta_protecao(n):
        return RedLineViolation("RL6", "block", "corte de seguro/proteção essencial")
    if _saca_reserva(n, insuficiente):
        return RedLineViolation("RL6", "block", "saque/realocação da reserva por rendimento")
    return None


def _rl6_mexer_reserva_protecao(out, e5) -> list[RedLineViolation]:
    insuficiente = _avaliacao_insuficiente(e5.get("reserva_emergencia") or {})
    for blob in _prose_blobs(out):
        violation = _rl6_blob_violation(_norm(blob), insuficiente)
        if violation:
            return [violation]
    return []


def _severidade_exigida_concentracao(e5: Mapping[str, Any]) -> set[str] | None:
    """Severidade que o parecer precisa ter no tema concentração, graduada (RL7 1.4); ``None`` = sem concentração relevante. C11-Fase2 ([[ADR-340]]): fonte = ``ratios.concentracao_imobiliaria`` (SSOT base carteira, sempre presente); thresholds ALTA 60→75, MEDIA_MAIS 40→50; o acoplamento largo a ``real_estate.alertas`` foi removido (senão `concentracao_alta` a 50% furaria a linha de hard-block ratificada em 75%)."""
    ratios = e5.get("ratios") or {}
    conc = ratios.get("concentracao_imobiliaria")
    conc = conc if isinstance(conc, (int, float)) else 0.0
    if conc > 75.0:
        return _SEVERIDADE_ALTA
    if conc > 50.0:
        return _SEVERIDADE_MEDIA_MAIS
    return None


def _rl7_severidade_incoerente(out, e5) -> list[RedLineViolation]:
    exige = _severidade_exigida_concentracao(e5)
    if exige is None:
        return []
    cobertos = {
        r.get("tema_canonico")
        for r in (out.get("riscos") or [])
        if isinstance(r, dict) and r.get("severidade") in exige
    }
    if not (_TEMA_CONCENTRACAO & cobertos):
        return [
            RedLineViolation(
                "RL7", "block", "subdiagnóstico: concentração sem risco no nível exigido"
            )
        ]
    return []


@dataclass(frozen=True)
class RedLine:
    id: str
    check: Callable[..., list[RedLineViolation]]
    needs_institutions: bool = field(default=False)


RED_LINES: tuple[RedLine, ...] = (
    RedLine("RL1", _rl1_reserva_antes_risco),
    RedLine("RL2", _rl2_divida_cara_precede_risco),
    RedLine("RL3", _rl3_promessa_retorno),
    RedLine("RL4", _rl4_ativo_especifico, needs_institutions=True),
    RedLine("RL5", _rl5_p0_sem_fonte),
    RedLine("RL6", _rl6_mexer_reserva_protecao),
    RedLine("RL7", _rl7_severidade_incoerente),
)


def check_red_lines(
    output: Mapping[str, Any],
    e5_data: Mapping[str, Any],
    *,
    institutions: Sequence[str] = (),
) -> RedLinesResult:
    """Avalia as 7 red lines sobre o dict do output do parecer + o E5 (ADR-300)."""
    violations: list[RedLineViolation] = []
    for rl in RED_LINES:
        if rl.needs_institutions:
            violations.extend(rl.check(output, e5_data, institutions))
        else:
            violations.extend(rl.check(output, e5_data))
    return RedLinesResult(violations=tuple(violations))


__all__ = [
    "RED_LINES",
    "RED_LINES_VERSION",
    "RedLineViolation",
    "RedLinesResult",
    "check_red_lines",
]
