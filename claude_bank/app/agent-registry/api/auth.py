"""Authentication utilities for agent registry."""
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config.settings import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


def create_agent_token(agent_id: str, agent_name: str) -> str:
    """Create JWT token for agent.

    Args:
        agent_id: Agent ID
        agent_name: Agent name

    Returns:
        JWT token string
    """
    payload = {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "exp": datetime.utcnow() + timedelta(seconds=settings.jwt_expiration_seconds),
        "iat": datetime.utcnow(),
        "iss": "bankx-agent-registry",
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def verify_agent_token(token: str) -> dict:
    """Verify and decode agent JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> dict:
    """Get current authenticated agent from request.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If authentication fails
    """
    if not settings.auth_enabled:
        # If auth is disabled, return a dummy payload
        return {"agent_id": "system", "agent_name": "SystemAgent"}

    token = credentials.credentials
    return verify_agent_token(token)


async def verify_agent_or_skip(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
) -> Optional[dict]:
    """Verify agent token or skip if auth is disabled.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Decoded token payload or None if auth disabled
    """
    if not settings.auth_enabled:
        return None

    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    return verify_agent_token(credentials.credentials)
