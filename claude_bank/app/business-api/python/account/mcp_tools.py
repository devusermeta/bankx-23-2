from fastmcp import FastMCP
import logging
from typing import Annotated
from services import AccountService, UserService

logger = logging.getLogger(__name__)

# Initialize services with JSON StateManager
user_service = UserService()
account_service = AccountService()

mcp = FastMCP("Account MCP Server")

@mcp.tool(name="getAccountsByUserName", description="Get the list of all accounts for a specific user")
def get_accounts_by_user_name(userName: Annotated[str, "username of logged user"]):
    logger.info("getAccountsByUserName called with userName=%s", userName)
    return user_service.get_accounts_by_user_name(userName)

@mcp.tool(name="getAccountDetails", description="Get account details including balance and payment methods")
def get_account_details(accountId: Annotated[str, "Unique identifier for the user account"]):
    logger.info("Request to getAccountDetails with accountId: %s", accountId)
    account = account_service.get_account_details(accountId)
    
    if account is None:
        return {"error": "Account not found"}
    
    # Convert Pydantic model to dict to ensure proper JSON serialization
    result = account.model_dump()
    logger.info(f"Returning account details: {result}")
    return result


@mcp.tool(name="getPaymentMethodDetails", description="Get payment method detail with available balance")
def get_payment_method_details(paymentMethodId: Annotated[str, "Unique identifier for the payment method"]):
    logger.info("Request to getPaymentMethodDetails with paymentMethodId: %s", paymentMethodId)
    return account_service.get_payment_method_details(paymentMethodId)


# NOTE: The following beneficiary-related tools have been MOVED to Contacts Service (port 8074):
# - getRegisteredBeneficiary → getRegisteredBeneficiaries (Contacts Service)
# - verifyAccountNumber → verifyAccountNumber (Contacts Service)
# - addBeneficiary → addBeneficiary (Contacts Service)
#
# Agents should now use the Contacts MCP Server for beneficiary operations.
# The methods remain in AccountService for backward compatibility but are not exposed as MCP tools.
