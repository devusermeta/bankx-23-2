"""
Audited MCP Tool Wrapper for Azure AI Foundry agents.

This module provides a wrapper around MCPStreamableHTTPTool that adds audit logging
for compliance tracking when MCP tools are invoked by Azure AI Foundry agents.
"""

import logging
from typing import Any, Dict, Optional
from agent_framework import MCPStreamableHTTPTool
from app.observability.banking_telemetry import get_banking_telemetry

logger = logging.getLogger(__name__)


class AuditedMCPTool(MCPStreamableHTTPTool):
    """
    Wrapper around MCPStreamableHTTPTool that adds audit logging.
    
    This wrapper intercepts MCP tool calls and logs them for compliance purposes
    (GDPR, PCI-DSS). It tracks:
    - Which tool was called
    - By which user (customer_id)
    - What data was accessed
    - When and how long it took
    - Compliance flags (PCI_DSS, GDPR_PERSONAL_DATA, HIGH_VALUE_TRANSACTION)
    """
    
    def __init__(
        self,
        name: str,
        url: str,
        customer_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        mcp_server_name: Optional[str] = None
    ):
        """
        Initialize audited MCP tool.
        
        Args:
            name: Tool name (e.g., "Account MCP server client")
            url: MCP server URL
            customer_id: Customer ID for audit tracking
            thread_id: Thread ID for audit tracking
            mcp_server_name: Friendly name (e.g., "account", "transaction")
        """
        super().__init__(name=name, url=url)
        self.customer_id = customer_id
        self.thread_id = thread_id
        self.mcp_server_name = mcp_server_name or self._extract_server_name(url)
        self.telemetry = get_banking_telemetry()
        self._thread_context = None  # Will be set by agent
        
        logger.debug(
            f"Created audited MCP tool: {name} "
            f"(server={self.mcp_server_name}, customer={customer_id})"
        )
    
    def set_thread_context(self, thread):
        """Set thread context to extract actual thread_id during execution."""
        self._thread_context = thread
    
    def _extract_server_name(self, url: str) -> str:
        """Extract server name from URL for audit logging."""
        # Extract from common patterns like http://localhost:8070 -> "account"
        # or environment variables like MCP_ACCOUNT_URL -> "account"
        if "8070" in url or "account" in url.lower():
            return "account"
        elif "8071" in url or "transaction" in url.lower():
            return "transaction"
        elif "8072" in url or "payment" in url.lower():
            return "payment"
        elif "8073" in url or "limits" in url.lower():
            return "limits"
        elif "8074" in url or "contacts" in url.lower():
            return "contacts"
        elif "8075" in url or "prodinfo" in url.lower():
            return "prodinfo_faq"
        elif "8076" in url or "money" in url.lower() or "coach" in url.lower():
            return "ai_money_coach"
        elif "8077" in url or "escalation" in url.lower() or "comms" in url.lower():
            return "escalation_comms"
        else:
            return "unknown"
    
    async def call_tool(self, tool_name: str, **arguments) -> Any:
        """
        Override call_tool to add audit logging.
        
        This method is called when the Azure AI agent invokes an MCP tool.
        We wrap it with audit logging to track the invocation.
        """
        import time
        import sys
        from pathlib import Path
        import inspect
        
        # Add common to path if not already there
        common_path = str(Path(__file__).parent.parent.parent.parent / "common")
        if common_path not in sys.path:
            sys.path.insert(0, common_path)
        
        from observability import get_audit_logger
        
        audit_logger = get_audit_logger()
        start_time = time.perf_counter()
        
        # Try to get thread_id from multiple sources:
        # 1. From _thread_context (if set via set_thread_context)
        # 2. From the call stack (agent's thread context)
        # 3. Fall back to self.thread_id (initial value)
        actual_thread_id = self.thread_id
        
        if self._thread_context and hasattr(self._thread_context, 'service_thread_id'):
            actual_thread_id = self._thread_context.service_thread_id
            logger.info(f"🔍 Thread ID from context: {actual_thread_id}")
        else:
            # Try to find thread_id from call stack
            for frame_info in inspect.stack():
                frame_locals = frame_info.frame.f_locals
                # Look for 'thread' parameter in any parent frame
                if 'thread' in frame_locals:
                    thread_obj = frame_locals['thread']
                    if hasattr(thread_obj, 'service_thread_id'):
                        actual_thread_id = thread_obj.service_thread_id
                        logger.info(f"🔍 Thread ID from stack: {actual_thread_id}")
                        break
        
        logger.info(
            f"🔧 MCP Tool Call: {tool_name} on {self.mcp_server_name} "
            f"(customer={self.customer_id}, thread={actual_thread_id})"
        )
        
        # Determine operation type based on tool name
        operation_type = self._get_operation_type(tool_name)
        
        # Call parent implementation with audit context
        with audit_logger.audit_operation(
            operation_type=operation_type,
            mcp_server=self.mcp_server_name,
            tool_name=tool_name,
            user_id=self.customer_id or "unknown",
            thread_id=actual_thread_id,
            parameters=arguments
        ) as audit:
            try:
                # Call the actual MCP tool
                result = await super().call_tool(tool_name, **arguments)
                
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Extract audit information from result
                data_accessed = self._extract_data_accessed(tool_name, arguments, result)
                data_scope = self._get_data_scope(tool_name)
                compliance_flags = self._get_compliance_flags(tool_name, arguments, result)
                
                # Set audit information
                audit.set_data_accessed(data_accessed)
                audit.set_data_scope(data_scope)
                audit.set_result("success", f"Tool {tool_name} executed successfully")
                
                for flag in compliance_flags:
                    audit.add_compliance_flag(flag)
                
                logger.info(
                    f"✅ MCP Tool Success: {tool_name} "
                    f"({duration_ms:.2f}ms, flags={compliance_flags})"
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                logger.error(
                    f"❌ MCP Tool Error: {tool_name} failed after {duration_ms:.2f}ms: {e}"
                )
                
                audit.set_result("error", f"Tool {tool_name} failed: {str(e)}")
                raise
    
    def _get_operation_type(self, tool_name: str) -> str:
        """Determine operation type (READ/WRITE) based on tool name."""
        write_operations = [
            "submit", "create", "add", "update", "delete", "transfer",
            "pay", "register", "verify", "approve", "reject"
        ]
        
        tool_lower = tool_name.lower()
        for op in write_operations:
            if op in tool_lower:
                return "WRITE"
        
        return "READ"
    
    def _extract_data_accessed(
        self, tool_name: str, arguments: Dict[str, Any], result: Any
    ) -> list:
        """Extract list of data IDs that were accessed."""
        data_ids = []
        
        # Extract from arguments
        for key in ["account_id", "accountId", "transaction_id", "transactionId", 
                    "payment_id", "paymentId", "customer_id", "customerId"]:
            if key in arguments and arguments[key]:
                data_ids.append(str(arguments[key]))
        
        # Extract from result if it's a dict/list
        if isinstance(result, dict):
            # Single object result
            for key in ["account_id", "accountId", "transaction_id", "transactionId",
                       "payment_id", "paymentId", "id"]:
                if key in result and result[key]:
                    data_ids.append(str(result[key]))
        elif isinstance(result, list):
            # List of objects result
            for item in result[:10]:  # Limit to first 10 for audit log size
                if isinstance(item, dict):
                    for key in ["account_id", "accountId", "transaction_id", 
                               "transactionId", "payment_id", "paymentId", "id"]:
                        if key in item and item[key]:
                            data_ids.append(str(item[key]))
        
        return list(set(data_ids))  # Remove duplicates
    
    def _get_data_scope(self, tool_name: str) -> str:
        """Determine data scope based on tool name."""
        tool_lower = tool_name.lower()
        
        if "account" in tool_lower and "balance" in tool_lower:
            return "account_balance"
        elif "account" in tool_lower:
            return "account_details"
        elif "transaction" in tool_lower and "search" in tool_lower:
            return "transaction_history"
        elif "transaction" in tool_lower and "aggregate" in tool_lower:
            return "transaction_aggregation"
        elif "transaction" in tool_lower:
            return "transaction_details"
        elif "payment" in tool_lower or "transfer" in tool_lower:
            return "payment_execution"
        elif "limit" in tool_lower:
            return "account_limits"
        elif "contact" in tool_lower or "beneficiary" in tool_lower:
            return "contact_information"
        elif "product" in tool_lower or "faq" in tool_lower:
            return "product_information"
        else:
            return "general"
    
    def _get_compliance_flags(
        self, tool_name: str, arguments: Dict[str, Any], result: Any
    ) -> list:
        """Determine compliance flags based on operation."""
        flags = []
        tool_lower = tool_name.lower()
        
        # PCI-DSS: Financial account data
        if any(word in tool_lower for word in ["account", "payment", "card", "limit"]):
            flags.append("PCI_DSS")
        
        # GDPR: Personal data
        if any(word in tool_lower for word in ["transaction", "contact", "customer"]):
            flags.append("GDPR_PERSONAL_DATA")
        
        # High value transactions
        if "payment" in tool_lower or "transfer" in tool_lower:
            amount = arguments.get("amount") or arguments.get("value")
            if amount and float(amount) > 10000:
                flags.append("HIGH_VALUE_TRANSACTION")
        
        return flags
