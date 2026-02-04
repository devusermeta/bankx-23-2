"""
User mapper to map Entra ID email/UPN to BankX customer_id.
Reads from dynamic_data/customers.json to find matching customer.
"""
import json
import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path

# Add common module to path for environment-aware utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "app" / "common"))
from path_utils import get_dynamic_data_dir


class UserMapper:
    """
    Maps Entra ID user email to BankX customer_id.
    """
    
    def __init__(self, customers_file: str = "customers.json"):
        """
        Initialize the user mapper.
        
        Args:
            customers_file: Filename of customers JSON file (default: customers.json)
        """
        # Use environment-aware path resolution
        dynamic_data_dir = get_dynamic_data_dir()
        self.customers_file = dynamic_data_dir / customers_file
        
        print(f"📁 [USER_MAPPER] Looking for customers file at: {self.customers_file}")
        
        if not self.customers_file.exists():
            print(f"❌ [USER_MAPPER] Customers file not found!")
            raise FileNotFoundError(f"Customers file not found: {self.customers_file}")
        
        self._load_customers()
    
    def _load_customers(self):
        """Load customer data from JSON file."""
        with open(self.customers_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.customers = data.get("customers", [])
    
    def get_customer_id_by_email(self, email: str) -> Optional[str]:
        """
        Maps an email address to a customer_id.
        
        Supports two email formats:
        1. BankX Entra ID email (e.g., somchai@bankxthb.onmicrosoft.com)
        2. Legacy email (e.g., somchai.rattanakorn@example.com)
        
        Args:
            email: The user's email address from Entra ID token
            
        Returns:
            customer_id (e.g., "CUST-001") or None if not found
        """
        if not email:
            return None
        
        email_lower = email.lower()
        
        # Method 1: Check bankx_email field (direct match)
        for customer in self.customers:
            bankx_email = customer.get("bankx_email", "").lower()
            if bankx_email and bankx_email == email_lower:
                return customer["customer_id"]
        
        # Method 2: Check legacy email field (direct match)
        for customer in self.customers:
            legacy_email = customer.get("email", "").lower()
            if legacy_email == email_lower:
                return customer["customer_id"]
        
        # Method 3: Extract username from BankX email and match with legacy email
        # e.g., "somchai@bankxthb.onmicrosoft.com" -> match "somchai.rattanakorn@example.com"
        if "@bankxthb.onmicrosoft.com" in email_lower:
            username = email_lower.split("@")[0]  # e.g., "somchai"
            
            for customer in self.customers:
                legacy_email = customer.get("email", "").lower()
                if legacy_email.startswith(username + "."):
                    return customer["customer_id"]
        
        return None
    
    def get_customer_info(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full customer information by customer_id.
        
        Args:
            customer_id: The customer ID (e.g., "CUST-001")
            
        Returns:
            Customer dict or None if not found
        """
        for customer in self.customers:
            if customer["customer_id"] == customer_id:
                return customer
        return None


# Singleton instance
_user_mapper: Optional[UserMapper] = None


def get_user_mapper() -> UserMapper:
    """
    Returns a singleton instance of UserMapper.
    """
    global _user_mapper
    if _user_mapper is None:
        _user_mapper = UserMapper()
    return _user_mapper
