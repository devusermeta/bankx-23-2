"""
Account MCP Server

Main entry point for the unified Account MCP Server.
Exposes account and limits tools via MCP protocol.
Compatible with Azure AI Foundry MCP integration.
"""

import logging
import json
from typing import Dict, Any
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from services import AccountService, LimitsService
from data_loader_service import DataLoaderService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress verbose logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger("account-mcp")

# Initialize FastAPI app for MCP JSON-RPC
app = FastAPI(title="Account MCP Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize data loader and services
data_loader = DataLoaderService()
account_service = AccountService(data_loader)
limits_service = LimitsService(data_loader)


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def get_accounts_by_username(email: str) -> Dict[str, Any]:
    """
    Get all accounts for a user by their email address.
    
    Args:
        email: User's email address
    
    Returns:
        Dictionary with success status and list of accounts or error message
    """
    logger.info(f"[MCP] get_accounts_by_username called: email={email}")
    
    try:
        accounts = account_service.get_accounts_by_user_name(email)
        
        if not accounts:
            result = {
                "success": False,
                "error": f"No accounts found for user: {email}",
                "accounts": []
            }
        else:
            result = {
                "success": True,
                "accounts": accounts,
                "count": len(accounts)
            }
        
        logger.info(f"[MCP] Found {len(accounts)} accounts for {email}")
        return result
    
    except Exception as e:
        logger.error(f"[MCP] Error in get_accounts_by_username: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "accounts": []
        }


def get_account_details(account_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific account.
    
    Args:
        account_id: Account identifier (e.g., CHK-001, SAV-001)
    
    Returns:
        Dictionary with success status and account details or error message
    """
    logger.info(f"[MCP] get_account_details called: account_id={account_id}")
    
    try:
        account = account_service.get_account_details(account_id)
        
        if not account:
            result = {
                "success": False,
                "error": f"Account not found: {account_id}"
            }
        else:
            result = {
                "success": True,
                **account.model_dump()  # Convert Pydantic model to dict
            }
        
        logger.info(f"[MCP] Account details retrieved for {account_id}")
        return result
    
    except Exception as e:
        logger.error(f"[MCP] Error in get_account_details: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def get_payment_method_details(payment_method_id: str) -> Dict[str, Any]:
    """
    Get details about a specific payment method.
    
    Args:
        payment_method_id: Payment method identifier (e.g., PM-CHK-001)
    
    Returns:
        Dictionary with success status and payment method details or error message
    """
    logger.info(f"[MCP] get_payment_method_details called: payment_method_id={payment_method_id}")
    
    try:
        payment_method = account_service.get_payment_method_details(payment_method_id)
        
        if not payment_method:
            result = {
                "success": False,
                "error": f"Payment method not found: {payment_method_id}"
            }
        else:
            result = {
                "success": True,
                **payment_method.model_dump()  # Convert Pydantic model to dict
            }
        
        logger.info(f"[MCP] Payment method details retrieved for {payment_method_id}")
        return result
    
    except Exception as e:
        logger.error(f"[MCP] Error in get_payment_method_details: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


def check_limits(account_id: str, transaction_amount: float, transaction_type: str = "transfer") -> Dict[str, Any]:
    """
    Check if a transaction is within account limits.
    
    Args:
        account_id: Account identifier
        transaction_amount: Amount to check in THB
        transaction_type: Type of transaction (transfer, payment, withdrawal)
    
    Returns:
        Dictionary with success status, whether transaction is allowed, and limit details
    """
    logger.info(f"[MCP] check_limits called: account_id={account_id}, amount={transaction_amount}, type={transaction_type}")
    
    try:
        result = limits_service.check_limits(account_id, transaction_amount, transaction_type)
        
        # Check if transaction is allowed (all three conditions must be true)
        allowed = result.sufficient_balance and result.within_per_txn_limit and result.within_daily_limit
        logger.info(f"[MCP] Limits check result for {account_id}: allowed={allowed}")
        
        # Return result with allowed flag added
        result_dict = result.model_dump()
        result_dict["allowed"] = allowed
        return {"success": True, **result_dict}
    
    except Exception as e:
        logger.error(f"[MCP] Error in check_limits: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "allowed": False
        }


def get_account_limits(account_id: str) -> Dict[str, Any]:
    """
    Get all limit information for an account.
    
    Args:
        account_id: Account identifier
    
    Returns:
        Dictionary with success status and all limit details or error message
    """
    logger.info(f"[MCP] get_account_limits called: account_id={account_id}")
    
    try:
        limits = limits_service.get_account_limits(account_id)
        
        if not limits:
            result = {
                "success": False,
                "error": f"No limits found for account: {account_id}"
            }
        else:
            result = {
                "success": True,
                **limits.model_dump()  # Convert Pydantic model to dict
            }
        
        logger.info(f"[MCP] Limits retrieved for {account_id}")
        return result
    
    except Exception as e:
        logger.error(f"[MCP] Error in get_account_limits: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# =============================================================================
# MCP JSON-RPC ENDPOINTS (Azure AI Foundry Compatible)
# =============================================================================

@app.post("/mcp")
@app.options("/mcp")
async def mcp_endpoint(request: Request):
    """MCP JSON-RPC endpoint compatible with Azure AI Foundry"""
    
    # Handle OPTIONS for CORS
    if request.method == "OPTIONS":
        return Response(status_code=204)
    
    try:
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")
        
        logger.info(f"📨 MCP Request: method={method}, id={request_id}")
        
        # Handle initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "account-mcp",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                },
                "id": request_id
            }
        
        # Handle tools/list
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "getAccountsByUserName",
                            "description": "Get all accounts for a user by their email address",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "email": {
                                        "type": "string",
                                        "description": "User's email address"
                                    }
                                },
                                "required": ["email"]
                            }
                        },
                        {
                            "name": "getAccountDetails",
                            "description": "Get detailed information about a specific account including balance, type, and payment methods",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "account_id": {
                                        "type": "string",
                                        "description": "Account identifier (e.g., CHK-001, SAV-001)"
                                    }
                                },
                                "required": ["account_id"]
                            }
                        },
                        {
                            "name": "getPaymentMethodDetails",
                            "description": "Get details about a specific payment method",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "payment_method_id": {
                                        "type": "string",
                                        "description": "Payment method identifier (e.g., PM-CHK-001)"
                                    }
                                },
                                "required": ["payment_method_id"]
                            }
                        },
                        {
                            "name": "checkLimits",
                            "description": "Check if a transaction is within account limits. Returns whether the transaction is allowed and provides detailed limit information.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "account_id": {
                                        "type": "string",
                                        "description": "Account identifier"
                                    },
                                    "transaction_amount": {
                                        "type": "number",
                                        "description": "Amount to check in THB"
                                    },
                                    "transaction_type": {
                                        "type": "string",
                                        "description": "Type of transaction: transfer, payment, or withdrawal",
                                        "enum": ["transfer", "payment", "withdrawal"],
                                        "default": "transfer"
                                    }
                                },
                                "required": ["account_id", "transaction_amount"]
                            }
                        },
                        {
                            "name": "getAccountLimits",
                            "description": "Get all limit information for an account including daily and per-transaction limits",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "account_id": {
                                        "type": "string",
                                        "description": "Account identifier"
                                    }
                                },
                                "required": ["account_id"]
                            }
                        }
                    ]
                },
                "id": request_id
            }
        
        # Handle tools/call
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            logger.info(f"🔧 Tool Call: {tool_name} with args={arguments}")
            
            # Route to appropriate tool
            if tool_name == "getAccountsByUserName":
                result = get_accounts_by_username(**arguments)
            elif tool_name == "getAccountDetails":
                result = get_account_details(**arguments)
            elif tool_name == "getPaymentMethodDetails":
                result = get_payment_method_details(**arguments)
            elif tool_name == "checkLimits":
                result = check_limits(**arguments)
            elif tool_name == "getAccountLimits":
                result = get_account_limits(**arguments)
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    },
                    "id": request_id
                }
            
            logger.info(f"✅ Tool result: {json.dumps(result)[:200]}...")
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                },
                "id": request_id
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }
    
    except Exception as e:
        logger.error(f"❌ Error handling MCP request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": body.get("id") if 'body' in locals() else None
        }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "account-mcp"}


if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("🚀 Starting Account MCP Server (Azure AI Foundry Compatible)")
    logger.info("=" * 80)
    logger.info("Server: http://localhost:8070")
    logger.info("MCP JSON-RPC Endpoint: http://localhost:8070/mcp")
    logger.info("Health Check: http://localhost:8070/health")
    logger.info("=" * 80)
    logger.info("Available Tools:")
    logger.info("  1. getAccountsByUserName - Get all accounts for a user")
    logger.info("  2. getAccountDetails - Get detailed account information")
    logger.info("  3. getPaymentMethodDetails - Get payment method details")
    logger.info("  4. checkLimits - Check if transaction is within limits")
    logger.info("  5. getAccountLimits - Get all account limits")
    logger.info("=" * 80)
    logger.info("Protocol: MCP JSON-RPC over HTTP (Azure AI Foundry compatible)")
    logger.info("=" * 80)
    
    # Run FastAPI server with Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070, log_level="info")
