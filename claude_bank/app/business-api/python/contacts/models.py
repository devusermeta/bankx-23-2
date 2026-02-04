"""
Contacts Service Models

Defines data models for beneficiaries and contact management.
"""

from pydantic import BaseModel
from typing import Optional


class Beneficiary(BaseModel):
    """
    Beneficiary model for registered payees.

    Represents a trusted recipient that a customer has pre-registered
    for faster, easier payments.
    """
    id: Optional[str] = None
    account_number: str
    name: str
    alias: str
    customer_id: Optional[str] = None
    source: Optional[str] = None  # 'csv' or 'json'
    added_date: Optional[str] = None


class AccountVerification(BaseModel):
    """
    Result of account number verification.

    Used during payment flow to validate recipient account.
    """
    valid: bool
    account_number: str
    account_holder_name: Optional[str] = None
    account_id: Optional[str] = None
    message: str
