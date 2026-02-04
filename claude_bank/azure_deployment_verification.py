#!/usr/bin/env python3
"""
Azure Deployment Verification Script
Checks agent IDs, MCP endpoints, and routing configuration
Run this in the deployed Azure Container App to diagnose issues
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

# Load .env
env_file = Path(__file__).parent / "app" / "copilot" / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)
    print(f"{CYAN}✅ Loaded .env from: {env_file}{RESET}\n")
else:
    print(f"{YELLOW}⚠️  .env file not found at: {env_file}{RESET}")
    print(f"{YELLOW}Using environment variables only{RESET}\n")

print(f"\n{BLUE}{'='*100}{RESET}")
print(f"{BLUE}AZURE DEPLOYMENT VERIFICATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
print(f"{BLUE}{'='*100}{RESET}\n")

# ============================================================================
# 1. CHECK ENVIRONMENT VARIABLES
# ============================================================================
print(f"\n{CYAN}1. ENVIRONMENT VARIABLES & AGENT IDs{RESET}")
print(f"{CYAN}{'-'*100}{RESET}")

required_vars = {
    "FOUNDRY_PROJECT_ENDPOINT": "Azure AI Foundry endpoint",
    "FOUNDRY_MODEL_DEPLOYMENT_NAME": "Model deployment name",
    "ACCOUNT_MCP_URL": "Account MCP server",
    "TRANSACTION_MCP_URL": "Transaction MCP server",
    "PAYMENT_MCP_URL": "Payment MCP server",
    "LIMITS_MCP_URL": "Limits MCP server",
    "CONTACTS_MCP_URL": "Contacts MCP server",
    "ESCALATION_COMMS_MCP_URL": "Escalation/Comms MCP server",
}

agent_id_vars = {
    "SUPERVISOR_AGENT_ID": "Supervisor Agent",
    "ACCOUNT_AGENT_ID": "Account Agent",
    "TRANSACTION_AGENT_ID": "Transaction Agent",
    "PAYMENT_AGENT_ID": "Payment Agent",
    "PRODINFO_FAQ_AGENT_ID": "ProdInfo FAQ Agent (UC2)",
    "AI_MONEY_COACH_AGENT_ID": "AI Money Coach Agent (UC3)",
    "ESCALATION_COMMS_AGENT_ID": "Escalation Comms Agent",
}

knowledge_base_vars = {
    "PRODINFO_FAQ_VECTOR_STORE_IDS": "ProdInfo FAQ Vector Store IDs",
    "AI_MONEY_COACH_VECTOR_STORE_IDS": "AI Money Coach Vector Store IDs",
}

print(f"\n{YELLOW}📋 REQUIRED ENVIRONMENT VARIABLES:{RESET}")
all_required_set = True
for var_name, description in required_vars.items():
    value = os.getenv(var_name)
    if value:
        # Truncate long values for display
        display_val = value if len(value) < 50 else value[:47] + "..."
        print(f"  {GREEN}✅{RESET} {var_name:35} = {display_val}")
    else:
        print(f"  {RED}❌{RESET} {var_name:35} = {RED}NOT SET{RESET}")
        all_required_set = False

print(f"\n{YELLOW}🆔 AGENT IDs (Required in Docker mode):{RESET}")
all_agent_ids_set = True
for var_name, description in agent_id_vars.items():
    value = os.getenv(var_name)
    if value:
        print(f"  {GREEN}✅{RESET} {description:35} = {value}")
    else:
        print(f"  {YELLOW}⚠️ {RESET} {description:35} = {YELLOW}NOT SET{RESET}")
        all_agent_ids_set = False

print(f"\n{YELLOW}📚 KNOWLEDGE BASE VECTOR STORE IDs (For UC2/UC3):{RESET}")
for var_name, description in knowledge_base_vars.items():
    value = os.getenv(var_name)
    if value:
        ids = value.split(",")
        print(f"  {GREEN}✅{RESET} {description:35} = {len(ids)} store(s)")
        for idx, store_id in enumerate(ids, 1):
            store_id = store_id.strip()
            print(f"       [{idx}] {store_id[:60]}{'...' if len(store_id) > 60 else ''}")
    else:
        print(f"  {YELLOW}⚠️ {RESET} {description:35} = {YELLOW}NOT SET{RESET}")

# ============================================================================
# 2. CHECK DOCKER/CONTAINER MODE
# ============================================================================
print(f"\n{CYAN}2. DEPLOYMENT MODE{RESET}")
print(f"{CYAN}{'-'*100}{RESET}")

is_docker = os.path.exists("/.dockerenv")
use_prebuilt_only = os.getenv('USE_PREBUILT_AGENTS_ONLY', 'false').lower() == 'true'

print(f"  Running in Docker container:     {GREEN if is_docker else RED}{'YES' if is_docker else 'NO'}{RESET}")
print(f"  USE_PREBUILT_AGENTS_ONLY:        {GREEN if use_prebuilt_only else YELLOW}{'TRUE' if use_prebuilt_only else 'FALSE (local dev mode)'}{RESET}")

if is_docker:
    print(f"\n  {GREEN}✅ Container detected (/.dockerenv exists){RESET}")
    if use_prebuilt_only:
        print(f"  {GREEN}✅ Docker mode: Using pre-configured agents{RESET}")
        if not all_agent_ids_set:
            print(f"  {RED}❌ ERROR: Docker mode enabled but not all agent IDs are set!{RESET}")
    else:
        print(f"  {YELLOW}⚠️  Docker mode: Agent creation mode enabled (may fail){RESET}")
else:
    print(f"\n  {YELLOW}⚠️  Local development environment detected{RESET}")
    print(f"  Agents will be created on-demand if IDs are not provided")

# ============================================================================
# 3. VERIFY MCP ENDPOINT ACCESSIBILITY
# ============================================================================
print(f"\n{CYAN}3. MCP ENDPOINT CONNECTIVITY{RESET}")
print(f"{CYAN}{'-'*100}{RESET}")

mcp_endpoints = {
    "ACCOUNT_MCP_URL": "Account MCP",
    "TRANSACTION_MCP_URL": "Transaction MCP",
    "PAYMENT_MCP_URL": "Payment MCP",
    "LIMITS_MCP_URL": "Limits MCP",
    "CONTACTS_MCP_URL": "Contacts MCP",
    "ESCALATION_COMMS_MCP_URL": "Escalation/Comms MCP",
}

async def check_mcp_connectivity():
    """Check if MCP endpoints are reachable"""
    import aiohttp
    
    results = {}
    async with aiohttp.ClientSession() as session:
        for env_var, label in mcp_endpoints.items():
            url = os.getenv(env_var)
            if not url:
                results[label] = ("NOT SET", None)
                continue
            
            try:
                # Try to reach the /mcp endpoint
                mcp_url = f"{url}/mcp" if not url.endswith("/mcp") else url
                async with session.get(mcp_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        results[label] = ("REACHABLE", 200)
                    else:
                        results[label] = ("REACHABLE", resp.status)
            except aiohttp.ClientConnectorError as e:
                results[label] = ("UNREACHABLE", str(e)[:50])
            except Exception as e:
                results[label] = ("ERROR", str(e)[:50])
    
    return results

try:
    mcp_results = asyncio.run(check_mcp_connectivity())
    
    for label, (status, detail) in mcp_results.items():
        url = os.getenv([k for k, v in mcp_endpoints.items() if v == label][0]) if label != "NOT SET" else None
        
        if status == "NOT SET":
            print(f"  {YELLOW}⚠️ {label:30} = NOT SET{RESET}")
        elif status == "REACHABLE" and detail == 200:
            print(f"  {GREEN}✅{RESET} {label:30} = REACHABLE (HTTP {detail})")
        elif status == "REACHABLE":
            print(f"  {YELLOW}⚠️ {label:30} = REACHABLE but HTTP {detail}{RESET}")
        else:
            print(f"  {RED}❌{RESET} {label:30} = {status} ({detail})")
except Exception as e:
    print(f"  {RED}❌ Failed to check MCP connectivity: {e}{RESET}")

# ============================================================================
# 4. ROUTING STRATEGY VERIFICATION
# ============================================================================
print(f"\n{CYAN}4. ROUTING STRATEGY VERIFICATION{RESET}")
print(f"{CYAN}{'-'*100}{RESET}")

print(f"\n{YELLOW}UC1 - Financial Operations (Account, Transaction, Payment, Limits, Contacts):{RESET}")
print(f"  Strategy: {GREEN}Cache FIRST → MCP Server FALLBACK{RESET}")
print(f"  {YELLOW}Required for routing:{RESET}")
print(f"    - Cache Manager initialized")
print(f"    - MCP servers accessible:")
print(f"      ✓ Account MCP (balance, account details)")
print(f"      ✓ Transaction MCP (last 5 transactions)")
print(f"      ✓ Payment MCP (payment initiation)")
print(f"      ✓ Limits MCP (transaction limits)")
print(f"      ✓ Contacts MCP (beneficiaries)")

print(f"\n{YELLOW}UC2 - Product Information & FAQ:{RESET}")
print(f"  Strategy: {GREEN}Direct Azure AI Foundry Agent (with Vector Store){RESET}")
print(f"  {YELLOW}Required for routing:{RESET}")
print(f"    - Agent ID: {os.getenv('PRODINFO_FAQ_AGENT_ID', 'NOT SET')}")
print(f"    - Vector Store IDs: {os.getenv('PRODINFO_FAQ_VECTOR_STORE_IDS', 'NOT SET').split(',')[0] if os.getenv('PRODINFO_FAQ_VECTOR_STORE_IDS') else 'NOT SET'}")

print(f"\n{YELLOW}UC3 - Personal Finance Coaching:{RESET}")
print(f"  Strategy: {GREEN}Direct Azure AI Foundry Agent (with Vector Store){RESET}")
print(f"  {YELLOW}Required for routing:{RESET}")
print(f"    - Agent ID: {os.getenv('AI_MONEY_COACH_AGENT_ID', 'NOT SET')}")
print(f"    - Vector Store IDs: {os.getenv('AI_MONEY_COACH_VECTOR_STORE_IDS', 'NOT SET').split(',')[0] if os.getenv('AI_MONEY_COACH_VECTOR_STORE_IDS') else 'NOT SET'}")

# ============================================================================
# 5. SUMMARY & RECOMMENDATIONS
# ============================================================================
print(f"\n{CYAN}5. DEPLOYMENT READINESS SUMMARY{RESET}")
print(f"{CYAN}{'-'*100}{RESET}")

issues = []

if not all_required_set:
    issues.append("Some required environment variables are not set")

if is_docker and not all_agent_ids_set:
    issues.append("Running in Docker but not all agent IDs are configured")

if not os.getenv('PRODINFO_FAQ_AGENT_ID'):
    issues.append("PRODINFO_FAQ_AGENT_ID not set (UC2 routing will fail)")

if not os.getenv('AI_MONEY_COACH_AGENT_ID'):
    issues.append("AI_MONEY_COACH_AGENT_ID not set (UC3 routing will fail)")

if not os.getenv('PRODINFO_FAQ_VECTOR_STORE_IDS'):
    issues.append("PRODINFO_FAQ_VECTOR_STORE_IDS not set (UC2 agent cannot access knowledge base)")

if not os.getenv('AI_MONEY_COACH_VECTOR_STORE_IDS'):
    issues.append("AI_MONEY_COACH_VECTOR_STORE_IDS not set (UC3 agent cannot access knowledge base)")

if issues:
    print(f"\n{RED}❌ ISSUES FOUND:{RESET}")
    for idx, issue in enumerate(issues, 1):
        print(f"  {idx}. {RED}{issue}{RESET}")
    
    print(f"\n{YELLOW}RECOMMENDATIONS:{RESET}")
    print(f"  1. Set all agent IDs in the Container App environment variables:")
    print(f"     SUPERVISOR_AGENT_ID, ACCOUNT_AGENT_ID, TRANSACTION_AGENT_ID,")
    print(f"     PAYMENT_AGENT_ID, PRODINFO_FAQ_AGENT_ID, AI_MONEY_COACH_AGENT_ID,")
    print(f"     ESCALATION_COMMS_AGENT_ID")
    print(f"  2. Configure vector store IDs:")
    print(f"     PRODINFO_FAQ_VECTOR_STORE_IDS, AI_MONEY_COACH_VECTOR_STORE_IDS")
    print(f"  3. Verify MCP endpoints are accessible from the container")
    print(f"  4. Set USE_PREBUILT_AGENTS_ONLY=true in Docker mode")
else:
    print(f"\n{GREEN}✅ NO ISSUES FOUND - DEPLOYMENT READY{RESET}")

# ============================================================================
# 6. NEXT STEPS
# ============================================================================
print(f"\n{CYAN}6. NEXT STEPS{RESET}")
print(f"{CYAN}{'-'*100}{RESET}")

print(f"\n  {YELLOW}To verify routing is working:{RESET}")
print(f"    1. Check copilot container logs for 'route_to_*_agent' calls")
print(f"    2. Look for '[DEBUG] Created pending_routing_events' in logs")
print(f"    3. Verify MCP tool calls are being made (getAccountsByUserName, etc.)")
print(f"    4. Check /api/dashboard endpoints for conversations and decisions")

print(f"\n  {YELLOW}To collect container logs:{RESET}")
print(f"    az containerapp logs show --name <app-name> --resource-group <rg>")
print(f"    Or tail logs in Azure Portal → Container App → Logs")

print(f"\n{BLUE}{'='*100}{RESET}\n")
