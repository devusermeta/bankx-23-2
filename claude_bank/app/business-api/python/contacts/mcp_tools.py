"""
Contacts MCP Server Tools

Exposes beneficiary management and account verification as MCP tools for agents.
"""

from fastmcp import FastMCP
import logging
from typing import Annotated, Optional
from services import ContactsService
import sys
from pathlib import Path

# Add account service path
sys.path.insert(0, str(Path(__file__).parent.parent / "account"))

logger = logging.getLogger(__name__)

# Initialize service
contacts_service = ContactsService()

mcp = FastMCP("Contacts MCP Server")


@mcp.tool(
    name="getRegisteredBeneficiaries",
    description="Get list of registered beneficiaries for a specific account. Returns trusted payees that the customer has pre-registered."
)
def get_registered_beneficiaries(
    accountId: Annotated[str, "Account ID (e.g., CHK-001)"]
):
    """
    Get registered beneficiaries for an account.

    Returns list of beneficiaries with:
    - account_number: Beneficiary's account number
    - name: Full name
    - alias: Friendly name
    - added_date: When beneficiary was added

    Used by Payment Agent to show available beneficiaries for quick payments.
    """
    logger.info(f"getRegisteredBeneficiaries called: accountId={accountId}")
    beneficiaries = contacts_service.get_registered_beneficiaries(accountId)
    return [b.model_dump() for b in beneficiaries]


@mcp.tool(
    name="verifyAccountNumber",
    description="Verify if an account number exists in the banking system. Use when user provides an account number for payment to check if it's valid."
)
def verify_account_number(
    accountNumber: Annotated[str, "Account number to verify (format: XXX-XXX-XXX)"]
):
    """
    Verify account number for payments to unregistered beneficiaries.

    When user wants to pay someone NOT in their beneficiary list:
    1. Ask for account number
    2. Call this tool to verify
    3. If invalid, allow up to 3 retry attempts
    4. If valid, proceed with payment

    Returns:
    - valid: bool (True if account exists)
    - account_number: str (the account number)
    - account_holder_name: str (if valid)
    - account_id: str (if valid)
    - message: str (success or error message)
    """
    logger.info(f"verifyAccountNumber called: accountNumber={accountNumber}")
    result = contacts_service.verify_account_number(accountNumber)
    return result.model_dump()


@mcp.tool(
    name="addBeneficiary",
    description="Add a new beneficiary after successful payment. Call this ONLY when user explicitly confirms they want to save the recipient."
)
def add_beneficiary(
    accountId: Annotated[str, "Sender's account ID"],
    beneficiaryAccountNumber: Annotated[str, "Recipient's account number"],
    beneficiaryName: Annotated[str, "Recipient's full name"],
    alias: Annotated[Optional[str], "Optional friendly name for the beneficiary (e.g., 'Mom', 'Landlord')"] = None
):
    """
    Add beneficiary after successful payment to unregistered account.

    IMPORTANT: Only call this when:
    1. Payment was successful
    2. Recipient was NOT in beneficiary list
    3. User explicitly agrees to save (conversational prompt)

    Example conversation:
    Agent: "Payment successful! Would you like to save Somchai as a beneficiary for future payments?"
    User: "Yes"
    Agent: *calls this tool*

    Returns:
    - success: bool
    - message: str (confirmation or error message)
    """
    logger.info(f"addBeneficiary called: accountId={accountId}, beneficiaryAccountNumber={beneficiaryAccountNumber}")
    return contacts_service.add_beneficiary(accountId, beneficiaryAccountNumber, beneficiaryName, alias)


@mcp.tool(
    name="removeBeneficiary",
    description="Remove a beneficiary from customer's registered list."
)
def remove_beneficiary(
    accountId: Annotated[str, "Sender's account ID"],
    beneficiaryAccountNumber: Annotated[str, "Beneficiary's account number to remove"]
):
    """
    Remove a beneficiary from customer's list.

    Use when customer wants to remove a trusted payee from their saved contacts.

    Returns:
    - success: bool
    - message: str (confirmation or error message)
    """
    logger.info(f"removeBeneficiary called: accountId={accountId}, beneficiaryAccountNumber={beneficiaryAccountNumber}")
    return contacts_service.remove_beneficiary(accountId, beneficiaryAccountNumber)


@mcp.tool(
    name="isBeneficiaryRegistered",
    description="Check if a specific account number is registered as beneficiary for this customer. Use for payment flow decision making."
)
def is_beneficiary_registered(
    accountId: Annotated[str, "Sender's account ID"],
    beneficiaryAccountNumber: Annotated[str, "Account number to check"]
):
    """
    Check if account is registered as beneficiary.

    KEY for payment flow:
    - If registered → auto-populate payment details from beneficiary info
    - If not → ask user for account number and verify

    Returns:
    - is_registered: bool
    - beneficiary: dict (if registered, contains name, alias, etc.)
    - message: str
    """
    logger.info(f"isBeneficiaryRegistered called: accountId={accountId}, beneficiaryAccountNumber={beneficiaryAccountNumber}")
    return contacts_service.is_beneficiary_registered(accountId, beneficiaryAccountNumber)
