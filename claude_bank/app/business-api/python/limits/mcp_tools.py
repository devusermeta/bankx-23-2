"""
Limits MCP Server Tools

Exposes transaction limit checking as MCP tools for agents.
"""

from fastmcp import FastMCP
import logging
from typing import Annotated
from services import LimitsService

logger = logging.getLogger(__name__)

# Initialize service with StateManager
limits_service = LimitsService()

mcp = FastMCP("Limits MCP Server")


@mcp.tool(
    name="checkLimits",
    description="Check if a transaction is within account limits (balance, per-transaction limit, daily limit). Use for Policy Gate validation in US 1.4."
)
def check_limits(
    accountId: Annotated[str, "Account ID to check (e.g., CHK-001)"],
    amount: Annotated[float, "Transaction amount to validate"],
    currency: Annotated[str, "Currency code (e.g., THB)"] = "THB"
):
    """
    Check transaction limits for Policy Gate validation.

    Returns detailed validation results:
    - sufficient_balance: bool
    - within_per_txn_limit: bool
    - within_daily_limit: bool
    - remaining_after: float (balance after transaction)
    - daily_limit_remaining_after: float (daily limit remaining after)
    - error_message: str (if any check fails)

    This is used by Payment Agent before presenting TRANSFER_APPROVAL card.
    """
    logger.info(f"checkLimits called: accountId={accountId}, amount={amount}, currency={currency}")
    result = limits_service.check_limits(accountId, amount, currency)
    return result.model_dump()


@mcp.tool(
    name="getAccountLimits",
    description="Get transaction limits for an account. Returns per-transaction limit, daily limit, remaining today, and utilization percentage."
)
def get_account_limits(
    accountId: Annotated[str, "Account ID (e.g., CHK-001)"]
):
    """
    Get comprehensive limits information for an account.

    Returns:
    - per_transaction_limit: Maximum per single transaction
    - daily_limit: Maximum total per day
    - remaining_today: Daily limit remaining
    - daily_used: Amount used today
    - utilization_percent: Daily limit utilization %
    - currency: Currency code

    Used by Account Agent for US 1.3 (BALANCE_CARD).
    """
    logger.info(f"getAccountLimits called: accountId={accountId}")
    return limits_service.get_limits_info(accountId)


@mcp.tool(
    name="updateLimitsAfterTransaction",
    description="Update daily limits after a successful transaction. Called by Payment Service internally."
)
def update_limits_after_transaction(
    accountId: Annotated[str, "Account ID"],
    amount: Annotated[float, "Transaction amount (positive value)"]
):
    """
    Update remaining daily limit after transaction.

    This is called by Payment Service after successful payment execution.
    Deducts the amount from remaining_today limit.

    NOTE: This should only be called by Payment Service, not by agents directly.
    """
    logger.info(f"updateLimitsAfterTransaction called: accountId={accountId}, amount={amount}")
    limits_service.update_limits_after_transaction(accountId, amount)
    return {"status": "ok", "message": f"Limits updated for account {accountId}"}
