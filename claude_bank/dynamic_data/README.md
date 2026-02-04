# Dynamic Data Folder

This folder contains **runtime state** for the banking demo application. Files here are updated dynamically as transactions occur and are persisted across application restarts.

## Files

### `account_balances.json`
- **Purpose:** Stores current account balances (overrides CSV seed data)
- **Format:** `{ "CHK-001": 102427.94, "CHK-002": 216483.22, ... }`
- **Updates:** Modified on every payment/transfer
- **Initial state:** Created on first payment (uses CSV balances as baseline)

### `transactions.json`
- **Purpose:** Stores new transactions created during runtime
- **Format:** Account ID → List of transaction objects
- **Updates:** New transaction appended on every payment
- **Merge logic:** Combined with `transactions.csv` (historical) for complete history

### `beneficiary_mappings.json`
- **Purpose:** Stores beneficiary/payee relationships added at runtime
- **Format:** Customer ID → List of beneficiary objects
- **Updates:** Modified when user saves new beneficiaries
- **Merge logic:** Combined with `contacts.csv` (pre-existing) for complete list

## Data Flow

```
Application Startup:
├─ Load CSV files (read-only seed data)
│  ├─ schemas/tools-sandbox/uc1_synthetic_data/accounts.csv → Initial balances
│  ├─ schemas/tools-sandbox/uc1_synthetic_data/transactions.csv → Historical transactions
│  └─ schemas/tools-sandbox/uc1_synthetic_data/contacts.csv → Pre-existing beneficiaries
│
└─ Load JSON files (read-write runtime state)
   ├─ dynamic_data/account_balances.json → Current balances (if exists)
   ├─ dynamic_data/transactions.json → New transactions (if exists)
   └─ dynamic_data/beneficiary_mappings.json → New beneficiaries (if exists)

During Runtime:
├─ User sends payment → Update both balances, create 2 transactions (OUT + IN)
├─ Save to account_balances.json (atomic update)
└─ Append to transactions.json (persistent history)

On Restart:
└─ All balances and transactions persist! ✅
```

## Example: Payment Flow

**Before payment:**
- Somchai (CHK-001): 102,927.94 THB
- Anan (CHK-004): 220,994.98 THB

**User action:** "Send 500 THB to Anan"

**After payment:**
- Somchai (CHK-001): 102,427.94 THB (↓ 500)
- Anan (CHK-004): 221,494.98 THB (↑ 500)

**Persisted to:**
1. `account_balances.json` (both accounts updated)
2. `transactions.json` (2 new transactions: OUT for Somchai, IN for Anan)

**Result:** After browser reload or service restart, balances and transaction history remain intact! 🎯

## Reset to Initial State

To reset to CSV seed data:
```bash
# Delete JSON files
rm dynamic_data/account_balances.json
rm dynamic_data/transactions.json
# Keep beneficiary_mappings.json if you want to preserve saved beneficiaries
```

Next application startup will reload from CSV files only.
