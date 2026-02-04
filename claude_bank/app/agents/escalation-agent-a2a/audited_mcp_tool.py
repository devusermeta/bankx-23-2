# """
# Simple Audited MCP Tool Wrapper for A2A Service

# Lightweight wrapper around MCPStreamableHTTPTool that adds basic audit logging
# for compliance tracking when MCP tools are invoked.

# This is a simplified version of the full AuditedMCPTool from the copilot service,
# adapted for the standalone A2A service without banking telemetry dependencies.
# """

# import logging
# from agent_framework import MCPStreamableHTTPTool

# logger = logging.getLogger(__name__)


# class AuditedMCPTool(MCPStreamableHTTPTool):
#     """
#     Wrapper around MCPStreamableHTTPTool that adds audit logging.
    
#     Tracks:
#     - Which tool was called
#     - By which customer (customer_id)
#     - In which conversation (thread_id)
#     - When it was called
#     """
    
#     def __init__(
#         self,
#         name: str,
#         url: str,
#         customer_id: str | None = None,
#         thread_id: str | None = None,
#         mcp_server_name: str | None = None,
#         **kwargs
#     ):
#         """
#         Initialize audited MCP tool.
        
#         Args:
#             name: Tool name (e.g., "Account MCP Server")
#             url: MCP server URL
#             customer_id: Customer ID for audit tracking
#             thread_id: Thread ID for audit tracking
#             mcp_server_name: Friendly name (e.g., "account", "limits")
#             **kwargs: Additional arguments passed to MCPStreamableHTTPTool
#         """
#         super().__init__(name=name, url=url, **kwargs)
#         self.customer_id = customer_id
#         self.thread_id = thread_id
#         self.mcp_server_name = mcp_server_name or self._extract_server_name(url)
        
#         logger.debug(
#             f"[AUDIT] Created MCP tool: {name} "
#             f"(server={self.mcp_server_name}, customer={customer_id}, thread={thread_id})"
#         )
    
#     def _extract_server_name(self, url: str) -> str:
#         """Extract server name from URL for audit logging."""
#         if "8070" in url or "account" in url.lower():
#             return "account"
#         elif "8071" in url or "transaction" in url.lower():
#             return "transaction"
#         elif "8072" in url or "payment" in url.lower():
#             return "payment"
#         elif "8073" in url or "limits" in url.lower():
#             return "limits"
#         elif "8074" in url or "contacts" in url.lower():
#             return "contacts"
#         elif "8075" in url or "audit" in url.lower():
#             return "audit"
#         elif "8076" in url or "prodinfo" in url.lower():
#             return "prodinfo_faq"
#         elif "8077" in url or "coach" in url.lower():
#             return "ai_money_coach"
#         elif "8078" in url or "escalation" in url.lower():
#             return "escalation_comms"
#         else:
#             return "unknown"
    
#     async def connect(self):
#         """Connect to MCP server with audit logging."""
#         logger.info(
#             f"[AUDIT] 🔌 Connecting to {self.mcp_server_name.upper()} MCP server "
#             f"(customer={self.customer_id}, thread={self.thread_id})"
#         )
        
#         try:
#             result = await super().connect()
#             logger.info(
#                 f"[AUDIT] ✅ Connected to {self.mcp_server_name.upper()} MCP server "
#                 f"(customer={self.customer_id})"
#             )
#             return result
#         except Exception as e:
#             logger.error(
#                 f"[AUDIT] ❌ Failed to connect to {self.mcp_server_name.upper()} MCP server: {e} "
#                 f"(customer={self.customer_id})"
#             )
#             raise
    
#     def __repr__(self):
#         return (
#             f"AuditedMCPTool(name={self.name}, server={self.mcp_server_name}, "
#             f"customer={self.customer_id}, thread={self.thread_id})"
#         )


# # For backward compatibility
# __all__ = ["AuditedMCPTool"]


"""
Audited MCP Tool Wrapper for A2A Service with Full Compliance Logging

Wrapper around MCPStreamableHTTPTool that adds comprehensive audit logging
for compliance tracking (GDPR, PCI-DSS) when MCP tools are invoked.

Logs MCP tool invocations to: observability/mcp_audit_YYYY-MM-DD.json
"""

import logging
import sys
import time
from pathlib import Path
from typing import Any
from agent_framework import MCPStreamableHTTPTool

# Add common observability to path
common_path = str(Path(__file__).parent.parent.parent / "common")
if common_path not in sys.path:
    sys.path.insert(0, common_path)

from observability import get_audit_logger

logger = logging.getLogger(__name__)


class AuditedMCPTool(MCPStreamableHTTPTool):
    """
    Wrapper around MCPStreamableHTTPTool that adds full audit logging to JSON files.
    
    Tracks and logs:
    - Which tool was called
    - By which customer (customer_id)
    - In which conversation (thread_id)
    - What parameters were passed
    - What data was accessed
    - Duration and success/failure
    - Compliance flags (PCI_DSS, GDPR, etc.)
    """
    
    def __init__(
        self,
        name: str,
        url: str,
        customer_id: str | None = None,
        thread_id: str | None = None,
        mcp_server_name: str | None = None,
        **kwargs
    ):
        """
        Initialize audited MCP tool.
        
        Args:
            name: Tool name (e.g., "Account MCP Server")
            url: MCP server URL
            customer_id: Customer ID for audit tracking
            thread_id: Thread ID for audit tracking
            mcp_server_name: Friendly name (e.g., "account", "limits")
            **kwargs: Additional arguments passed to MCPStreamableHTTPTool
        """
        super().__init__(name=name, url=url, **kwargs)
        self.customer_id = customer_id
        self.thread_id = thread_id
        self.mcp_server_name = mcp_server_name or self._extract_server_name(url)
        
        print(f"\n[AUDIT INIT DEBUG] 🔧 Initializing AuditedMCPTool...")
        print(f"[AUDIT INIT DEBUG] Name: {name}")
        print(f"[AUDIT INIT DEBUG] Server: {self.mcp_server_name}")
        print(f"[AUDIT INIT DEBUG] Attempting to get audit logger...")
        
        try:
            self.audit_logger = get_audit_logger()
            print(f"[AUDIT INIT DEBUG] ✅ audit_logger created: {type(self.audit_logger)}")
            
            # Print all methods to see what agent framework might call
            print(f"[AUDIT INIT DEBUG] 📋 Available methods on this tool:")
            for attr in dir(self):
                if not attr.startswith('_') and callable(getattr(self, attr)):
                    print(f"[AUDIT INIT DEBUG]    - {attr}")
            
        except Exception as e:
            print(f"[AUDIT INIT DEBUG] ❌ FAILED to create audit_logger: {e}")
            print(f"[AUDIT INIT DEBUG] Traceback: {type(e).__name__}")
            raise
        
        logger.debug(
            f"[AUDIT] Created MCP tool with FULL audit logging: {name} "
            f"(server={self.mcp_server_name}, customer={customer_id}, thread={thread_id})"
        )
    
    def _extract_server_name(self, url: str) -> str:
        """Extract server name from URL for audit logging."""
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
        elif "8075" in url or "audit" in url.lower():
            return "audit"
        elif "8076" in url or "prodinfo" in url.lower():
            return "prodinfo_faq"
        elif "8077" in url or "coach" in url.lower():
            return "ai_money_coach"
        elif "8078" in url or "escalation" in url.lower():
            return "escalation_comms"
        else:
            return "unknown"
    
    def _get_operation_type(self, tool_name: str) -> str:
        """Determine operation type from tool name."""
        tool_lower = tool_name.lower()
        if "get" in tool_lower or "read" in tool_lower or "list" in tool_lower or "search" in tool_lower:
            return "read"
        elif "create" in tool_lower or "add" in tool_lower:
            return "create"
        elif "update" in tool_lower or "edit" in tool_lower or "modify" in tool_lower:
            return "update"
        elif "delete" in tool_lower or "remove" in tool_lower:
            return "delete"
        else:
            return "execute"
    
    def _get_compliance_flags(self, tool_name: str, arguments: dict, result: Any) -> list[str]:
        """Determine compliance flags based on operation."""
        flags = []
        tool_lower = tool_name.lower()
        
        # PCI-DSS: Payment card data
        if self.mcp_server_name in ["payment", "transaction"]:
            flags.append("PCI_DSS")
        
        # GDPR: Personal data
        if self.mcp_server_name in ["account", "contacts"]:
            flags.append("GDPR_PERSONAL_DATA")
        
        # High value transactions
        if "amount" in arguments:
            try:
                amount = float(arguments.get("amount", 0))
                if amount > 10000:
                    flags.append("HIGH_VALUE_TRANSACTION")
            except (ValueError, TypeError):
                pass
        
        return flags
    
    def _get_data_scope(self, tool_name: str) -> str:
        """Determine data scope from tool name."""
        if "account" in tool_name.lower() or "balance" in tool_name.lower():
            return "account_data"
        elif "transaction" in tool_name.lower():
            return "transaction_history"
        elif "payment" in tool_name.lower() or "transfer" in tool_name.lower():
            return "payment_data"
        elif "contact" in tool_name.lower() or "beneficiary" in tool_name.lower():
            return "contact_data"
        else:
            return "general"
    
    def _extract_data_accessed(self, tool_name: str, arguments: dict, result: Any) -> list[Any]:
        """Extract summary of data accessed."""
        data_summary = []
        
        # Add tool name
        data_summary.append(f"tool:{tool_name}")
        
        # Add key parameters
        for key in ["customer_id", "account_id", "transaction_id", "amount"]:
            if key in arguments:
                data_summary.append(f"{key}:{arguments[key]}")
        
        return data_summary
    
    async def call_tool(self, tool_name: str, **arguments) -> Any:
        """
        Override call_tool to add comprehensive audit logging to JSON files.
        
        This method wraps MCP tool invocations with full compliance audit logging.
        """
        print(f"\n{'='*80}")
        print(f"[AUDIT DEBUG] 🔍 call_tool() INVOKED!")
        print(f"[AUDIT DEBUG] Tool: {tool_name}")
        print(f"[AUDIT DEBUG] Server: {self.mcp_server_name}")
        print(f"[AUDIT DEBUG] Customer: {self.customer_id}")
        print(f"[AUDIT DEBUG] Thread: {self.thread_id}")
        print(f"[AUDIT DEBUG] audit_logger exists: {hasattr(self, 'audit_logger')}")
        if hasattr(self, 'audit_logger'):
            print(f"[AUDIT DEBUG] audit_logger type: {type(self.audit_logger)}")
        print(f"{'='*80}\n")
        
        start_time = time.perf_counter()
        operation_type = self._get_operation_type(tool_name)
        
        logger.info(
            f"[AUDIT] 🔧 MCP Tool Call: {tool_name} on {self.mcp_server_name.upper()} "
            f"(customer={self.customer_id}, thread={self.thread_id})"
        )
        
        # Use audit logger context manager to log to mcp_audit_YYYY-MM-DD.json
        with self.audit_logger.audit_operation(
            operation_type=operation_type,
            mcp_server=self.mcp_server_name,
            tool_name=tool_name,
            user_id=self.customer_id or "unknown",
            thread_id=self.thread_id,
            parameters=arguments
        ) as audit:
            try:
                # Call the actual MCP tool
                result = await super().call_tool(tool_name, **arguments)
                
                # Calculate duration
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                # Extract audit information
                data_accessed = self._extract_data_accessed(tool_name, arguments, result)
                data_scope = self._get_data_scope(tool_name)
                compliance_flags = self._get_compliance_flags(tool_name, arguments, result)
                
                # Set audit information (will be written to JSON)
                audit.set_data_accessed(data_accessed)
                audit.set_data_scope(data_scope)
                audit.set_result("success", f"Tool {tool_name} executed successfully")
                
                for flag in compliance_flags:
                    audit.add_compliance_flag(flag)
                
                logger.info(
                    f"[AUDIT] ✅ MCP Tool Success: {tool_name} "
                    f"({duration_ms:.2f}ms, flags={compliance_flags})"
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                
                logger.error(
                    f"[AUDIT] ❌ MCP Tool Error: {tool_name} failed after {duration_ms:.2f}ms: {e}"
                )
                
                audit.set_result("error", f"Tool {tool_name} failed: {str(e)}")
                raise
    
    async def __call__(self, tool_name: str, **arguments):
        """Alternative calling interface that might be used by agent framework."""
        print(f"\n{'='*80}")
        print(f"[AUDIT __call__ DEBUG] 🔍 __call__() INVOKED!")
        print(f"[AUDIT __call__ DEBUG] Tool: {tool_name}")
        print(f"[AUDIT __call__ DEBUG] Arguments: {list(arguments.keys())}")
        print(f"{'='*80}\n")
        return await self.call_tool(tool_name, **arguments)
    
    async def connect(self):
        """Connect to MCP server with audit logging."""
        logger.info(
            f"[AUDIT] 🔌 Connecting to {self.mcp_server_name.upper()} MCP server "
            f"(customer={self.customer_id}, thread={self.thread_id})"
        )
        
        try:
            result = await super().connect()
            logger.info(
                f"[AUDIT] ✅ Connected to {self.mcp_server_name.upper()} MCP server"
            )
            return result
        except Exception as e:
            logger.error(
                f"[AUDIT] ❌ Failed to connect to {self.mcp_server_name.upper()} MCP server: {e}"
            )
            raise
    
    def __repr__(self):
        return (
            f"AuditedMCPTool(name={self.name}, server={self.mcp_server_name}, "
            f"customer={self.customer_id}, thread={self.thread_id})"
        )


# For backward compatibility
__all__ = ["AuditedMCPTool"]
