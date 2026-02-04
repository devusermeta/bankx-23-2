"""
Contacts Service

Business logic for beneficiary management and account verification.
"""

import sys
from pathlib import Path
from typing import List, Optional
import logging

from models import Beneficiary, AccountVerification

# Add account service path to import data loader and beneficiary service
sys.path.insert(0, str(Path(__file__).parent.parent / "account"))
from data_loader_service import DataLoaderService
from beneficiary_service import BeneficiaryService

logger = logging.getLogger(__name__)


class ContactsService:
    """
    Contacts Service - Handles beneficiary management and account verification.

    Key responsibilities:
    1. Get registered beneficiaries for a customer
    2. Verify if an account number exists in the system
    3. Add new beneficiaries after successful payments
    4. Remove beneficiaries
    5. Check if a specific account is registered as beneficiary
    """

    def __init__(self, data_loader: Optional[DataLoaderService] = None,
                 beneficiary_service: Optional[BeneficiaryService] = None):
        """
        Initialize Contacts Service.

        Args:
            data_loader: Optional data loader service (for account verification)
            beneficiary_service: Optional beneficiary service (for beneficiary management)
        """
        self.data_loader = data_loader or DataLoaderService()
        self.beneficiary_service = beneficiary_service or BeneficiaryService()
        logger.info("ContactsService initialized")


    def get_registered_beneficiaries(self, account_id: str) -> List[Beneficiary]:
        """
        Get list of registered beneficiaries for an account.

        Args:
            account_id: Account ID (e.g., "CHK-001")

        Returns:
            List of Beneficiary models
        """
        logger.info(f"Getting registered beneficiaries for account {account_id}")

        # Get account data to find customer_id
        account_data = self.data_loader.accounts.get(account_id)
        if not account_data:
            logger.warning(f"Account not found: {account_id}")
            return []

        customer_id = account_data['customer_id']

        # Get beneficiaries from service
        beneficiaries_data = self.beneficiary_service.get_beneficiaries(customer_id)

        # Convert to Beneficiary model
        beneficiaries = []
        for i, ben_data in enumerate(beneficiaries_data):
            beneficiaries.append(
                Beneficiary(
                    id=str(i + 1),
                    account_number=ben_data.get('account_number', ''),
                    name=ben_data.get('name', 'Unknown'),
                    alias=ben_data.get('alias', ''),
                    customer_id=ben_data.get('customer_id'),
                    source=ben_data.get('source'),
                    added_date=ben_data.get('added_date')
                )
            )

        logger.info(f"Found {len(beneficiaries)} beneficiaries for customer {customer_id}")
        return beneficiaries


    def verify_account_number(self, account_number: str) -> AccountVerification:
        """
        Verify if an account number exists in the system.

        KEY function for payment flow with unregistered beneficiaries.

        When user wants to pay someone not in their beneficiary list:
        1. Agent asks for account number
        2. This function verifies it exists
        3. If valid, returns account holder name for confirmation
        4. If invalid, agent retry logic kicks in (max 3 attempts)

        Args:
            account_number: Account number to verify (e.g., "214-125-859")

        Returns:
            AccountVerification model with validation result
        """
        logger.info(f"Verifying account number: {account_number}")

        # Check if account exists
        account = self.data_loader.get_account_by_number(account_number)

        if account:
            # Get account holder name
            holder_name = self.data_loader.get_account_holder_name(account_number)

            return AccountVerification(
                valid=True,
                account_number=account_number,
                account_holder_name=holder_name,
                account_id=account['account_id'],
                message=f'Account verified. Holder: {holder_name}'
            )
        else:
            return AccountVerification(
                valid=False,
                account_number=account_number,
                message='Invalid account number. Please check and try again.'
            )


    def add_beneficiary(
        self,
        account_id: str,
        beneficiary_account_number: str,
        beneficiary_name: str,
        alias: Optional[str] = None
    ) -> dict:
        """
        Add a new beneficiary after successful payment.

        Called when user confirms they want to save recipient as beneficiary.

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
        account_data = self.data_loader.accounts.get(account_id)
        if not account_data:
            return {
                'success': False,
                'message': 'Sender account not found'
            }

        customer_id = account_data['customer_id']

        # Add beneficiary using service
        try:
            success = self.beneficiary_service.add_beneficiary(
                customer_id=customer_id,
                account_number=beneficiary_account_number,
                name=beneficiary_name,
                alias=alias or beneficiary_name
            )

            if success:
                return {
                    'success': True,
                    'message': f'Beneficiary {beneficiary_name} added successfully'
                }
            else:
                return {
                    'success': False,
                    'message': f'Beneficiary {beneficiary_name} is already registered'
                }

        except Exception as e:
            logger.error(f"Error adding beneficiary: {e}")
            return {
                'success': False,
                'message': f'Failed to add beneficiary: {str(e)}'
            }


    def remove_beneficiary(self, account_id: str, beneficiary_account_number: str) -> dict:
        """
        Remove a beneficiary from customer's list.

        Args:
            account_id: Sender's account ID
            beneficiary_account_number: Beneficiary's account number to remove

        Returns:
            Dict with success status and message
        """
        logger.info(f"Removing beneficiary for account {account_id}: {beneficiary_account_number}")

        # Get customer_id from account
        account_data = self.data_loader.accounts.get(account_id)
        if not account_data:
            return {
                'success': False,
                'message': 'Sender account not found'
            }

        customer_id = account_data['customer_id']

        # Remove beneficiary using service
        try:
            success = self.beneficiary_service.remove_beneficiary(
                customer_id=customer_id,
                account_number=beneficiary_account_number
            )

            if success:
                return {
                    'success': True,
                    'message': f'Beneficiary removed successfully'
                }
            else:
                return {
                    'success': False,
                    'message': 'Beneficiary not found'
                }

        except Exception as e:
            logger.error(f"Error removing beneficiary: {e}")
            return {
                'success': False,
                'message': f'Failed to remove beneficiary: {str(e)}'
            }


    def is_beneficiary_registered(
        self,
        account_id: str,
        beneficiary_account_number: str
    ) -> dict:
        """
        Check if a specific account is registered as beneficiary.

        This is KEY for payment flow decision making:
        - If registered → auto-populate payment details
        - If not → ask for account number and verify

        Args:
            account_id: Sender's account ID
            beneficiary_account_number: Account number to check

        Returns:
            Dict with is_registered bool and beneficiary details if found
        """
        logger.info(f"Checking if {beneficiary_account_number} is registered for account {account_id}")

        # Get customer_id from account
        account_data = self.data_loader.accounts.get(account_id)
        if not account_data:
            return {
                'is_registered': False,
                'message': 'Sender account not found'
            }

        customer_id = account_data['customer_id']

        # Check if beneficiary exists
        beneficiary = self.beneficiary_service.is_beneficiary_registered(
            customer_id=customer_id,
            account_number=beneficiary_account_number
        )

        if beneficiary:
            return {
                'is_registered': True,
                'beneficiary': beneficiary,
                'message': f"Beneficiary {beneficiary['name']} is registered"
            }
        else:
            return {
                'is_registered': False,
                'message': 'Beneficiary not registered'
            }
