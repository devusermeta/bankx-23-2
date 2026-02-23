"""
Audited MCP Tool Wrapper for Payment Agent v2 A2A Service

Wrapper around MCPStreamableHTTPTool that adds comprehensive audit logging
for compliance tracking (GDPR, PCI-DSS) when MCP tools are invoked.

Logs MCP tool invocations to: observability/mcp_audit_YYYY-MM-DD.json
"""

import logging
import os
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
            name: Tool name (e.g., "Payment Unified MCP Server")
            url: MCP server URL
            customer_id: Customer ID for audit tracking
            thread_id: Thread ID for audit tracking
            mcp_server_name: Friendly name (e.g., "payment-unified")
            **kwargs: Additional arguments passed to MCPStreamableHTTPTool
        """
        # CRITICAL FIX: Force use of external URLs for local development
        # Prevent agent framework from converting to .internal domains
        self._force_external_urls = os.getenv("FORCE_EXTERNAL_MCP_URLS", "true").lower() == "true"
        
        if self._force_external_urls and url and ".azurecontainerapps.io" in url and ".internal." not in url:
            # Store the original external URL and prevent framework auto-transformation
            self._original_external_url = url
            # Use the URL directly without allowing framework transformation
            print(f"[URL FIX] 🔧 Using external URL: {url}")
        else:
            self._original_external_url = url
            
        super().__init__(name=name, url=url, **kwargs)
        self.customer_id = customer_id
        self.thread_id = thread_id
        self.mcp_server_name = mcp_server_name or "payment-unified"
        
        logger.info(f"[AUDIT] Initializing AuditedMCPTool for {name}")
        
        try:
            self.audit_logger = get_audit_logger()
            logger.info(f"[AUDIT] ✅ Audit logger created for {self.mcp_server_name}")
        except Exception as e:
            logger.error(f"[AUDIT] ❌ Failed to create audit_logger: {e}")
            raise
        
        logger.debug(
            f"[AUDIT] Created MCP tool with FULL audit logging: {name} "
            f"(server={self.mcp_server_name}, customer={customer_id}, thread={thread_id})"
        )
    
    def _get_operation_type(self, tool_name: str) -> str:
        """Determine operation type from tool name."""
        tool_lower = tool_name.lower()
        if "get" in tool_lower or "read" in tool_lower or "list" in tool_lower:
            return "read"
        elif "check" in tool_lower or "validate" in tool_lower:
            return "validate"
        elif "execute" in tool_lower or "transfer" in tool_lower:
            return "execute"
        else:
            return "operation"
    
    def _get_compliance_flags(self, tool_name: str, arguments: dict, result: Any) -> list[str]:
        """Determine compliance flags based on operation."""
        flags = ["PCI_DSS"]  # All payment operations
        
        # GDPR: Personal data
        if "account" in tool_name.lower() or "beneficiary" in tool_name.lower():
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
        if "account" in tool_name.lower():
            return "account_data"
        elif "beneficiary" in tool_name.lower():
            return "contact_data"
        elif "transfer" in tool_name.lower() or "execute" in tool_name.lower():
            return "payment_data"
        else:
            return "general"
    
    def _extract_data_accessed(self, tool_name: str, arguments: dict, result: Any) -> list[Any]:
        """Extract summary of data accessed."""
        data_summary = [f"tool:{tool_name}"]
        
        # Add key parameters
        for key in ["customer_id", "account_id", "sender_account_id", "recipient_account_id", "amount"]:
            if key in arguments:
                data_summary.append(f"{key}:{arguments[key]}")
        
        return data_summary
    
    async def call_tool(self, tool_name: str, **arguments) -> Any:
        """
        Override call_tool to add comprehensive audit logging to JSON files.
        
        This method wraps MCP tool invocations with full compliance audit logging.
        """
        logger.info(
            f"[AUDIT] 🔧 MCP Tool Call: {tool_name} on {self.mcp_server_name.upper()} "
            f"(customer={self.customer_id}, thread={self.thread_id}, args={list(arguments.keys())})"
        )
        
        start_time = time.perf_counter()
        operation_type = self._get_operation_type(tool_name)
        
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
        """Connect to MCP server with audit logging and URL fix."""
        logger.info(
            f"[AUDIT] 🔌 Connecting to {self.mcp_server_name.upper()} MCP server "
            f"(customer={self.customer_id}, thread={self.thread_id})"
        )
        
        # CRITICAL FIX: Restore external URL before connection
        if self._force_external_urls and hasattr(self, '_original_external_url'):
            original_url = getattr(self, '_original_external_url')
            current_url = getattr(self, 'url', None) or getattr(self, '_url', None)
            
            # Check if framework has transformed URL to .internal
            if (current_url and ".internal." in current_url and 
                original_url and ".internal." not in original_url):
                
                logger.warning(f"[URL FIX] Framework transformed URL - restoring external URL")
                
                # Force external URL
                if hasattr(self, 'url'):
                    self.url = original_url
                if hasattr(self, '_url'):
                    self._url = original_url
        
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


__all__ = ["AuditedMCPTool"]
