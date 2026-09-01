"""Gate de PII no view-model do relatório ([[ADR-337]] c4 · A40.l6 · [[ADR-425]] A40.l115).

Varre **toda string** do payload que o React/PDF consomem — não uma allowlist de
chave. O allowlist era o ponto cego: o fix do #1569 tirou a PII de ``descricao`` e
a pôs em ``endereco_canonical``, que o gate não varria (§Ataque A1). Predicado que
chaveia no VALOR segue o dado quando o render muda de campo; predicado que chaveia
no NOME do campo não. Custo medido: 631 strings nas 6 fixtures de relatório do
repo, 2 hits, zero falso-positivo.

Tipos cobertos: IDENTIFICADOR · CPF_PARCIAL · CONTA · MATRICULA · ENDERECO · CEP

Essa linha é **contrato, não prosa**: ``TIPOS_COBERTOS`` é a fonte única e
``test_cobertura_declarada_igual_a_medida`` compara os dois conjuntos por
IGUALDADE nas duas direções. A [[A40.l115]] nasceu do modo de falha inverso — a
docstring de ``parecer_context_sanitizer`` afirmava cobertura que o código não
tinha, e a afirmação valeu como justificativa para NÃO existir gate.

Não imprime o valor casado — só o dot-path e o tipo (disciplina de
``lint_no_real_pii``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.observability.pii_patterns import (
    contains_bare_identifier,
    contains_identifier,
    scrub_bare_identifiers,
    scrub_identifiers,
)

# `[^\d\n]{0,14}` entre o rótulo e o número: cobre "(IPTU): ", " nº ", ". ".
# Sem isso, "INSCRICAO MUNICIPAL (IPTU): 999.999" atravessava (§Ataque A6).
_CONTRATO = re.compile(
    r"(?i)\b(matr[íi]cula|matr\.|contrato|inscri[cç][aã]o(?:\s+municipal)?|iptu)"
    r"[^\d\n]{0,14}([\d][\d./-]{4,})"
)
_CEP = re.compile(r"\b\d{5}-?\d{3}\b")
# Abreviações são a forma comum em descrição de IRPF; só `Av.` estava coberta.
_ENDERECO = re.compile(
    r"(?i)\b(?:rua|avenida|pra[çc]a|alameda|travessa|estrada|rodovia|av\.|r\.|"
    r"trav\.|al\.|p[çc]\.|rod\.|est\.)\s+"
    r"[\wÀ-ü.]+(?:\s+[\wÀ-ü.]+){0,5},?\s+\d{1,5}\b"
)

# [[A40.l115]] — CPF **parcialmente** mascarado. O gate media só a forma crua, e o
# produto emite três máscaras diferentes (`***.***.***-XX` do prompt E1.6,
# `***.***.789-00` da [[ADR-259]] §4, `***.456.789-**` da [[ADR-231]]). Um grupo é
# `\d{3}` OU `\*{3}` — máscara real nunca mistura dentro do grupo. O lookahead
# exige ao menos um `*` no PRÓPRIO token (classe restrita a `[\d*.-]`, senão um
# asterisco vizinho na frase fabricaria o match) — sem ele isto duplicaria `_CPF`.
_G3 = r"(?:\d{3}|\*{3})"
_CPF_PARCIAL = re.compile(
    rf"(?<![\d*]){_G3}\.(?=[\d*.\-]*\*){_G3}\.{_G3}-(?:\d{{2}}|\*{{2}})(?![\d*])"
)

# [[A40.l115]] — agência/conta. Rótulo + dígitos, nunca dígitos soltos: conta não
# tem forma própria (4-12 dígitos casa CEP, protocolo, ano, valor). O rótulo vem
# em DUAS forças porque `conta` é palavra hiperfrequente em pt-BR e o gate ia
# rodar sobre PROSA do parecer, não só sobre rótulo de linha (objeção medida do
# sre-devops): `conta: R$ 1.500` virava `R$ •.500` e `levar em conta 2026` virava
# `•026` — corromper valor monetário é pior que o vazamento que isso evita.
#   forte (`ag`/`c/c`/`cc`) — token bancário inequívoco, basta rótulo + dígitos;
#   fraco (`conta`/`poupança`) — exige FORMA de conta (dígito verificador após
#   hífen). Dinheiro e ano não têm DV, então a forma é o discriminador.
# `$` fora do gap é a segunda barreira contra `R$` ([[ADR-090]]: valor não se toca).
_ROTULO_FORTE = r"(?:ag[êe]ncia|ag|c/?c)"
_ROTULO_FRACO = r"(?:conta(?:\s+corrente)?|poupan[çc]a)"
_GAP = r"[^\d\n•$]{0,6}"
_CONTA = re.compile(
    rf"(?i)\b(?:(?P<forte>{_ROTULO_FORTE}){_GAP}(?P<numf>\d[\d.\-]{{3,}})"
    rf"|(?P<fraco>{_ROTULO_FRACO}){_GAP}(?P<numw>\d[\d.]*\d-\d+))(?![\d.,]*,)"
)

# Cauda preservada na conta: o dono precisa saber QUAL conta é a linha. Medido na
# [[A40.l115]]: remover o número inteiro deixa 4 linhas do `posicao_31_12` com
# rótulo `'CDB'`/`'RDB/CDB'`/`'Conta Corrente'` — o nome da instituição não está
# no rótulo (só existe como `cnpj_emissor`), e a linha perde identidade.
# 4 (não 3) é a convenção que todo app de banco brasileiro usa — o dono reconhece
# o padrão sem aprender nada — e não depende de sorte de transcrição do LLM para
# desambiguar duas aplicações do mesmo emissor, tipo e moeda (financial-planner).
_CONTA_CAUDA = 4

# Agência sai INTEIRA: não desambigua nada para o dono (contas do mesmo banco
# compartilham agência) e é a metade transacional do par que um TED/boleto
# consome. O princípio: publica-se o que desambigua, oculta-se o que credencia.
# FORÇA do rótulo (casa ou não) e NATUREZA (agência ou conta) são eixos
# ortogonais: `cc` é rótulo forte e é CONTA — preserva cauda, não zera.
_AG_CAUDA = 0
_ROTULO_AGENCIA = re.compile(r"(?i)^ag")

_TOKEN_CONTRATO = "[matricula-redigida]"
_TOKEN_CEP = "[cep-redigido]"
_TOKEN_ENDERECO = "[endereco-redigido]"
_TOKEN_CPF_PARCIAL = "[cpf-redigido]"

#: Vocabulário DECLARADO do gate — fonte única da docstring, de
#: ``cartorial_pii_tipos`` e do teste de igualdade de conjunto.
TIPOS_COBERTOS = (
    "IDENTIFICADOR",
    "CPF_PARCIAL",
    "CONTA",
    "MATRICULA",
    "ENDERECO",
    "CEP",
)


@dataclass(frozen=True)
class ViewModelPiiHit:
    path: str
    tipo: str

    def format(self) -> str:
        return f"{self.path}: {self.tipo}"


def _mascara_conta(match: re.Match) -> str:
    """``Ag 1234`` → ``Ag ••••``; ``Conta 1234567-8`` → ``Conta ••••567-8`` — cauda da
    conta preservada, agência zerada (`cc`/`c/c` é conta, não agência)."""
    numero = match.group("numf") or match.group("numw")
    rotulo = match.group("forte") or match.group("fraco")
    cauda = _AG_CAUDA if _ROTULO_AGENCIA.match(rotulo) else _CONTA_CAUDA
    digitos = [i for i, c in enumerate(numero) if c.isdigit()]
    corte = digitos[-cauda] if cauda and len(digitos) > cauda else len(numero)
    mascarado = "".join("•" if c.isdigit() else c for c in numero[:corte]) + numero[corte:]
    return match.group(0).replace(numero, mascarado, 1)


def redact_cartorial(text: str) -> str:
    """Remove identificadores cartoriais do texto; idempotente."""
    out = scrub_bare_identifiers(scrub_identifiers(text))
    out = _CPF_PARCIAL.sub(_TOKEN_CPF_PARCIAL, out)
    out = _CONTA.sub(_mascara_conta, out)
    out = _CONTRATO.sub(_TOKEN_CONTRATO, out)
    out = _CEP.sub(_TOKEN_CEP, out)
    return _ENDERECO.sub(_TOKEN_ENDERECO, out)


def cartorial_pii_tipos(text: str) -> tuple[str, ...]:
    """Tipos presentes no texto, sem devolver o match — subconjunto de ``TIPOS_COBERTOS``."""
    found: list[str] = []
    if contains_identifier(text) or contains_bare_identifier(text):
        found.append("IDENTIFICADOR")
    if _CPF_PARCIAL.search(text):
        found.append("CPF_PARCIAL")
    if _CONTA.search(text):
        found.append("CONTA")
    if _CONTRATO.search(text):
        found.append("MATRICULA")
    if _ENDERECO.search(text):
        found.append("ENDERECO")
    if _CEP.search(text):
        found.append("CEP")
    return tuple(found)


def scan_view_model_pii(payload: object) -> tuple[ViewModelPiiHit, ...]:
    """Percorre o payload e aponta QUALQUER string com PII cartorial."""
    hits: list[ViewModelPiiHit] = []
    _walk(payload, "", hits)
    return tuple(hits)


# Redigir só no produtor deixa exposto tudo que já está gravado: o relatório
# re-renderiza artefato ARMAZENADO, e o anterior ao fix carrega a descrição
# cartorial crua que `/reports/{id}/data` serve (A40.l6). Leitura e escrita
# passam a usar a MESMA definição de PII — duas divergiriam. No-op sobre
# payload limpo: só reescreve string que o scanner acusaria.
def redact_view_model(node: object) -> object:
    """Gêmeo de escrita de ``scan_view_model_pii`` — redige o que ele acusaria."""
    if isinstance(node, dict):
        return {key: redact_view_model(value) for key, value in node.items()}
    if isinstance(node, list):
        return [redact_view_model(item) for item in node]
    if isinstance(node, str) and cartorial_pii_tipos(node):
        return redact_cartorial(node)
    return node


def _walk(node: object, path: str, hits: list[ViewModelPiiHit]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _walk(value, f"{path}.{key}" if path else str(key), hits)
        return
    if isinstance(node, list):
        for idx, item in enumerate(node):
            _walk(item, f"{path}[{idx}]", hits)
        return
    if isinstance(node, str):
        hits.extend(ViewModelPiiHit(path=path, tipo=tipo) for tipo in cartorial_pii_tipos(node))


__all__ = [
    "TIPOS_COBERTOS",
    "ViewModelPiiHit",
    "cartorial_pii_tipos",
    "redact_cartorial",
    "redact_view_model",
    "scan_view_model_pii",
]
