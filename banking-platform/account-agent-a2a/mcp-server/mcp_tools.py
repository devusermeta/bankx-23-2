"""
MCP Tools for Account MCP Server

Exposes account and limits operations as MCP tools.
Combines tools from Classic Claude's account and limits servers.
"""

from fastmcp import FastMCP
import logging
from typing import Annotated
from services import AccountService, LimitsService
from data_loader_service import DataLoaderService

logger = logging.getLogger(__name__)

# Initialize data loader and services
data_loader = DataLoaderService()
account_service = AccountService(data_loader)
limits_service = LimitsService(data_loader)

# Create MCP server
mcp = FastMCP("Account MCP Server")


@mcp.tool(
    name="getAccountsByUserName",
    description="Get the list of all accounts for a specific user by their email address"
)
def get_accounts_by_user_name(
    userName: Annotated[str, "Email address of the logged-in user"]
):
    """
    Get all accounts for a user.
    
    Example: getAccountsByUserName("somchai.rattanakorn@example.com")
    """
    logger.info(f"getAccountsByUserName called with userName={userName}")
    return account_service.get_accounts_by_user_name(userName)


@mcp.tool(
    name="getAccountDetails",
    description="Get detailed account information including balance and payment methods"
)
def get_account_details(
    accountId: Annotated[str, "Unique identifier for the user account (e.g., CHK-001)"]
):
    """
    Get account details with balance.
    
    Example: getAccountDetails("CHK-001")
    """
    logger.info(f"getAccountDetails called with accountId={accountId}")
    account = account_service.get_account_details(accountId)
    
    if account is None:
        return {"error": "Account not found"}
    
    return account.model_dump()


@mcp.tool(
    name="getPaymentMethodDetails",
    description="Get payment method details with available balance"
)
def get_payment_method_details(
    paymentMethodId: Annotated[str, "Unique identifier for the payment method (e.g., PM-CHK-001)"]
):
    """
    Get payment method with balance.
    
    Example: getPaymentMethodDetails("PM-CHK-001")
    """
    logger.info(f"getPaymentMethodDetails called with paymentMethodId={paymentMethodId}")
    payment_method = account_service.get_payment_method_details(paymentMethodId)
    
    if payment_method is None:
        return {"error": "Payment method not found"}
    
    return payment_method.model_dump()


@mcp.tool(
    name="checkLimits",
    description="Check if a transaction is within account limits (balance, per-transaction limit, daily limit). Use for validation before payment approval."
)
def check_limits(
    accountId: Annotated[str, "Account ID to check (e.g., CHK-001)"],
    amount: Annotated[float, "Transaction amount to validate"],
    currency: Annotated[str, "Currency code (e.g., THB)"] = "THB"
):
    """
    Check if transaction is within all limits.
    
    Returns validation results:
    - sufficient_balance: bool
    - within_per_txn_limit: bool
    - within_daily_limit: bool
    - remaining_after: float
    - daily_limit_remaining_after: float
    - error_message: str (if any check fails)
    
    Example: checkLimits("CHK-001", 30000.0, "THB")
    """
    logger.info(f"checkLimits called: accountId={accountId}, amount={amount}, currency={currency}")
    result = limits_service.check_limits(accountId, amount, currency)
    return result.model_dump()


@mcp.tool(
    name="getAccountLimits",
    description="Get comprehensive transaction limits for an account. Returns per-transaction limit, daily limit, remaining today, and utilization percentage."
)
def get_account_limits(
    accountId: Annotated[str, "Account ID (e.g., CHK-001)"]
):
    """
    Get account limits information.
    
    Returns:
    - per_transaction_limit: Maximum per single transaction
    - daily_limit: Maximum total per day
    - remaining_today: Daily limit remaining
    - daily_used: Amount used today
    - utilization_percent: Daily limit utilization %
    - currency: Currency code
    
    Example: getAccountLimits("CHK-001")
    """
    logger.info(f"getAccountLimits called: accountId={accountId}")
    return limits_service.get_limits_info(accountId)
