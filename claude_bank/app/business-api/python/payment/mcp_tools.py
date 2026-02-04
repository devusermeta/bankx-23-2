from fastmcp import FastMCP
import logging
from typing import Optional, Annotated
from services import PaymentService
from models import Payment

logger = logging.getLogger(__name__)

# Initialize payment service (now uses StateManager internally)
payment_service = PaymentService(
    transaction_api_url="http://localhost:8071"  # Local transaction service
)

mcp = FastMCP("Payment MCP Server")


@mcp.tool(name="processPayment", description="Submit a payment request")
def process_payment(
    account_id: Annotated[str, "Unique identifier for the account making the payment"],
    amount: Annotated[float, "Payment amount in the account's currency"],
    description: Annotated[str, "Description or purpose of the payment"],
    payment_method_id: Annotated[str, "Identifier for the payment method to use"],
    timestamp: Annotated[str, "ISO timestamp when the payment was initiated"],
    recipient_name: Annotated[Optional[str], "Name of the payment recipient"] = None,
    recipient_bank_code: Annotated[Optional[str], "Bank code or routing number for the recipient"] = None,
    payment_type: Annotated[Optional[str], "Type of payment (e.g., transfer, bill_pay, etc.)"] = None
):
    logger.info(
        "processPayment called with account_id=%s, amount=%s, description=%s, payment_method_id=%s, recipient_name=%s, recipient_bank_code=%s",
        account_id, amount, description, payment_method_id, recipient_name, recipient_bank_code
    )

    # Create Payment object from individual parameters
    payment_obj = Payment(
        accountId=account_id,
        amount=amount,
        description=description,
        recipientName=recipient_name,
        recipientBankCode=recipient_bank_code,
        paymentMethodId=payment_method_id,
        paymentType=payment_type,
        timestamp=timestamp
    )

    try:
        payment_service.process_payment(payment_obj)
        logger.info("processPayment completed successfully for account_id=%s, amount=%s", account_id, amount)
        return {"status": "ok"}
    except Exception as e:
        logger.exception("Error while processing payment: %s", e)
        # Return structured error so calling agent can display a clear message
        return {"status": "error", "message": str(e)}
