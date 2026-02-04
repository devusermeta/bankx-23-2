"""
User context model for storing authenticated user information.
This is passed through the request chain to provide user identity to agents.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """
    Represents an authenticated user's context.
    
    Populated from the validated JWT token and customer mapping.
    """
    # Entra ID claims
    entra_user_id: str = Field(..., description="Object ID (oid) from Entra ID token")
    entra_user_email: str = Field(..., description="Email/UPN from Entra ID token")
    entra_user_name: Optional[str] = Field(None, description="Display name from token")
    entra_user_roles: List[str] = Field(default_factory=list, description="App roles assigned to user (Customer, BankAgent, BankTeller)")
    
    # BankX customer mapping
    customer_id: Optional[str] = Field(None, description="BankX customer ID (e.g., CUST-001) mapped from email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entra_user_id": "83ecd908-3efa-40b9-a998-604e6570497e",
                "entra_user_email": "somchai@bankxthb.onmicrosoft.com",
                "entra_user_name": "Somchai Rattanakorn",
                "entra_user_roles": ["Customer"],
                "customer_id": "CUST-001"
            }
        }
