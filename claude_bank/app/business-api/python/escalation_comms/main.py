"""
EscalationComms MCP Server - Ticket Management & Email Notifications

Port: 8078
Purpose: Manage support tickets and send email notifications via Azure Communication Services

Shared by:
- Escalation Agent (UC4) - for ticket management (get, create, update, close)
- ProdInfoFAQ Agent (UC2) - for ticket creation emails
- AIMoneyCoach Agent (UC3) - for ticket creation emails

Ticket Management Tools:
1. get_tickets - View customer's support tickets
2. create_ticket - Create new support ticket (with automatic email confirmation)
3. get_ticket_details - Get detailed ticket information including history
4. update_ticket - Update ticket status, priority, or add notes
5. close_ticket - Close a resolved ticket

Email Tools:
6. send_email - Send generic email
7. send_ticket_notification - Send formatted ticket notification
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP

from logging_config import setup_logging

# Load environment variables from .env file (check multiple locations)
# Priority: 1. Local .env, 2. Project root .env
local_env = Path(__file__).parent / ".env"
root_env = Path(__file__).parent.parent.parent.parent.parent / ".env"

if local_env.exists():
    load_dotenv(local_env)
elif root_env.exists():
    load_dotenv(root_env)
else:
    # Fallback: try to find .env in parent directories
    load_dotenv(dotenv_path=None, override=False)
from services import AzureCommunicationEmailService
from ticket_service import TicketService
from mcp_tools import register_tools

# Setup logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration from environment
PORT = int(os.getenv("PORT", "8078"))
HOST = os.getenv("HOST", "0.0.0.0")

# Azure Communication Services configuration
AZURE_COMMUNICATION_SERVICES_ENDPOINT = os.getenv("AZURE_COMMUNICATION_SERVICES_ENDPOINT")
AZURE_COMMUNICATION_SERVICES_EMAIL_FROM = os.getenv("AZURE_COMMUNICATION_SERVICES_EMAIL_FROM", "support@bankx.com")

# Initialize FastMCP server
mcp = FastMCP("EscalationComms MCP Server")

logger.info("=" * 80)
logger.info("EscalationComms MCP Server - Email Notifications")
logger.info("=" * 80)
logger.info(f"Port: {PORT}")
logger.info(f"Azure Communication Services: {AZURE_COMMUNICATION_SERVICES_ENDPOINT}")
logger.info(f"From Email: {AZURE_COMMUNICATION_SERVICES_EMAIL_FROM}")
logger.info("=" * 80)

# Validate required configuration
if not AZURE_COMMUNICATION_SERVICES_ENDPOINT:
    logger.warning("AZURE_COMMUNICATION_SERVICES_ENDPOINT not configured")
    logger.warning("Email functionality will be mocked for development")

# Initialize services
logger.info("Initializing email service...")

if AZURE_COMMUNICATION_SERVICES_ENDPOINT:
    email_service = AzureCommunicationEmailService(
        endpoint=AZURE_COMMUNICATION_SERVICES_ENDPOINT,
        from_email=AZURE_COMMUNICATION_SERVICES_EMAIL_FROM
    )
    logger.info("Azure Communication Services email client initialized")
else:
    # Mock service for development
    logger.warning("Using mock email service (emails will be logged, not sent)")
    email_service = None

# Initialize ticket service
logger.info("Initializing ticket service...")
ticket_service = TicketService()
logger.info(f"Ticket service initialized")

# Register MCP tools
logger.info("Registering MCP tools...")
register_tools(mcp=mcp, email_service=email_service, ticket_service=ticket_service)

logger.info("✅ EscalationComms MCP Server initialized successfully")
logger.info("=" * 80)

if __name__ == "__main__":
    logger.info(f"Starting EscalationComms MCP Server on {HOST}:{PORT}...")
    mcp.run(transport="http", host=HOST, port=PORT)
