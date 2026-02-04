"""
Beneficiary Management Service

This service manages beneficiary (trusted payee) relationships for customers.
In real-world banking, customers can register beneficiaries to simplify future payments.

Key Features:
- Load existing beneficiaries from contacts.csv (pre-registered)
- Add new beneficiaries dynamically during payment flow
- Store beneficiary mappings in JSON for persistence
- Validate beneficiaries against actual customer/account data

Data Flow:
1. On startup, load contacts.csv into memory
2. Allow runtime additions (user saves new beneficiary)
3. Persist new beneficiaries to beneficiary_mappings.json
"""

import json
import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

# Add common module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "common"))
from path_utils import get_csv_data_dir, get_data_dir

logger = logging.getLogger(__name__)


class BeneficiaryService:
    """
    Manages beneficiary relationships between customers.
    
    A beneficiary is a trusted payee that a customer has pre-registered,
    allowing for faster payments without re-entering account details.
    """
    
    def __init__(self):
        """Initialize the beneficiary service with CSV and JSON data."""
        # Use environment-aware path resolution
        self.data_path = get_csv_data_dir()
        
        # Path to store runtime beneficiary additions (JSON file in data folder)
        self.json_storage_path = get_data_dir() / "beneficiary_mappings.json"
        
        # In-memory storage: maps customer_id -> list of beneficiaries
        # Structure: {
        #   "CUST-001": [
        #       {"customer_id": "CUST-004", "account_number": "703-384-928", "name": "Anan Chaiyaporn", "alias": "Anan", "added_date": "2025-11-03"}
        #   ]
        # }
        self.beneficiary_mappings: Dict[str, List[Dict]] = {}
        
        # Load initial data
        self._load_contacts_from_csv()
        self._load_beneficiaries_from_json()
        
        logger.info(f"BeneficiaryService initialized with {len(self.beneficiary_mappings)} customer mappings")
    
    
    def _load_contacts_from_csv(self):
        """
        Load pre-existing contacts from contacts.csv.
        
        This represents beneficiaries that customers have already registered
        through the bank's normal channels (branch, online banking, etc.)
        """
        contacts_file = self.data_path / "contacts.csv"
        
        try:
            with open(contacts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    owner_id = row['owner_customer_id']
                    
                    # Create beneficiary entry
                    beneficiary = {
                        "account_number": row['account_no'],
                        "name": row['name'],
                        "alias": row['alias'],
                        "source": "csv",  # Mark as pre-existing
                        "added_date": "2025-10-27"  # From README - when data was generated
                    }
                    
                    # Add to owner's beneficiary list
                    if owner_id not in self.beneficiary_mappings:
                        self.beneficiary_mappings[owner_id] = []
                    
                    self.beneficiary_mappings[owner_id].append(beneficiary)
            
            logger.info(f"Loaded {sum(len(v) for v in self.beneficiary_mappings.values())} contacts from CSV")
        
        except FileNotFoundError:
            logger.warning(f"contacts.csv not found at {contacts_file}")
        except Exception as e:
            logger.error(f"Error loading contacts from CSV: {e}")
    
    
    def _load_beneficiaries_from_json(self):
        """
        Load runtime-added beneficiaries from JSON storage.
        
        These are beneficiaries that users have added during payment flows,
        not pre-existing in the CSV data.
        """
        if not self.json_storage_path.exists():
            logger.info("No existing beneficiary_mappings.json found (will create on first save)")
            return
        
        try:
            with open(self.json_storage_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                
                # Merge JSON beneficiaries with CSV beneficiaries
                for customer_id, beneficiaries in json_data.items():
                    if customer_id not in self.beneficiary_mappings:
                        self.beneficiary_mappings[customer_id] = []
                    
                    # Add JSON beneficiaries (mark them as runtime-added)
                    for ben in beneficiaries:
                        ben['source'] = 'json'  # Mark as runtime-added
                        self.beneficiary_mappings[customer_id].append(ben)
            
            logger.info(f"Loaded beneficiaries from JSON: {self.json_storage_path}")
        
        except Exception as e:
            logger.error(f"Error loading beneficiaries from JSON: {e}")
    
    
    def _save_beneficiaries_to_json(self):
        """
        Save runtime-added beneficiaries to JSON file.
        
        Only saves beneficiaries that were added during runtime (source='json'),
        not the pre-existing CSV contacts.
        """
        # Filter out CSV-sourced beneficiaries (only save runtime additions)
        json_data = {}
        
        for customer_id, beneficiaries in self.beneficiary_mappings.items():
            json_beneficiaries = [b for b in beneficiaries if b.get('source') == 'json']
            if json_beneficiaries:
                json_data[customer_id] = json_beneficiaries
        
        # Ensure data directory exists
        self.json_storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.json_storage_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved beneficiaries to JSON: {self.json_storage_path}")
        
        except Exception as e:
            logger.error(f"Error saving beneficiaries to JSON: {e}")
    
    
    def get_beneficiaries(self, customer_id: str) -> List[Dict]:
        """
        Get all beneficiaries for a specific customer.
        
        Args:
            customer_id: The customer's unique ID (e.g., "CUST-001")
        
        Returns:
            List of beneficiary dictionaries, or empty list if none found
        """
        beneficiaries = self.beneficiary_mappings.get(customer_id, [])
        logger.info(f"Retrieved {len(beneficiaries)} beneficiaries for {customer_id}")
        return beneficiaries
    
    
    def is_beneficiary_registered(self, customer_id: str, account_number: str) -> Optional[Dict]:
        """
        Check if a specific account number is registered as a beneficiary for this customer.
        
        This is the KEY function for the payment flow:
        - If beneficiary exists → return their details (auto-populate payment)
        - If not exists → return None (need to ask for details)
        
        Args:
            customer_id: The customer making the payment
            account_number: The recipient's account number
        
        Returns:
            Beneficiary dict if found, None otherwise
        """
        beneficiaries = self.get_beneficiaries(customer_id)
        
        for beneficiary in beneficiaries:
            if beneficiary['account_number'] == account_number:
                logger.info(f"Found registered beneficiary: {beneficiary['name']} ({account_number})")
                return beneficiary
        
        logger.info(f"Account {account_number} is NOT a registered beneficiary for {customer_id}")
        return None
    
    
    def add_beneficiary(self, customer_id: str, account_number: str, name: str, 
                       alias: Optional[str] = None, customer_id_beneficiary: Optional[str] = None) -> bool:
        """
        Add a new beneficiary for a customer.
        
        This is called when:
        1. User makes payment to unregistered account
        2. Payment succeeds
        3. User chooses to save recipient as beneficiary
        
        Args:
            customer_id: The customer adding the beneficiary
            account_number: The beneficiary's account number
            name: Full name of the beneficiary
            alias: Optional nickname for the beneficiary
            customer_id_beneficiary: Optional customer ID of the beneficiary
        
        Returns:
            True if added successfully, False if already exists
        """
        # Check if already registered
        if self.is_beneficiary_registered(customer_id, account_number):
            logger.warning(f"Beneficiary {account_number} already registered for {customer_id}")
            return False
        
        # Create new beneficiary entry
        new_beneficiary = {
            "account_number": account_number,
            "name": name,
            "alias": alias or name.split()[0],  # Default alias is first name
            "customer_id": customer_id_beneficiary,  # Optional
            "source": "json",  # Runtime-added
            "added_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Add to in-memory storage
        if customer_id not in self.beneficiary_mappings:
            self.beneficiary_mappings[customer_id] = []
        
        self.beneficiary_mappings[customer_id].append(new_beneficiary)
        
        # Persist to JSON file
        self._save_beneficiaries_to_json()
        
        logger.info(f"Added new beneficiary {name} ({account_number}) for customer {customer_id}")
        return True
    
    
    def remove_beneficiary(self, customer_id: str, account_number: str) -> bool:
        """
        Remove a beneficiary from a customer's list.
        
        Args:
            customer_id: The customer ID
            account_number: The beneficiary's account number to remove
        
        Returns:
            True if removed, False if not found
        """
        if customer_id not in self.beneficiary_mappings:
            return False
        
        # Find and remove the beneficiary
        original_count = len(self.beneficiary_mappings[customer_id])
        self.beneficiary_mappings[customer_id] = [
            b for b in self.beneficiary_mappings[customer_id]
            if b['account_number'] != account_number
        ]
        
        removed = len(self.beneficiary_mappings[customer_id]) < original_count
        
        if removed:
            # Update JSON storage
            self._save_beneficiaries_to_json()
            logger.info(f"Removed beneficiary {account_number} for customer {customer_id}")
        
        return removed


# Singleton instance for the service
beneficiary_service = BeneficiaryService()
