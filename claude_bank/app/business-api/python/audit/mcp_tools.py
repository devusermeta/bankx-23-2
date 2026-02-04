"""
Audit MCP Server Tools

Exposes decision ledger and governance logging as MCP tools for agents.
"""

from fastmcp import FastMCP
import logging
from typing import Annotated, Optional, Dict, Any
from services import AuditService

logger = logging.getLogger(__name__)

# Initialize service
audit_service = AuditService()

mcp = FastMCP("Audit MCP Server")


@mcp.tool(
    name="logDecision",
    description="Log an agent decision to the Decision Ledger for governance and audit (US 1.A1-1.A3). Call this after every significant action."
)
def log_decision(
    conversationId: Annotated[str, "Conversation identifier"],
    customerId: Annotated[str, "Customer ID (hashed in production)"],
    agentName: Annotated[str, "Agent that performed action (e.g., 'TransactionAgent')"],
    action: Annotated[str, "Action type (e.g., 'VIEW_TRANSACTIONS', 'TRANSFER')"],
    input: Annotated[Dict[str, Any], "Sanitized input parameters"],
    output: Annotated[Dict[str, Any], "Output summary (structured output schema)"],
    rationale: Annotated[str, "Human-readable decision rationale"],
    policyEvaluation: Annotated[Optional[Dict], "Optional policy check results"] = None,
    approval: Annotated[Optional[Dict], "Optional approval metadata"] = None,
    metadata: Annotated[Optional[Dict], "Optional metadata (latency, request_id, etc.)"] = None
):
    """
    Log a decision to the Decision Ledger.

    PRIMARY function for US 1.A1-1.A3 (Agent Governance).

    Agents MUST call this after every significant action to create complete audit trail:
    - View Transactions → log decision
    - Transfer → log decision (including policy evaluation and approval)
    - Aggregations → log decision
    - Balance check → log decision

    Returns:
    - ledger_id: Unique identifier for the ledger entry

    Example:
    ```python
    logDecision(
        conversationId="CONV-123",
        customerId="CUST-001",
        agentName="TransactionAgent",
        action="VIEW_TRANSACTIONS",
        input={"account_id": "CHK-001", "from_date": "2025-10-20", "to_date": "2025-10-26"},
        output={"type": "TXN_TABLE", "total_count": 10},
        rationale="Retrieved transaction history for last week. Natural language date 'last week' normalized to 2025-10-20 to 2025-10-26."
    )
    ```
    """
    logger.info(f"logDecision called: action={action}, customer={customerId}, agent={agentName}")
    ledger_id = audit_service.log_decision(
        conversation_id=conversationId,
        customer_id=customerId,
        agent_name=agentName,
        action=action,
        input_data=input,
        output_data=output,
        rationale=rationale,
        policy_evaluation=policyEvaluation,
        approval=approval,
        metadata=metadata
    )
    return {"ledger_id": ledger_id, "status": "logged"}


@mcp.tool(
    name="getCustomerAuditHistory",
    description="Get audit history for a customer. Used by teller dashboard for compliance review."
)
def get_customer_audit_history(
    customerId: Annotated[str, "Customer ID"],
    limit: Annotated[int, "Maximum number of entries to return"] = 50
):
    """
    Get complete audit history for a customer.

    Returns all decision ledger entries for the customer (most recent first).

    Used by teller dashboard for US 1.T1-1.T5.

    Returns list of DecisionLedgerEntry objects.
    """
    logger.info(f"getCustomerAuditHistory called: customerId={customerId}, limit={limit}")
    entries = audit_service.get_customer_audit_history(customerId, limit)
    return [e.model_dump() for e in entries]


@mcp.tool(
    name="getAgentInteractions",
    description="Get agent interaction logs for teller dashboard (US 1.T3). Shows all agent-customer interactions."
)
def get_agent_interactions(
    customerId: Annotated[str, "Customer ID"],
    limit: Annotated[int, "Maximum number of interactions to return"] = 50
):
    """
    Get agent interaction logs for a customer.

    Returns simplified view of agent actions for teller dashboard.

    Used by US 1.T3 (View Agent Interaction Logs).

    Returns list of AgentInteractionLog objects.
    """
    logger.info(f"getAgentInteractions called: customerId={customerId}, limit={limit}")
    interactions = audit_service.get_agent_interactions(customerId, limit)
    return [i.model_dump() for i in interactions]


@mcp.tool(
    name="getDecisionAuditTrail",
    description="Get decision audit trail for teller dashboard (US 1.T4). Shows governance decisions with policy evaluations."
)
def get_decision_audit_trail(
    customerId: Annotated[str, "Customer ID"],
    limit: Annotated[int, "Maximum number of decisions to return"] = 50
):
    """
    Get decision audit trail for a customer.

    Returns governance view of decisions with policy evaluations and approvals.

    Used by US 1.T4 (View Decision Audit Trail).

    Returns list of DecisionAuditTrail objects.
    """
    logger.info(f"getDecisionAuditTrail called: customerId={customerId}, limit={limit}")
    trail = audit_service.get_decision_audit_trail(customerId, limit)
    return [t.model_dump() for t in trail]


@mcp.tool(
    name="searchAuditLogs",
    description="Search and filter audit logs (US 1.T5). Supports filtering by customer, agent, action, and date range."
)
def search_audit_logs(
    customerId: Annotated[Optional[str], "Filter by customer ID"] = None,
    agentName: Annotated[Optional[str], "Filter by agent name"] = None,
    action: Annotated[Optional[str], "Filter by action type"] = None,
    fromTimestamp: Annotated[Optional[str], "Start date/time (ISO 8601)"] = None,
    toTimestamp: Annotated[Optional[str], "End date/time (ISO 8601)"] = None,
    page: Annotated[int, "Page number (1-indexed)"] = 1,
    pageSize: Annotated[int, "Results per page"] = 50
):
    """
    Search audit logs with filters.

    Supports multiple filter criteria for flexible querying.

    Used by US 1.T5 (Search and Filter Records).

    Returns AuditSearchResult with paginated results.

    Example filters:
    - All transfers: action="TRANSFER"
    - All TransactionAgent actions: agentName="TransactionAgent"
    - Specific customer: customerId="CUST-001"
    - Date range: fromTimestamp="2025-10-20T00:00:00+07:00"
    """
    logger.info(f"searchAuditLogs called: customer={customerId}, agent={agentName}, action={action}")
    result = audit_service.search_audit_logs(
        customer_id=customerId,
        agent_name=agentName,
        action=action,
        from_timestamp=fromTimestamp,
        to_timestamp=toTimestamp,
        page=page,
        page_size=pageSize
    )
    return result.model_dump()


@mcp.tool(
    name="getConversationHistory",
    description="Get all decisions in a conversation. Shows complete decision history for a conversation."
)
def get_conversation_history(
    conversationId: Annotated[str, "Conversation ID"]
):
    """
    Get complete decision history for a conversation.

    Returns all ledger entries for the conversation in chronological order.

    Useful for debugging and understanding complete conversation flow.

    Returns list of DecisionLedgerEntry objects.
    """
    logger.info(f"getConversationHistory called: conversationId={conversationId}")
    entries = audit_service.get_conversation_history(conversationId)
    return [e.model_dump() for e in entries]
