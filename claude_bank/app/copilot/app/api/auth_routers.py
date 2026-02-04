from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.config.settings import settings
from app.models.user_context import UserContext
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/auth_setup")
def auth_setup():
    """
    Returns authentication configuration for the frontend MSAL client.
    This endpoint is called by the frontend to configure Microsoft Entra ID authentication.
    """
    tenant_id = settings.AZURE_AUTH_TENANT_ID
    client_id = settings.AZURE_APP_CLIENT_ID
    
    # Debug logging
    print(f"[AUTH_SETUP] ✅ AZURE_AUTH_TENANT_ID: {tenant_id}")
    print(f"[AUTH_SETUP] ✅ AZURE_APP_CLIENT_ID: {client_id}")
    
    # If auth configuration is not set, disable login
    if not tenant_id or not client_id:
        print("[AUTH_SETUP] ❌ Auth configuration missing, returning useLogin=false")
        return JSONResponse(content={"useLogin": False})
    
    # Define the API scope
    api_scope = f"api://{client_id}/BankX.Access"
    
    return JSONResponse(content={
        "useLogin": True,
        "msalConfig": {
            "auth": {
                "clientId": client_id,
                "authority": f"https://login.microsoftonline.com/{tenant_id}",
                "redirectUri": "/",
                "postLogoutRedirectUri": "/",
                "navigateToLoginRequestUrl": True
            },
            "cache": {
                "cacheLocation": "localStorage",
                "storeAuthStateInCookie": False
            }
        },
        "loginRequest": {
            # Include offline_access to get refresh tokens for longer sessions
            "scopes": ["openid", "profile", "email", "offline_access", api_scope]
        },
        "tokenRequest": {
            "scopes": [api_scope, "offline_access"]
        }
    })


@router.get("/whoami")
async def whoami(user_context: UserContext = Depends(get_current_user)):
    """
    Simple authenticated endpoint that returns user info.
    Calling this triggers cache initialization in get_current_user dependency.
    Frontend should call this immediately after login to pre-populate cache.
    """
    return JSONResponse(content={
        "customer_id": user_context.customer_id,
        "email": user_context.entra_user_email,
        "message": "Cache initialization triggered"
    })
