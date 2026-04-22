"""Use cases do agregado ``Auth`` (ADR-072 · ADR-101 R15).

Registro + login. ``current_user`` (GET /me) continua no router porque
depende de ``Depends(get_current_user)`` — dependency do FastAPI já
valida o JWT e retorna 401 antes do handler.
"""

from backend.app.application.auth.login_user import login_user
from backend.app.application.auth.register_user import register_user

__all__ = ["login_user", "register_user"]
