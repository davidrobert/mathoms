"""Superfície de diagnóstico (ADR-404) — tabelas cuja row EXPLICA a execução.

Todo write daqui abre sessão própria e é fail-open: perder o diagnóstico é
aceitável; perder a execução que ele documenta, não. As funções públicas deste
pacote **não aceitam** `Session` — compartilhar transação com a transição de
estado do run é o defeito que a ADR-404 fecha, e o boundary o torna impossível
em vez de proibido. Gate: `dev/check_diagnostic_session_isolation.py`.
"""
