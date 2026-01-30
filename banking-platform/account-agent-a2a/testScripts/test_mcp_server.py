"""
MCP Server Test Script

Tests all 5 tools exposed by the Account MCP Server.
Run this AFTER starting the MCP server on port 8070.

Usage:
    1. Start MCP server: cd mcp-server && python main.py
    2. Run tests: python test_mcp_server.py
"""

import json
import requests
from typing import Dict, Any


# MCP Server Configuration  
# Using JSON-RPC over HTTP (same as financial-calculator)
MCP_SERVER_URL = "http://localhost:8070/mcp"
HEADERS = {"Content-Type": "application/json"}


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.RESET}")
    print("=" * 80)


def print_test(test_name: str):
    """Print test name"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}TEST: {test_name}{Colors.RESET}")
    print("-" * 80)


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_result(result: Any):
    """Print JSON result"""
    print(f"\n{Colors.YELLOW}Result:{Colors.RESET}")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call an MCP tool using JSON-RPC format (same as financial-calculator)
    
    Args:
        tool_name: Name of the tool to call
        arguments: Tool arguments as dictionary
    
    Returns:
        Tool result or error
    """
    # JSON-RPC 2.0 format for tools/call
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    try:
        response = requests.post(MCP_SERVER_URL, json=rpc_payload, headers=HEADERS, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        # Check for JSON-RPC error
        if "error" in result:
            return {"error": f"MCP Error: {result['error']}"}
        
        # Extract result from JSON-RPC response
        # The result contains a "content" array with text (JSON string)
        if "result" in result and "content" in result["result"]:
            content_text = result["result"]["content"][0]["text"]
            return json.loads(content_text)
        
        return result.get("result", result)
    
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to MCP server. Is it running on port 8070?"}
    except requests.exceptions.Timeout:
        return {"error": "Request timeout. Server not responding."}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def test_server_connection():
    """Test if MCP server is reachable"""
    print_test("Server Connection")
    
    # Test server with simple tool call
    try:
        print(f"{Colors.CYAN}Testing connection to {MCP_SERVER_URL}{Colors.RESET}")
        
        # Try a simple tool call as a connection test
        result = call_mcp_tool("getAccountLimits", {"account_id": "CHK-001"})
        
        if "error" in result:
            if "Cannot connect" in result["error"]:
                print_error("Cannot connect to MCP server on port 8070")
                print(f"{Colors.YELLOW}Make sure to start the server first:{Colors.RESET}")
                print("  cd account-agent-a2a/mcp-server")
                print("  python main.py")
                return False
            else:
                # Server responded but with an error - that's still a connection
                print_success("MCP server is running on port 8070")
                print(f"{Colors.YELLOW}Note: Test call returned error (expected): {result['error']}{Colors.RESET}")
                return True
        else:
            print_success("MCP server is running and responding on port 8070")
            return True
            
    except Exception as e:
        print_error(f"Connection test failed: {str(e)}")
        return False


def test_get_accounts_by_username():
    """Test getAccountsByUserName tool"""
    print_test("getAccountsByUserName")
    
    # Test with valid email
    print(f"\n{Colors.CYAN}Calling with email: somchai.rattanakorn@example.com{Colors.RESET}")
    result = call_mcp_tool("getAccountsByUserName", {
        "email": "somchai.rattanakorn@example.com"
    })
    
    if "error" in result:
        print_error(f"Failed: {result['error']}")
        return False
    
    if result.get("success") and isinstance(result.get("accounts"), list) and len(result["accounts"]) > 0:
        print_success(f"Found {result['count']} account(s)")
        print_result(result)
        return True
    else:
        print_error("No accounts found or unexpected result")
        print_result(result)
        return False


def test_get_account_details():
    """Test getAccountDetails tool"""
    print_test("getAccountDetails")
    
    # Test with valid account ID
    print(f"\n{Colors.CYAN}Calling with account ID: CHK-001{Colors.RESET}")
    result = call_mcp_tool("getAccountDetails", {
        "account_id": "CHK-001"
    })
    
    if "error" in result:
        print_error(f"Failed: {result['error']}")
        return False
    
    if "id" in result and "balance" in result:
        print_success(f"Account: {result['id']}, Balance: {result['balance']} {result.get('currency', 'THB')}")
        print_result(result)
        return True
    else:
        print_error("Invalid account details format")
        print_result(result)
        return False


def test_get_payment_method_details():
    """Test getPaymentMethodDetails tool"""
    print_test("getPaymentMethodDetails")
    
    # Test with valid payment method ID
    print(f"\n{Colors.CYAN}Calling with payment method ID: PM-CHK-001{Colors.RESET}")
    result = call_mcp_tool("getPaymentMethodDetails", {
        "payment_method_id": "PM-CHK-001"
    })
    
    if "error" in result:
        print_error(f"Failed: {result['error']}")
        return False
    
    if "id" in result and "availableBalance" in result:
        print_success(f"Payment Method: {result['id']}, Available: {result['availableBalance']}")
        print_result(result)
        return True
    else:
        print_error("Invalid payment method format")
        print_result(result)
        return False


def test_check_limits():
    """Test checkLimits tool"""
    print_test("checkLimits")
    
    # Test with valid transaction
    print(f"\n{Colors.CYAN}Checking limits for 30,000 THB transaction on CHK-001{Colors.RESET}")
    result = call_mcp_tool("checkLimits", {
        "account_id": "CHK-001",
        "transaction_amount": 30000.0,
        "transaction_type": "transfer"
    })
    
    if "error" in result:
        print_error(f"Failed: {result['error']}")
        return False
    
    if "sufficient_balance" in result:
        balance_ok = result["sufficient_balance"]
        per_txn_ok = result.get("within_per_txn_limit", False)
        daily_ok = result.get("within_daily_limit", False)
        
        status = "✓ PASS" if (balance_ok and per_txn_ok and daily_ok) else "✗ FAIL"
        print(f"\n{Colors.BOLD}Validation Result: {status}{Colors.RESET}")
        print(f"  Balance: {'✓' if balance_ok else '✗'} {result.get('current_balance', 0)} THB")
        print(f"  Per-Transaction Limit: {'✓' if per_txn_ok else '✗'}")
        print(f"  Daily Limit: {'✓' if daily_ok else '✗'}")
        
        if not (balance_ok and per_txn_ok and daily_ok):
            print(f"\n{Colors.RED}Error: {result.get('error_message', 'Unknown error')}{Colors.RESET}")
        
        print_result(result)
        return True
    else:
        print_error("Invalid limits check format")
        print_result(result)
        return False


def test_get_account_limits():
    """Test getAccountLimits tool"""
    print_test("getAccountLimits")
    
    # Test with valid account
    print(f"\n{Colors.CYAN}Getting limits for account: CHK-001{Colors.RESET}")
    result = call_mcp_tool("getAccountLimits", {
        "account_id": "CHK-001"
    })
    
    if "error" in result:
        print_error(f"Failed: {result['error']}")
        return False
    
    if "daily_limit" in result:
        print_success("Limits retrieved successfully")
        print(f"\n{Colors.BOLD}Limit Summary:{Colors.RESET}")
        print(f"  Per-Transaction: {result.get('per_transaction_limit', 0):,.0f} {result.get('currency', 'THB')}")
        print(f"  Daily Limit: {result.get('daily_limit', 0):,.0f} {result.get('currency', 'THB')}")
        print(f"  Remaining Today: {result.get('remaining_today', 0):,.0f} {result.get('currency', 'THB')}")
        print(f"  Daily Used: {result.get('daily_used', 0):,.0f} {result.get('currency', 'THB')}")
        print(f"  Utilization: {result.get('utilization_percent', 0):.1f}%")
        
        print_result(result)
        return True
    else:
        print_error("Invalid limits format")
        print_result(result)
        return False


def run_all_tests():
    """Run all MCP server tests"""
    print_header("MCP Server Test Suite")
    print(f"Testing server at: {MCP_SERVER_URL}")
    
    # Test connection first
    if not test_server_connection():
        print_error("\nCannot proceed - MCP server is not running!")
        return
    
    # Run all tool tests
    tests = [
        ("Get Accounts by Username", test_get_accounts_by_username),
        ("Get Account Details", test_get_account_details),
        ("Get Payment Method Details", test_get_payment_method_details),
        ("Check Limits", test_check_limits),
        ("Get Account Limits", test_get_account_limits),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if success else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"{status}  {test_name}")
    
    print("\n" + "=" * 80)
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED ({passed}/{total}){Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ SOME TESTS FAILED ({passed}/{total} passed){Colors.RESET}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Fatal error: {str(e)}{Colors.RESET}")
