"""
Serviço de autenticação JWT e API Keys.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from infrastructure.persistence.models import ApiKeyModel
from settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Serviço para autenticação JWT e API Keys."""

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Cria um JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
            )
        to_encode.update({"exp": expire, "iat": datetime.utcnow()})
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """Verifica e decodifica um JWT token."""
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def hash_api_key(key: str) -> str:
        """Hash de API key usando SHA-256."""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """
        Gera uma nova API key.
        Retorna (key_plaintext, key_hash).
        """
        prefix = "gsfat"
        random_part = secrets.token_urlsafe(32)
        key = f"{prefix}_{random_part}"
        key_hash = AuthService.hash_api_key(key)
        return key, key_hash

    @staticmethod
    def verify_api_key(db: Session, key: str) -> Optional[ApiKeyModel]:
        """
        Verifica se uma API key é válida.
        Retorna o modelo ApiKeyModel se válida, None caso contrário.
        """
        key_hash = AuthService.hash_api_key(key)
        api_key = (
            db.query(ApiKeyModel)
            .filter(
                ApiKeyModel.key_hash == key_hash,
                ApiKeyModel.is_active == True,  # noqa: E712
            )
            .first()
        )

        if not api_key:
            return None

        # Verifica expiração
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Atualiza last_used_at
        api_key.last_used_at = datetime.utcnow()
        db.commit()

        return api_key

    @staticmethod
    def create_api_key_record(
        db: Session,
        name: str,
        scopes: list[str],
        expires_at: Optional[datetime] = None,
    ) -> tuple[str, ApiKeyModel]:
        """
        Cria um novo registro de API key no banco.
        Retorna (plaintext_key, ApiKeyModel).
        """
        key, key_hash = AuthService.generate_api_key()

        api_key_model = ApiKeyModel(
            id=str(uuid.uuid4()),
            key_hash=key_hash,
            name=name,
            scopes=scopes,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        db.add(api_key_model)
        db.commit()
        db.refresh(api_key_model)

        return key, api_key_model
