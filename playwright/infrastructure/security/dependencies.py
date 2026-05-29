"""Dependencies para autenticacao na API."""

from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from infrastructure.persistence.postgres_job_repository import get_db
from infrastructure.security.auth_service import AuthService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_header)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Dependency para verificar API key em endpoints protegidos.
    Retorna informacoes da API key se for valida.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    api_key_model = AuthService.verify_api_key(db, api_key)

    if not api_key_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return {
        "id": api_key_model.id,
        "name": api_key_model.name,
        "scopes": api_key_model.scopes,
    }


def require_scope(required_scope: str):
    """
    Dependency factory para verificar se a API key tem um scope especifico.
    """

    async def _verify_scope(api_key_info: Annotated[dict, Depends(verify_api_key)]):
        if required_scope not in api_key_info["scopes"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}",
            )
        return api_key_info

    return _verify_scope
