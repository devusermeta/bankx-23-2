"""
JWT token validator for Microsoft Entra ID tokens.
Validates tokens using JWKS (JSON Web Key Set) from Microsoft's discovery endpoint.
"""
import jwt
import requests
from typing import Dict, Any, Optional
from jwt import PyJWKClient
from fastapi import HTTPException, status
from app.config.settings import settings


class TokenValidator:
    """
    Validates JWT tokens from Microsoft Entra ID using JWKS.
    """
    
    def __init__(self):
        # Get auth config from settings (which properly loads .env files)
        self.tenant_id = settings.AZURE_AUTH_TENANT_ID
        self.client_id = settings.AZURE_APP_CLIENT_ID
        
        print(f"🔐 [TOKEN_VALIDATOR] Initializing...")
        print(f"   Tenant ID: {self.tenant_id}")
        print(f"   Client ID: {self.client_id}")
        
        if not self.tenant_id or not self.client_id:
            print("❌ [TOKEN_VALIDATOR] Missing required environment variables")
            raise ValueError("AZURE_AUTH_TENANT_ID and AZURE_APP_CLIENT_ID must be set in environment")
        
        # JWKS endpoint for token validation
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self.jwks_client = PyJWKClient(self.jwks_uri)
        
        # Issuer for token validation
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        
        # Expected audience for access tokens (API scope URI)
        self.api_audience = f"api://{self.client_id}"
        
        print(f"✅ [TOKEN_VALIDATOR] Initialized successfully")
        print(f"   JWKS URI: {self.jwks_uri}")
        print(f"   Expected issuer: {self.issuer}")
        print(f"   Expected audience: {self.api_audience} OR {self.client_id}")
    
    def validate_token(self, token: str) -> Dict[str, Any]:
        """
        Validates a JWT token and returns the decoded claims.
        
        Args:
            token: The JWT token string (without "Bearer " prefix)
            
        Returns:
            Dict containing the decoded token claims
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get the signing key from JWKS
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Try to decode with API audience first (api://client_id)
            # If that fails, try with just client_id (for ID tokens)
            audiences_to_try = [
                self.api_audience,  # api://c37e62a7-a62f-4ebf-a7c2-d6a3d318f76b
                self.client_id,     # c37e62a7-a62f-4ebf-a7c2-d6a3d318f76b
            ]
            
            last_error = None
            for audience in audiences_to_try:
                try:
                    decoded_token = jwt.decode(
                        token,
                        signing_key.key,
                        algorithms=["RS256"],
                        audience=audience,  # Try each audience
                        issuer=self.issuer,  # Validate issuer is our tenant
                        options={
                            "verify_signature": True,
                            "verify_exp": True,
                            "verify_aud": True,
                            "verify_iss": True
                        }
                    )
                    # If successful, return the decoded token
                    return decoded_token
                except jwt.InvalidAudienceError as e:
                    last_error = e
                    continue  # Try next audience
            
            # If we got here, all audiences failed
            if last_error:
                raise last_error
            
            return decoded_token
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidAudienceError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidIssuerError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def extract_user_claims(self, decoded_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts relevant user claims from the decoded token.
        
        Args:
            decoded_token: The decoded JWT token claims
            
        Returns:
            Dict with extracted user information
        """
        return {
            "user_id": decoded_token.get("oid"),  # Object ID
            "email": decoded_token.get("preferred_username") or decoded_token.get("upn") or decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "roles": decoded_token.get("roles", []),  # App roles assigned to user
        }


# Singleton instance
_token_validator: Optional[TokenValidator] = None


def get_token_validator() -> TokenValidator:
    """
    Returns a singleton instance of TokenValidator.
    """
    global _token_validator
    if _token_validator is None:
        _token_validator = TokenValidator()
    return _token_validator
