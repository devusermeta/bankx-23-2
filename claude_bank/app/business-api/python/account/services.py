from typing import List, Optional
from models import Account, PaymentMethod, PaymentMethodSummary, Beneficiary
from beneficiary_service import beneficiary_service
import logging
import sys
from pathlib import Path

# Add common directory to path for StateManager
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "common"))
from state_manager import get_state_manager

logger = logging.getLogger(__name__)


class AccountService:
    """
    Account Service - Handles account operations using JSON-based state management.
    
    Now integrates with:
    - StateManager: Provides account and customer data from JSON (with CSV fallback)
    - BeneficiaryService: Manages beneficiary/payee relationships
    
    All data is read from dynamic_data/*.json files which are automatically
    updated on transfers and persist across restarts.
    """
    
    def __init__(self):
        # Initialize state manager (JSON-based storage)
        self.state_manager = get_state_manager()
        logger.info("AccountService initialized with JSON StateManager")
        
        # Note: Old dummy accounts (1000, 1010, 1020) are replaced with
        # real accounts from CSV (CUST-001 to CUST-010)

    def get_account_details(self, account_id: str) -> Optional[Account]:
        """
        Get account details by account ID (e.g., "CHK-001").
        
        CHANGED: Now uses StateManager for JSON-based storage with auto-updates.
        """
        logger.info("Request to get_account_details with account_id: %s", account_id)
        if not account_id:
            raise ValueError("AccountId is empty or null")
        
        # Get account from JSON
        account_data = self.state_manager.get_account_by_id(account_id)
        if not account_data:
            logger.warning(f"Account not found: {account_id}")
            return None
        
        # Get customer details
        customers = self.state_manager.get_customers()
        customer = None
        for cust in customers:
            if cust['customer_id'] == account_data['customer_id']:
                customer = cust
                break
        
        if not customer:
            logger.warning(f"Customer not found for account: {account_id}")
            return None
        
        # Balance is already current from JSON (updated on each transfer)
        current_balance = account_data['ledger_balance']
        
        # Map JSON data to Account model
        return Account(
            id=account_data['account_id'],
            userName=customer['email'],  # Use email as userName
            accountHolderFullName=customer['full_name'],
            currency=account_data['currency'],
            activationDate="2025-09-01",
            balance=str(current_balance),  # Current balance from JSON
            paymentMethods=[
                # Default to bank transfer for Thai accounts
                PaymentMethodSummary(
                    id=f"PM-{account_data['account_id']}",
                    type="BankTransfer",
                    activationDate="2025-09-01",
                    expirationDate="9999-12-31"
                )
            ]
        )

    def get_payment_method_details(self, payment_method_id: str) -> Optional[PaymentMethod]:
        """
        Get payment method details.
        
        For Thai banking scenario, we primarily use BankTransfer.
        """
        logger.info("Request to get_payment_method_details with payment_method_id: %s", payment_method_id)
        if not payment_method_id:
            raise ValueError("PaymentMethodId is empty or null")
        
        # Extract account_id from payment method ID (format: PM-CHK-001)
        if payment_method_id.startswith("PM-"):
            account_id = payment_method_id[3:]  # Remove "PM-" prefix
            account_data = self.state_manager.get_account_by_id(account_id)
            
            if account_data:
                return PaymentMethod(
                    id=payment_method_id,
                    type="BankTransfer",
                    activationDate="2025-09-01",
                    expirationDate="9999-12-31",
                    availableBalance=str(account_data['available_balance']),
                    cardNumber=None  # Bank transfer doesn't have card number
                )
        
        logger.warning(f"Payment method not found: {payment_method_id}")
        return None

    def get_registered_beneficiary(self, account_id: str) -> List[Beneficiary]:
        """
        Get list of registered beneficiaries for an account.
        
        CHANGED: Now uses BeneficiaryService which loads from:
        - JSON contacts.json (pre-existing beneficiaries)
        - JSON beneficiary_mappings.json (runtime additions)
        
        This is called by PaymentAgent to check if recipient is already registered.
        """
        logger.info("Request to get_registered_beneficiary with account_id: %s", account_id)
        if not account_id:
            raise ValueError("AccountId is empty or null")
        
        # Get account data to find customer_id
        account_data = self.state_manager.get_account_by_id(account_id)
        if not account_data:
            logger.warning(f"Account not found: {account_id}")
            return []
        
        customer_id = account_data['customer_id']
        
        # Get beneficiaries from service
        beneficiaries_data = beneficiary_service.get_beneficiaries(customer_id)
        
        # Convert to Beneficiary model
        beneficiaries = []
        for i, ben_data in enumerate(beneficiaries_data):
            beneficiaries.append(
                Beneficiary(
                    id=str(i + 1),
                    fullName=ben_data.get('name', 'Unknown'),
                    bankCode=ben_data.get('account_number', ''),
                    bankName=ben_data.get('alias', '')  # Using alias as display name
                )
            )
        
        logger.info(f"Found {len(beneficiaries)} beneficiaries for customer {customer_id}")
        return beneficiaries
    
    
    def verify_account_number(self, account_number: str) -> dict:
        """
        Verify if an account number exists in the system.
        
        NEW FUNCTION - Key for payment flow with unregistered beneficiaries.
        
        When user wants to pay someone not in their beneficiary list:
        1. Agent asks for account number
        2. This function verifies it exists
        3. If valid, returns account holder name for confirmation
        4. If invalid, agent retry logic kicks in (max 3 attempts)
        
        Args:
            account_number: Account number to verify (e.g., "123-456-003")
        
        Returns:
            Dict with:
            - valid: bool (True if account exists)
            - account_number: str (the account number)
            - account_holder_name: str (if valid)
            - message: str (for invalid cases)
        """
        logger.info(f"Verifying account number: {account_number}")
        
        # Get all accounts and find by account_no
        accounts = self.state_manager.get_accounts()
        account = None
        for acc in accounts:
            if acc['account_no'] == account_number:
                account = acc
                break
        
        if account:
            holder_name = account['cust_name']
            
            return {
                'valid': True,
                'account_number': account_number,
                'account_holder_name': holder_name,
                'message': f'Account verified. Holder: {holder_name}'
            }
        else:
            return {
                'valid': False,
                'account_number': account_number,
                'message': 'Invalid account number. Please check and try again.'
            }
    
    
    def add_beneficiary(self, account_id: str, beneficiary_account_number: str, 
                       beneficiary_name: str, alias: str = None) -> dict:
        """
        Add a new beneficiary after successful payment.
        
        NEW FUNCTION - Called when user confirms they want to save recipient as beneficiary.
        
        Flow:
        1. Payment successful to unregistered account
        2. Agent asks: "Would you like to save this recipient for future payments?"
        3. If yes, agent calls this function
        4. Beneficiary saved to JSON for future use
        
        Args:
            account_id: Sender's account ID
            beneficiary_account_number: Recipient's account number
            beneficiary_name: Recipient's name
            alias: Optional friendly name (e.g., "Mom", "Landlord")
        
        Returns:
            Dict with success status and message
        """
        logger.info(f"Adding beneficiary for account {account_id}: {beneficiary_account_number}")
        
        # Get customer_id from account
        account_data = self.state_manager.get_account_by_id(account_id)
        if not account_data:
            return {
                'success': False,
                'message': 'Sender account not found'
            }
        
        customer_id = account_data['customer_id']
        
        # Add beneficiary using service
        try:
            beneficiary_service.add_beneficiary(
                customer_id=customer_id,
                account_number=beneficiary_account_number,
                name=beneficiary_name,
                alias=alias or beneficiary_name
            )
            
            return {
                'success': True,
                'message': f'Beneficiary {beneficiary_name} added successfully'
            }
        
        except Exception as e:
            logger.error(f"Error adding beneficiary: {e}")
            return {
                'success': False,
                'message': f'Failed to add beneficiary: {str(e)}'
            }


class UserService:
    """
    User Service - Handles user account lookups.
    
    CHANGED: Now uses StateManager for JSON-based storage.
    """
    
    def __init__(self):
        self.state_manager = get_state_manager()
        logger.info("UserService initialized with JSON StateManager")

    def get_accounts_by_user_name(self, user_name: str) -> List[Account]:
        """
        Get accounts by user email (userName is actually email in the old model).
        
        CHANGED: Now searches JSON data by email.
        """
        # Find customer by email
        customer = self.state_manager.get_customer_by_email(user_name)
        if not customer:
            logger.warning(f"Customer not found by email: {user_name}")
            return []
        
        # Get all accounts for this customer
        all_accounts = self.state_manager.get_accounts()
        accounts_data = [acc for acc in all_accounts if acc['customer_id'] == customer['customer_id']]
        
        # Convert to Account model
        accounts = []
        for account_data in accounts_data:
            accounts.append(
                Account(
                    id=account_data['account_id'],
                    userName=customer['email'],
                    accountHolderFullName=customer['full_name'],
                    currency=account_data['currency'],
                    activationDate="2025-09-01",
                    balance=str(account_data['available_balance']),
                    paymentMethods=None  # Don't populate here - use get_account_details for full info
                )
            )
        
        return accounts
