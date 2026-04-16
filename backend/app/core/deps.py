"""FastAPI dependencies — auth, DB session."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import decode_access_token_payload
from backend.app.models.user import User

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT, return the authenticated user.

    F9 · forced logout — se o `tv` do token é menor que `User.token_version`
    atual, o token foi invalidado (ex: user removido de workspace) e
    retornamos 401 com código `token_revoked` para o frontend detectar e
    limpar a sessão.
    """
    payload = decode_access_token_payload(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )
    user_id = payload["sub"]
    token_tv = payload.get("tv", 0)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )
    if token_tv < user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "token_revoked",
                "message": "Sua sessão foi encerrada. Faça login novamente.",
            },
        )
    return user
