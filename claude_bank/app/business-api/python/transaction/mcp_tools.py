from fastmcp import FastMCP
import logging
from typing import Annotated, Literal
from services import transaction_service_singleton as service

logger = logging.getLogger(__name__)
mcp = FastMCP("Transaction MCP Server")


@mcp.tool(name="getTransactionsByRecipientName", description="Get transactions by recipient name")
def get_transactions_by_recipient_name(accountId: str, recipientName: str):
    logger.info("getTransactionsByRecipientName called with accountId=%s, recipientName=%s", accountId, recipientName)
    return service.get_transactions_by_recipient_name(accountId, recipientName)


@mcp.tool(name="getLastTransactions", description="Get the last N transactions for an account (default 5)")
def get_last_transactions(
    accountId: Annotated[str, "Account ID to query"],
    limit: Annotated[int, "Number of transactions to return (default 5)"] = 5
):
    logger.info("getLastTransactions called with accountId=%s, limit=%s", accountId, limit)
    return service.get_last_transactions(accountId, limit=limit)


@mcp.tool(
    name="searchTransactions",
    description="Search transactions by date range. Use for US 1.1 (View Transactions). Returns all transactions in the specified period."
)
def search_transactions(
    accountId: Annotated[str, "Account ID to search (e.g., CHK-001)"],
    fromDate: Annotated[str, "Start date in YYYY-MM-DD format"],
    toDate: Annotated[str, "End date in YYYY-MM-DD format"]
):
    """
    Search transactions by date range for US 1.1: View Transactions.

    This tool retrieves all transactions for an account within the specified date range.
    Dates should be in YYYY-MM-DD format and represent Asia/Bangkok timezone.
    """
    logger.info(
        "searchTransactions called with accountId=%s, fromDate=%s, toDate=%s",
        accountId, fromDate, toDate
    )
    return service.search_transactions(accountId, fromDate, toDate)


@mcp.tool(
    name="getTransactionDetails",
    description="Get detailed information for a specific transaction. Use for US 1.5 (View Single Transaction Details)."
)
def get_transaction_details(
    accountId: Annotated[str, "Account ID for authorization"],
    txnId: Annotated[str, "Transaction ID to retrieve (e.g., T000044)"]
):
    """
    Get complete details for a specific transaction for US 1.5: View Single Transaction Details.

    Returns all fields including counterparty information, timestamps, status, and amount.
    Verifies the transaction belongs to the specified account for authorization.
    """
    logger.info("getTransactionDetails called with accountId=%s, txnId=%s", accountId, txnId)
    result = service.get_transaction_details(accountId, txnId)

    if result is None:
        return {"error": f"Transaction {txnId} not found for account {accountId}"}

    return result


@mcp.tool(
    name="aggregateTransactions",
    description="Aggregate transactions by metric type (COUNT, SUM_IN, SUM_OUT, NET). Use for US 1.2 (Transaction Aggregations)."
)
def aggregate_transactions(
    accountId: Annotated[str, "Account ID to aggregate"],
    fromDate: Annotated[str, "Start date in YYYY-MM-DD format"],
    toDate: Annotated[str, "End date in YYYY-MM-DD format"],
    metricType: Annotated[
        Literal["COUNT", "SUM_IN", "SUM_OUT", "NET"],
        "Type of aggregation: COUNT (number of transactions), SUM_IN (total inbound), SUM_OUT (total outbound), NET (cash flow)"
    ]
):
    """
    Aggregate transactions by metric type for US 1.2: Transaction Aggregations.

    Metric types:
    - COUNT: Total number of transactions
    - SUM_IN: Sum of all inbound amounts (direction=IN)
    - SUM_OUT: Sum of all outbound amounts (direction=OUT)
    - NET: Net cash flow (SUM_IN - SUM_OUT)

    Returns aggregation results with breakdown details.
    """
    logger.info(
        "aggregateTransactions called with accountId=%s, fromDate=%s, toDate=%s, metricType=%s",
        accountId, fromDate, toDate, metricType
    )
    return service.aggregate_transactions(accountId, fromDate, toDate, metricType)


