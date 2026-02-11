"""
Microsoft Graph API client for authentication and API access.
"""

import asyncio
import logging
from typing import Optional
import httpx
from datetime import datetime, timedelta
from config import settings

logger = logging.getLogger(__name__)


class GraphAPIClient:
    """
    Microsoft Graph API client with token management.
    """
    
    def __init__(self):
        self.client_id = settings.AZURE_CLIENT_ID
        self.client_secret = settings.AZURE_CLIENT_SECRET
        self.tenant_id = settings.AZURE_TENANT_ID
        self.scope = settings.GRAPH_SCOPE
        
        self.token_endpoint = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.graph_endpoint = settings.GRAPH_API_ENDPOINT
        
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._lock = asyncio.Lock()
        
    async def get_access_token(self) -> str:
        """
        Get valid access token (refreshes if expired).
        
        Returns:
            Access token string
        """
        async with self._lock:
            # Check if token is still valid
            if self._access_token and self._token_expiry:
                if datetime.now() < self._token_expiry - timedelta(minutes=5):
                    return self._access_token
            
            # Request new token
            logger.info("Requesting new Microsoft Graph access token")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_endpoint,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": self.scope,
                        "grant_type": "client_credentials"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to get access token: {response.status_code} - {response.text}")
                    raise Exception(f"Failed to authenticate with Microsoft Graph: {response.text}")
                
                token_data = response.json()
                self._access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
                
                logger.info(f"Successfully obtained access token (expires in {expires_in}s)")
                return self._access_token
    
    async def get_headers(self) -> dict:
        """
        Get HTTP headers with valid access token.
        
        Returns:
            Dictionary of HTTP headers
        """
        token = await self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """
        Perform GET request to Microsoft Graph API.
        
        Args:
            endpoint: API endpoint (relative to graph_endpoint)
            params: Query parameters
            
        Returns:
            Response JSON
        """
        headers = await self.get_headers()
        url = f"{self.graph_endpoint}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                logger.error(f"GET {endpoint} failed: {response.status_code} - {response.text}")
                raise Exception(f"Graph API GET failed: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def post(self, endpoint: str, data: dict) -> dict:
        """
        Perform POST request to Microsoft Graph API.
        
        Args:
            endpoint: API endpoint (relative to graph_endpoint)
            data: Request body
            
        Returns:
            Response JSON
        """
        headers = await self.get_headers()
        url = f"{self.graph_endpoint}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            
            if response.status_code not in [200, 201, 202]:
                logger.error(f"POST {endpoint} failed: {response.status_code} - {response.text}")
                raise Exception(f"Graph API POST failed: {response.status_code} - {response.text}")
            
            # Some endpoints return 204 No Content
            if response.status_code == 204 or not response.text:
                return {"success": True}
            
            return response.json()
    
    async def patch(self, endpoint: str, data: dict) -> dict:
        """
        Perform PATCH request to Microsoft Graph API.
        
        Args:
            endpoint: API endpoint (relative to graph_endpoint)
            data: Request body
            
        Returns:
            Response JSON
        """
        headers = await self.get_headers()
        url = f"{self.graph_endpoint}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(url, headers=headers, json=data)
            
            if response.status_code not in [200, 204]:
                logger.error(f"PATCH {endpoint} failed: {response.status_code} - {response.text}")
                raise Exception(f"Graph API PATCH failed: {response.status_code} - {response.text}")
            
            if response.status_code == 204 or not response.text:
                return {"success": True}
            
            return response.json()


# Global instance
_graph_client: Optional[GraphAPIClient] = None


async def get_graph_client() -> GraphAPIClient:
    """Get or create global Graph API client."""
    global _graph_client
    if _graph_client is None:
        _graph_client = GraphAPIClient()
    return _graph_client
