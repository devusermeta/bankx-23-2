# Contacts MCP Service

Beneficiary management and account verification service for BankX VB project.

## Overview

The Contacts Service provides beneficiary management and account verification as MCP (Model Context Protocol) tools. It handles trusted payee registration, account number validation, and contact management for payments.

## Features

- **Beneficiary Management**: Get, add, and remove registered beneficiaries (trusted payees)
- **Account Verification**: Validate account numbers before payments
- **Registration Check**: Check if account is already registered as beneficiary
- **CSV + JSON Persistence**: Load initial contacts from CSV, save runtime additions to JSON
- **Payment Flow Support**: Optimized for agent-driven payment workflows

## Architecture

```
Contacts Service
│
├── models.py              # Pydantic models (Beneficiary, AccountVerification)
├── services.py            # Business logic (ContactsService)
├── mcp_tools.py           # MCP tool definitions
└── main.py                # FastMCP server entry point
```

**Dependencies:**
- `data_loader_service.py` (from account service) - Account data lookup
- `beneficiary_service.py` (from account service) - Beneficiary persistence

## MCP Tools

### 1. `getRegisteredBeneficiaries`

Get list of registered beneficiaries for an account.

**Parameters:**
- `accountId` (str): Account ID (e.g., "CHK-001")

**Returns:**
```json
[
  {
    "id": "1",
    "account_number": "703-384-928",
    "name": "Anan Chaiyaporn",
    "alias": "Anan",
    "customer_id": "CUST-004",
    "source": "csv",
    "added_date": "2025-10-27"
  }
]
```

**Use Case:** Payment Agent displays list of beneficiaries for quick payment selection

### 2. `verifyAccountNumber`

Verify if an account number exists in the banking system.

**Parameters:**
- `accountNumber` (str): Account number (format: XXX-XXX-XXX)

**Returns:**
```json
{
  "valid": true,
  "account_number": "214-125-859",
  "account_holder_name": "Somchai Rattanakorn",
  "account_id": "CHK-002",
  "message": "Account verified. Holder: Somchai Rattanakorn"
}
```

**Use Case:** Payment to unregistered beneficiary - verify account before proceeding

**Payment Flow with Account Verification:**
```
1. User: "Pay 500 to Somchai"
2. Agent: Calls isBeneficiaryRegistered → NOT registered
3. Agent: "Please provide Somchai's account number"
4. User: "214-125-859"
5. Agent: Calls verifyAccountNumber → Valid
6. Agent: "Confirm payment of 500 THB to Somchai Rattanakorn (214-125-859)?"
7. User: "Yes"
8. Agent: Calls processPayment
9. Payment successful
10. Agent: "Would you like to save Somchai as beneficiary?"
11. User: "Yes"
12. Agent: Calls addBeneficiary
```

### 3. `addBeneficiary`

Add a new beneficiary after successful payment.

**Parameters:**
- `accountId` (str): Sender's account ID
- `beneficiaryAccountNumber` (str): Recipient's account number
- `beneficiaryName` (str): Recipient's full name
- `alias` (str, optional): Friendly name (e.g., "Mom")

**Returns:**
```json
{
  "success": true,
  "message": "Beneficiary Somchai Rattanakorn added successfully"
}
```

**IMPORTANT:** Only call after:
1. Payment was successful
2. Recipient NOT in beneficiary list
3. User explicitly agrees to save

### 4. `removeBeneficiary`

Remove a beneficiary from customer's list.

**Parameters:**
- `accountId` (str): Sender's account ID
- `beneficiaryAccountNumber` (str): Beneficiary's account number to remove

**Returns:**
```json
{
  "success": true,
  "message": "Beneficiary removed successfully"
}
```

### 5. `isBeneficiaryRegistered`

Check if account is registered as beneficiary.

**Parameters:**
- `accountId` (str): Sender's account ID
- `beneficiaryAccountNumber` (str): Account number to check

**Returns:**
```json
{
  "is_registered": true,
  "beneficiary": {
    "account_number": "703-384-928",
    "name": "Anan Chaiyaporn",
    "alias": "Anan"
  },
  "message": "Beneficiary Anan Chaiyaporn is registered"
}
```

**Use Case:** KEY for payment flow decision making
- If registered → auto-populate payment details
- If not → ask for account number

## Data Flow

### Payment Flow with Beneficiary Check

```
1. User requests payment (e.g., "Pay 500 to Anan")
2. Payment Agent calls isBeneficiaryRegistered
3. If registered:
   a. Agent auto-populates details from beneficiary info
   b. Agent asks for confirmation
   c. Agent calls processPayment
4. If NOT registered:
   a. Agent asks for account number
   b. Agent calls verifyAccountNumber (up to 3 retries if invalid)
   c. Agent asks for confirmation
   d. Agent calls processPayment
   e. After success, agent asks if user wants to save (addBeneficiary)
```

## Data Sources

### CSV: `contacts.csv`

Pre-existing beneficiaries (loaded on startup):

```csv
owner_customer_id,account_no,name,alias,relationship
CUST-001,703-384-928,Anan Chaiyaporn,Anan,friend
CUST-001,850-912-436,Wiparat Somchai,Wipa,family
...
```

### JSON: `beneficiary_mappings.json`

Runtime additions (persisted after user saves new beneficiaries):

```json
{
  "CUST-001": [
    {
      "account_number": "214-125-859",
      "name": "Somchai Rattanakorn",
      "alias": "Somchai",
      "source": "json",
      "added_date": "2025-11-06"
    }
  ]
}
```

## Running the Service

### Development Mode (port 8074)

```bash
export PROFILE=dev
python main.py
```

### Production Mode (port 8080)

```bash
export PROFILE=prod
python main.py
```

## Integration with Other Services

### Dependencies

- **DataLoaderService**: Account lookups and verification
- **BeneficiaryService**: Beneficiary persistence (CSV + JSON)

### Consumed By

- **Payment Agent**: All 5 tools for payment flow
- **Account Agent**: getRegisteredBeneficiaries for account overview

## Removed from Account Service

The following tools have been **moved** from Account Service to Contacts Service:

1. ~~`getRegisteredBeneficiary`~~ → `getRegisteredBeneficiaries` (Contacts Service)
2. ~~`verifyAccountNumber`~~ → `verifyAccountNumber` (Contacts Service)
3. ~~`addBeneficiary`~~ → `addBeneficiary` (Contacts Service)

**Account Service now focuses on:**
- Account details and balance
- Payment methods
- User account lookups

**Contacts Service now handles:**
- Beneficiary management
- Account verification
- Contact operations

## Testing

Create test contacts data:

```bash
mkdir -p schemas/tools-sandbox/uc1_synthetic_data
cat > schemas/tools-sandbox/uc1_synthetic_data/contacts.csv << EOF
owner_customer_id,account_no,name,alias,relationship
CUST-001,703-384-928,Anan Chaiyaporn,Anan,friend
CUST-001,850-912-436,Wiparat Somchai,Wipa,family
EOF
```

Test the service:

```bash
# Start the service
PROFILE=dev python main.py

# Test with curl (from another terminal)
curl -X POST http://localhost:8074/mcp/tools/getRegisteredBeneficiaries \
  -H "Content-Type: application/json" \
  -d '{"accountId": "CHK-001"}'

curl -X POST http://localhost:8074/mcp/tools/verifyAccountNumber \
  -H "Content-Type: application/json" \
  -d '{"accountNumber": "214-125-859"}'
```

## Future Enhancements

1. **Beneficiary Groups**: Organize beneficiaries into groups (family, work, utilities)
2. **Favorite Beneficiaries**: Mark frequently used beneficiaries
3. **Beneficiary Limits**: Set per-beneficiary transaction limits
4. **Beneficiary History**: Track payment history per beneficiary
5. **Bulk Beneficiary Import**: Import multiple beneficiaries from CSV
6. **Beneficiary Approval Workflow**: Require approval for adding high-value beneficiaries
