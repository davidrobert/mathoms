"""IP do cliente = primeiro hop não-confiável do X-Forwarded-For, lido da direita.

Quem resolve é o ``ProxyHeadersMiddleware`` do uvicorn, instalado em
``main.py`` com ``settings.FORWARDED_ALLOW_IPS`` (ADR-232 §Emenda 2026-10-09).
Ele só lê o XFF quando o peer TCP é um proxy confiável e devolve o hop que esse
proxy acrescentou; os hops à esquerda são texto do cliente e nunca são
alcançados. Este módulo só lê o resultado — nenhum caller parseia XFF cru, e
os launchers rodam ``--no-proxy-headers`` para o CLI não decidir antes do app.

Por que não o hop mais à esquerda: o caminho do ``docker-compose.prod.yml`` é
cliente → Traefik da plataforma → Next.js (rewrite ``/api/*`` via httpxy sem
``xfwd``, que repassa o XFF intacto e não acrescenta hop) → uvicorn. O leftmost
só é o cliente real se o Traefik descarta o XFF de entrada. É o default dele
(``forwardedHeaders.insecure=false``, sem ``trustedIPs``) e o proxy default do
Coolify v4 não o altera — mas essa config vive fora do repo e é editável pela
UI da plataforma. Com ``insecure``/``trustedIPs`` (receita comum para pôr
Cloudflare na frente), o leftmost vira forjável: o atacante rotaciona um hop
falso por request e nunca enche o balde per-IP do login.

Limites: hops todos confiáveis → leftmost, forjável só de dentro da rede
privada. Cloudflare proxy ON sem somar as faixas do CF à env → balde por edge
do CF, não por cliente (RUNBOOK). Bind IPv4 (``--host 0.0.0.0``) → peer nunca
chega como ``::ffff:`` mapeado, que não casaria com as faixas IPv4.
"""

from __future__ import annotations

from starlette.requests import HTTPConnection


def client_ip(connection: HTTPConnection) -> str | None:
    """IP já resolvido pelo ``ProxyHeadersMiddleware`` — nunca o XFF cru."""
    return connection.client.host if connection.client else None
