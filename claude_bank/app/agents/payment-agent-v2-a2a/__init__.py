"""
Payment Agent v2 - Simplified Transfer Agent

Streamlined payment/transfer agent with unified MCP server.
Replaces payment-agent-a2a with simpler validate → approve → execute flow.
"""

from .agent_handler import PaymentAgentHandler
from .audited_mcp_tool import AuditedMCPTool

__version__ = "2.0.0"
__all__ = ["PaymentAgentHandler", "AuditedMCPTool"]
