"""
Data Loader Service

This service loads real customer and account data from CSV files.
Replaces the hardcoded dummy data with actual synthetic data from uc1_synthetic_data.

Purpose:
- Provide realistic customer data for testing and development
- Support account verification during payments
- Enable customer lookup by various identifiers (customer_id, account_number, email)

Data Sources:
- customers.csv: Customer personal information
- accounts.csv: Account details and balances
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DataLoaderService:
    """
    Loads and provides access to customer and account data from CSV files.
    
    This simulates a real banking database but uses flat files for simplicity.
    """
    
    def __init__(self):
        """Initialize the data loader and load CSV data into memory."""
        # Path to synthetic data
        # Works in both Docker (/app/schemas) and local (project_root/schemas)
        if Path("/app/schemas").exists():
            # Running in Docker
            self.data_path = Path("/app/schemas") / "tools-sandbox" / "uc1_synthetic_data"
        else:
            # Running locally
            self.data_path = Path(__file__).parent.parent.parent.parent.parent / "schemas" / "tools-sandbox" / "uc1_synthetic_data"
        
        # In-memory storage
        self.customers: Dict[str, Dict] = {}  # customer_id -> customer data
        self.accounts: Dict[str, Dict] = {}   # account_id -> account data
        self.accounts_by_number: Dict[str, Dict] = {}  # account_no -> account data
        self.accounts_by_customer: Dict[str, List[Dict]] = {}  # customer_id -> list of accounts
        
        # Load data
        self._load_customers()
        self._load_accounts()
        
        logger.info(f"DataLoaderService initialized: {len(self.customers)} customers, {len(self.accounts)} accounts")
    
    
    def _load_customers(self):
        """
        Load customer data from customers.csv.
        Also loads bankx_email from customers.json if available.
        
        CSV columns: customer_id, full_name, email, phone
        """
        customers_file = self.data_path / "customers.csv"
        
        try:
            with open(customers_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    customer_id = row['customer_id']
                    self.customers[customer_id] = {
                        'customer_id': customer_id,
                        'full_name': row['full_name'],
                        'email': row['email'],
                        'phone': row['phone']
                    }
            
            logger.info(f"Loaded {len(self.customers)} customers from CSV")
            
            # Also load bankx_email from dynamic_data/customers.json
            json_customers_file = Path(__file__).parent.parent.parent.parent.parent / "dynamic_data" / "customers.json"
            try:
                import json
                from datetime import datetime
                print(f"🔄 [DATA_LOADER] Loading bankx_email from customers.json at {datetime.now()}")
                with open(json_customers_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    count = 0
                    for customer_data in json_data.get('customers', []):
                        customer_id = customer_data.get('customer_id')
                        if customer_id in self.customers and 'bankx_email' in customer_data:
                            # Add bankx_email to existing customer record
                            self.customers[customer_id]['bankx_email'] = customer_data['bankx_email']
                            count += 1
                print(f"✅ [DATA_LOADER] Enhanced {count} customers with bankx_email from JSON")
                logger.info(f"Enhanced {count} customers with bankx_email from JSON")
            except Exception as e:
                print(f"❌ [DATA_LOADER] Could not load bankx_email from customers.json: {e}")
                logger.warning(f"Could not load bankx_email from customers.json: {e}")
        
        except FileNotFoundError:
            logger.error(f"customers.csv not found at {customers_file}")
        except Exception as e:
            logger.error(f"Error loading customers: {e}")
    
    
    def _load_accounts(self):
        """
        Load account data from accounts.csv.
        
        CSV columns: account_id, customer_id, account_no, cust_name, acc_type, 
                     currency, ledger_balance, available_balance
        """
        accounts_file = self.data_path / "accounts.csv"
        
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    account_id = row['account_id']
                    customer_id = row['customer_id']
                    account_no = row['account_no']
                    
                    account_data = {
                        'account_id': account_id,
                        'customer_id': customer_id,
                        'account_no': account_no,
                        'cust_name': row['cust_name'],
                        'acc_type': row['acc_type'],
                        'currency': row['currency'],
                        'ledger_balance': float(row['ledger_balance']),
                        'available_balance': float(row['available_balance'])
                    }
                    
                    # Store in multiple indexes for fast lookup
                    self.accounts[account_id] = account_data
                    self.accounts_by_number[account_no] = account_data
                    
                    # Group accounts by customer
                    if customer_id not in self.accounts_by_customer:
                        self.accounts_by_customer[customer_id] = []
                    self.accounts_by_customer[customer_id].append(account_data)
            
            logger.info(f"Loaded {len(self.accounts)} accounts from CSV")
        
        except FileNotFoundError:
            logger.error(f"accounts.csv not found at {accounts_file}")
        except Exception as e:
            logger.error(f"Error loading accounts: {e}")
    
    
    def get_customer_by_id(self, customer_id: str) -> Optional[Dict]:
        """
        Get customer information by customer ID.
        
        Args:
            customer_id: Customer identifier (e.g., "CUST-001")
        
        Returns:
            Customer dict or None if not found
        """
        return self.customers.get(customer_id)
    
    
    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """
        Get customer information by email address.
        Searches both 'email' and 'bankx_email' fields.
        
        Args:
            email: Customer's email address (can be regular email or BankX Entra ID email)
        
        Returns:
            Customer dict or None if not found
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 [ACCOUNT_SERVICE] Searching for customer with email: {email}")
        logger.info(f"🔍 [ACCOUNT_SERVICE] NEW CODE LOADED - Checking both email and bankx_email fields")
        
        for customer in self.customers.values():
            # Check regular email
            if customer['email'].lower() == email.lower():
                logger.info(f"✅ [ACCOUNT_SERVICE] Found customer by regular email: {customer['customer_id']}")
                return customer
            # Also check bankx_email (Entra ID email)
            if 'bankx_email' in customer and customer['bankx_email'].lower() == email.lower():
                logger.info(f"✅ [ACCOUNT_SERVICE] Found customer by bankx_email: {customer['customer_id']}")
                return customer
        
        logger.warning(f"❌ [ACCOUNT_SERVICE] Customer not found for email: {email}")
        return None
    
    
    def get_account_by_number(self, account_no: str) -> Optional[Dict]:
        """
        Get account information by account number.
        
        This is the KEY function for payment verification:
        - User provides account number
        - System verifies it exists
        - Returns account details if valid
        
        Args:
            account_no: Account number (e.g., "214-125-859")
        
        Returns:
            Account dict or None if not found
        """
        return self.accounts_by_number.get(account_no)
    
    
    def get_accounts_by_customer(self, customer_id: str) -> List[Dict]:
        """
        Get all accounts for a specific customer.
        
        Args:
            customer_id: Customer identifier
        
        Returns:
            List of account dicts (may be empty)
        """
        return self.accounts_by_customer.get(customer_id, [])
    
    
    def verify_account_exists(self, account_no: str) -> bool:
        """
        Verify if an account number exists in the system.
        
        Used during payment flow to validate recipient account.
        
        Args:
            account_no: Account number to verify
        
        Returns:
            True if account exists, False otherwise
        """
        exists = account_no in self.accounts_by_number
        
        if exists:
            logger.info(f"Account verified: {account_no}")
        else:
            logger.warning(f"Account NOT found: {account_no}")
        
        return exists
    
    
    def get_account_holder_name(self, account_no: str) -> Optional[str]:
        """
        Get the account holder's name for a given account number.
        
        Useful for confirmation messages: "You are sending to Somchai Rattanakorn"
        
        Args:
            account_no: Account number
        
        Returns:
            Account holder's name or None if account not found
        """
        account = self.get_account_by_number(account_no)
        if account:
            # Get full name from customer data
            customer_id = account['customer_id']
            customer = self.get_customer_by_id(customer_id)
            if customer:
                return customer['full_name']
            # Fallback to short name from account
            return account['cust_name']
        return None


# Singleton instance
data_loader_service = DataLoaderService()
