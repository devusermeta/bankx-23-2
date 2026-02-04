"""
FastAPI dependencies for authentication.
Provides get_current_user dependency to extract and validate user from JWT token.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user_context import UserContext
from app.auth.token_validator import get_token_validator
from app.auth.user_mapper import get_user_mapper


# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserContext:
    """
    FastAPI dependency to extract and validate the current user from the Authorization header.
    
    Validates the JWT token and maps the user email to a customer_id.
    
    Args:
        credentials: HTTP Bearer token credentials from Authorization header
        
    Returns:
        UserContext with authenticated user information
        
    Raises:
        HTTPException: If authentication fails
    """
    print("🔐 [AUTH] get_current_user called")
    
    # Check if authentication is configured
    try:
        token_validator = get_token_validator()
        print("✅ [AUTH] Token validator initialized")
    except ValueError as e:
        # Auth not configured, return anonymous user (for development)
        print(f"❌ [AUTH] Token validator failed to initialize: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured"
        )
    except Exception as e:
        print(f"❌ [AUTH] Unexpected error initializing token validator: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication initialization error: {str(e)}"
        )
    
    # Check if token is provided
    if not credentials:
        print("❌ [AUTH] No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract token
    token = credentials.credentials
    print(f"✅ [AUTH] Token received (length: {len(token)})")
    
    # Validate token
    try:
        decoded_token = token_validator.validate_token(token)
        print(f"✅ [AUTH] Token validated successfully")
    except HTTPException as e:
        print(f"❌ [AUTH] Token validation failed: {e.detail}")
        raise
    except Exception as e:
        print(f"❌ [AUTH] Unexpected error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract user claims
    user_claims = token_validator.extract_user_claims(decoded_token)
    print(f"✅ [AUTH] User claims extracted: email={user_claims.get('email')}, oid={user_claims.get('user_id')}")
    
    if not user_claims.get("user_id") or not user_claims.get("email"):
        print(f"❌ [AUTH] Invalid token claims: {user_claims}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Map email to customer_id
    user_mapper = get_user_mapper()
    customer_id = user_mapper.get_customer_id_by_email(user_claims["email"])
    print(f"✅ [AUTH] Email mapped to customer_id: {user_claims['email']} → {customer_id}")
    
    if not customer_id:
        print(f"❌ [AUTH] No customer mapping found for {user_claims['email']}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {user_claims['email']} is not mapped to a BankX customer"
        )
    
    # Create UserContext
    user_context = UserContext(
        entra_user_id=user_claims["user_id"],
        entra_user_email=user_claims["email"],
        entra_user_name=user_claims.get("name"),
        entra_user_roles=user_claims.get("roles", []),
        customer_id=customer_id
    )
    
    print(f"✅ [AUTH] UserContext created successfully for {user_context.entra_user_email} (customer_id={user_context.customer_id})")
    
    # 🚀 Auto-initialize cache on first authentication
    import asyncio
    from app.cache import get_cache_manager
    cache_manager = get_cache_manager()
    
    # Always refresh cache on authentication (overwrite existing)
    print(f"🔄 [CACHE] Refreshing cache for {customer_id} on authentication")
    
    # Initialize cache in background (don't block auth)
    from app.cache.mcp_client import (
        get_account_mcp_client,
        get_transaction_mcp_client,
        get_contacts_mcp_client,
        get_limits_mcp_client
    )
    
    mcp_clients = {
        "account_mcp": get_account_mcp_client(),
        "transaction_mcp": get_transaction_mcp_client(),
        "contacts_mcp": get_contacts_mcp_client(),
        "limits_mcp": get_limits_mcp_client()
    }
    
    # Start cache initialization in background (will overwrite existing cache)
    asyncio.create_task(
        cache_manager.initialize_user_cache(
            customer_id=customer_id,
            user_email=user_claims["email"],
            mcp_clients=mcp_clients
        )
    )
    print(f"✅ [CACHE] Cache refresh started in background for {customer_id}")
    
    return user_context


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserContext]:
    """
    Optional version of get_current_user that returns None if authentication fails.
    Useful for endpoints that support both authenticated and anonymous access.
    
    Args:
        credentials: HTTP Bearer token credentials from Authorization header
        
    Returns:
        UserContext if authenticated, None otherwise
    """
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
