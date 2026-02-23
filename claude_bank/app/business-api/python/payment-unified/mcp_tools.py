"""
Unified Payment MCP Server - MCP Tools

FastMCP tools for the simplified payment/transfer system.
These tools provide a unified interface consolidating:
- Account operations
- Beneficiary/contact management
- Limits checking
- Transfer execution
"""

import logging
from typing import Optional
from fastmcp import FastMCP
from services import TransferService

logger = logging.getLogger(__name__)

# Initialize FastMCP and service
mcp = FastMCP("BankX Payment Unified MCP")
transfer_service = TransferService()


@mcp.tool()
def getAccountsByUserName(username: str) -> dict:
    """
    Get all accounts for a customer by their username (BankX email).
    
    This is typically the first tool called to let the customer choose
    which account they want to transfer from.
    
    Args:
        username: Customer's BankX email address
        
    Returns:
        Dictionary with "accounts" list containing account details
    """
    try:
        print(f"\n\n{'#'*100}")
        print(f"# MCP TOOL CALLED: getAccountsByUserName")
        print(f"{'#'*100}")
        print(f"Parameters:")
        print(f"  - username: {username}")
        print(f"{'#'*100}\n")
        
        accounts = transfer_service.get_accounts_by_username(username)
        
        if not accounts:
            return {
                "success": False,
                "message": f"No accounts found for user: {username}",
                "accounts": []
            }
        
        # Convert to dict format for JSON serialization
        accounts_data = [
            {
                "account_id": acc.account_id,
                "account_no": acc.account_no,
                "cust_name": acc.cust_name,
                "acc_type": acc.acc_type,
                "currency": acc.currency,
                "available_balance": acc.available_balance
            }
            for acc in accounts
        ]
        
        return {
            "success": True,
            "count": len(accounts_data),
            "accounts": accounts_data
        }
        
    except Exception as e:
        logger.error(f"Error in getAccountsByUserName: {e}")
        return {
            "success": False,
            "message": f"Error fetching accounts: {str(e)}",
            "accounts": []
        }


@mcp.tool()
def prepareTransfer(
    username: str,
    recipient_identifier: str,
    amount: float,
    recipient_name: Optional[str] = None
) -> dict:
    """
    Prepare a transfer by validating all details in ONE call.

    This is the FIRST tool to call for any transfer request.
    It internally calls getAccountsByUserName + validateTransfer + checkLimits
    and returns all information needed to show the user a confirmation table.

    This is a READ-ONLY operation - no money moves. It only validates and
    returns preview data.

    Args:
        username: Customer's BankX email address (e.g., "nattaporn@bankxthb.onmicrosoft.com")
        recipient_identifier: Recipient's name or alias (e.g., "Somchai Rattanakorn")
        amount: Transfer amount in THB (e.g., 800)
        recipient_name: Optional - same as recipient_identifier if not provided

    Returns:
        Dictionary with ALL data needed for confirmation table:
        - sender_account_id: Use this in executeTransfer
        - recipient_account_id: Use this in executeTransfer
        - sender_name, sender_account_no, current_balance
        - recipient_name, recipient_account_no
        - amount, currency
        - new_balance_preview (balance after transfer)
        - daily_limit_remaining
        - validation_status: "success" or "error"
        - error_message: Only present if validation_status is "error"
    """
    try:
        print(f"\n\n{'#'*100}")
        print(f"# MCP TOOL CALLED: prepareTransfer")
        print(f"{'#'*100}")
        print(f"Parameters:")
        print(f"  - username: {username}")
        print(f"  - recipient_identifier: {recipient_identifier}")
        print(f"  - amount: {amount:,.2f} THB")
        print(f"  - recipient_name: {recipient_name or '(not provided)'}")
        print(f"{'#'*100}\n")

        # Step 1: Get accounts for this user
        accounts = transfer_service.get_accounts_by_username(username)
        if not accounts:
            return {
                "validation_status": "error",
                "error_message": f"No accounts found for user: {username}"
            }

        # Use the first (primary) account
        sender_account = accounts[0]
        sender_account_id = sender_account.account_id

        print(f"✅ [prepareTransfer] Sender account: {sender_account_id} ({sender_account.cust_name})")

        # Step 2: Validate transfer (checks recipient + limits in one call)
        result = transfer_service.validate_transfer(
            sender_account_id,
            recipient_identifier,
            amount,
            recipient_name or recipient_identifier
        )

        if not result.valid:
            return {
                "validation_status": "error",
                "error_message": result.error_message or "Transfer validation failed",
                "sender_account_id": sender_account_id,
                "current_balance": result.sender_balance
            }

        # Build the complete confirmation payload
        new_balance_preview = result.checks.remaining_after
        daily_limit_remaining = result.checks.daily_limit_remaining_after

        print(f"✅ [prepareTransfer] Validation passed!")
        print(f"   {result.sender_name} → {result.recipient_name}")
        print(f"   Amount: {amount:,.2f} THB")
        print(f"   New balance preview: {new_balance_preview:,.2f} THB")

        return {
            "validation_status": "success",
            # IDs needed for executeTransfer
            "sender_account_id": result.sender_account_id,
            "recipient_account_id": result.recipient_account_id,
            # Sender details
            "sender_name": result.sender_name,
            "sender_account_no": sender_account.account_no,
            "current_balance": result.sender_balance,
            # Recipient details
            "recipient_name": result.recipient_name,
            "recipient_account_no": result.recipient_account_no,
            # Transfer details
            "amount": result.amount,
            "currency": result.currency,
            "payment_method": "Bank Transfer",
            # Balance preview
            "new_balance_preview": new_balance_preview,
            "daily_limit_remaining": daily_limit_remaining
        }

    except Exception as e:
        logger.error(f"Error in prepareTransfer: {e}")
        return {
            "validation_status": "error",
            "error_message": f"Error preparing transfer: {str(e)}"
        }


@mcp.tool()
def getAccountDetails(account_id: str) -> dict:
    """
    Get detailed information about a specific account including balance and limits.
    
    Args:
        account_id: The account ID (e.g., "CHK-001")
        
    Returns:
        Dictionary with account details, balance, and limit information
    """
    try:
        details = transfer_service.get_account_details(account_id)
        
        if not details:
            return {
                "success": False,
                "message": f"Account not found: {account_id}"
            }
        
        return {
            "success": True,
            "account": details
        }
        
    except Exception as e:
        logger.error(f"Error in getAccountDetails: {e}")
        return {
            "success": False,
            "message": f"Error fetching account details: {str(e)}"
        }


@mcp.tool()
def getRegisteredBeneficiaries(customer_id: str) -> dict:
    """
    Get all registered beneficiaries/contacts for a customer.
    
    This allows users to transfer to saved recipients by using their alias
    or account number. Not required if user provides the account number directly.
    
    Args:
        customer_id: Customer ID (e.g., "CUST-001")
        
    Returns:
        Dictionary with "beneficiaries" list
    """
    try:
        beneficiaries = transfer_service.get_registered_beneficiaries(customer_id)
        
        # Convert to dict format
        beneficiaries_data = [
            {
                "name": b.name,
                "account_number": b.account_number,
                "alias": b.alias,
                "added_date": b.added_date
            }
            for b in beneficiaries
        ]
        
        return {
            "success": True,
            "count": len(beneficiaries_data),
            "beneficiaries": beneficiaries_data
        }
        
    except Exception as e:
        logger.error(f"Error in getRegisteredBeneficiaries: {e}")
        return {
            "success": False,
            "message": f"Error fetching beneficiaries: {str(e)}",
            "beneficiaries": []
        }


@mcp.tool()
def checkLimits(account_id: str, amount: float) -> dict:
    """
    Check if a transaction amount is within all limits.
    
    IMPORTANT: This should be called TWICE:
    1. BEFORE showing the approval request to the user
    2. BEFORE executing the transfer (after approval)
    
    Checks three things:
    - Sufficient balance
    - Within per-transaction limit (50,000 THB)
    - Within daily limit (200,000 THB, resets at midnight)
    
    Args:
        account_id: Sender's account ID
        amount: Transaction amount in THB
        
    Returns:
        Dictionary with validation results and remaining limits
    """
    try:
        result = transfer_service.check_limits(account_id, amount)
        
        return {
            "success": True,
            "checks": {
                "sufficient_balance": result.sufficient_balance,
                "within_per_txn_limit": result.within_per_txn_limit,
                "within_daily_limit": result.within_daily_limit,
                "all_pass": (
                    result.sufficient_balance and 
                    result.within_per_txn_limit and 
                    result.within_daily_limit
                )
            },
            "details": {
                "current_balance": result.current_balance,
                "remaining_after": result.remaining_after,
                "daily_limit_remaining_after": result.daily_limit_remaining_after
            },
            "error_message": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Error in checkLimits: {e}")
        return {
            "success": False,
            "message": f"Error checking limits: {str(e)}"
        }


@mcp.tool()
def validateTransfer(
    sender_account_id: str,
    recipient_identifier: str,
    amount: float,
    recipient_name: Optional[str] = None
) -> dict:
    """
    Validate a complete transfer request BEFORE asking for user approval.
    
    This consolidates:
    - Sender account verification
    - Recipient lookup (by account number or beneficiary alias)
    - All limits checks (balance, per-txn, daily)
    
    Call this first, then show the approval request with the validated details.
    
    Args:
        sender_account_id: Sender's account ID
        recipient_identifier: Recipient's account number or beneficiary alias
        amount: Transfer amount in THB
        recipient_name: Optional recipient name for verification
        
    Returns:
        Dictionary with complete validation results
    """
    try:
        print(f"\n\n{'#'*100}")
        print(f"# MCP TOOL CALLED: validateTransfer")
        print(f"{'#'*100}")
        print(f"Parameters:")
        print(f"  - sender_account_id: {sender_account_id}")
        print(f"  - recipient_identifier: {recipient_identifier}")
        print(f"  - amount: {amount:,.2f} THB")
        # Default recipient_name to recipient_identifier if not provided or null
        if not recipient_name:
            recipient_name = recipient_identifier

        print(f"  - recipient_name: {recipient_name}")
        print(f"{'#'*100}\n")
        
        result = transfer_service.validate_transfer(
            sender_account_id,
            recipient_identifier,
            amount,
            recipient_name
        )
        
        return {
            "success": result.valid,
            "validation": {
                "valid": result.valid,
                "sender": {
                    "account_id": result.sender_account_id,
                    "name": result.sender_name,
                    "balance": result.sender_balance
                },
                "recipient": {
                    "account_id": result.recipient_account_id,
                    "name": result.recipient_name,
                    "account_no": result.recipient_account_no
                } if result.recipient_account_id else None,
                "amount": result.amount,
                "currency": result.currency,
                "limits_check": {
                    "sufficient_balance": result.checks.sufficient_balance,
                    "within_per_txn_limit": result.checks.within_per_txn_limit,
                    "within_daily_limit": result.checks.within_daily_limit,
                    "all_pass": (
                        result.checks.sufficient_balance and
                        result.checks.within_per_txn_limit and
                        result.checks.within_daily_limit
                    ),
                    "remaining_after": result.checks.remaining_after,
                    "daily_limit_remaining_after": result.checks.daily_limit_remaining_after
                }
            },
            "error_message": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Error in validateTransfer: {e}")
        return {
            "success": False,
            "message": f"Error validating transfer: {str(e)}"
        }


@mcp.tool()
def executeTransfer(
    sender_account_id: str,
    recipient_account_id: str,
    amount: float,
    description: str = "Transfer"
) -> dict:
    """
    Execute a transfer AFTER user approval.
    
    CRITICAL: This must ONLY be called after:
    1. validateTransfer() returned success
    2. User approved the transfer
    
    This will:
    - Re-check all limits (things may have changed since validation)
    - Debit sender account
    - Credit recipient account
    - Update daily limit remaining
    - Create transaction records for both accounts
    
    Args:
        sender_account_id: Sender's account ID
        recipient_account_id: Recipient's account ID
        amount: Transfer amount in THB
        description: Transaction description
        
    Returns:
        Dictionary with execution results including transaction ID
    """
    try:
        print(f"\n\n{'#'*100}")
        print(f"# MCP TOOL CALLED: executeTransfer")
        print(f"{'#'*100}")
        print(f"Parameters:")
        print(f"  - sender_account_id: {sender_account_id}")
        print(f"  - recipient_account_id: {recipient_account_id}")
        print(f"  - amount: {amount:,.2f} THB")
        print(f"  - description: {description}")
        print(f"{'#'*100}\n")
        
        result = transfer_service.execute_transfer(
            sender_account_id,
            recipient_account_id,
            amount,
            description
        )
        
        if not result.success:
            return {
                "success": False,
                "message": result.error_message,
                "sender_balance": result.sender_new_balance
            }
        
        return {
            "success": True,
            "transaction": {
                "transaction_id": result.transaction_id,
                "sender_new_balance": result.sender_new_balance,
                "recipient_new_balance": result.recipient_new_balance,
                "daily_limit_remaining": result.daily_limit_remaining,
                "message": f"Transfer completed successfully. Transaction ID: {result.transaction_id}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in executeTransfer: {e}")
        return {
            "success": False,
            "message": f"Error executing transfer: {str(e)}"
        }
