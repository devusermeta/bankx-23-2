# Limits MCP Service

Transaction limits management service for BankX VB project.

## Overview

The Limits Service provides transaction limit checking and validation as an MCP (Model Context Protocol) tool. It supports Policy Gate validation for transfers (US 1.4) and provides comprehensive limits information for account balance displays (US 1.3).

## Features

- **Per-Transaction Limit Checking**: Validates if a transaction amount is within the per-transaction limit (default: 50,000 THB)
- **Daily Limit Checking**: Validates if a transaction is within remaining daily limit (default: 200,000 THB)
- **Balance Checking**: Validates if account has sufficient balance for the transaction
- **Daily Limit Updates**: Updates remaining daily limit after successful payments
- **CSV Data Loading**: Loads initial limits from `limits.csv`
- **Runtime Persistence**: Saves limit updates to JSON for persistence across sessions

## Architecture

```
Limits Service
│
├── models.py                         # Pydantic models (AccountLimits, LimitsCheckResult)
├── limits_persistence_service.py     # CSV + JSON data loading/persistence
├── services.py                       # Business logic (LimitsService)
├── mcp_tools.py                      # MCP tool definitions
└── main.py                           # FastMCP server entry point
```

## MCP Tools

### 1. `checkLimits`

Check if a transaction is within all limits (Policy Gate validation).

**Parameters:**
- `accountId` (str): Account ID (e.g., "CHK-001")
- `amount` (float): Transaction amount to validate
- `currency` (str): Currency code (default: "THB")

**Returns:**
```json
{
  "sufficient_balance": true,
  "within_per_txn_limit": true,
  "within_daily_limit": true,
  "remaining_after": 95000.00,
  "daily_limit_remaining_after": 195000.00,
  "current_balance": 100000.00,
  "error_message": null
}
```

**Use Case:** US 1.4 - Transfer Approval (Policy Gate validation)

### 2. `getAccountLimits`

Get comprehensive limits information for an account.

**Parameters:**
- `accountId` (str): Account ID

**Returns:**
```json
{
  "per_transaction_limit": 50000.00,
  "daily_limit": 200000.00,
  "remaining_today": 200000.00,
  "daily_used": 0.00,
  "utilization_percent": 0.0,
  "currency": "THB"
}
```

**Use Case:** US 1.3 - Balance and Limits (BALANCE_CARD)

### 3. `updateLimitsAfterTransaction`

Update daily limits after a successful transaction.

**Parameters:**
- `accountId` (str): Account ID
- `amount` (float): Transaction amount (positive value)

**Returns:**
```json
{
  "status": "ok",
  "message": "Limits updated for account CHK-001"
}
```

**Note:** This is called internally by Payment Service, not by agents directly.

## Data Flow

### Policy Gate Validation (US 1.4)

```
1. Payment Agent receives transfer request
2. Agent calls checkLimits MCP tool
3. Limits Service checks:
   - Balance (via BalancePersistenceService)
   - Per-transaction limit
   - Daily limit remaining
4. Returns validation result
5. Agent presents TRANSFER_APPROVAL card to user
6. User approves
7. Agent calls processPayment MCP tool
8. Payment Service executes payment
9. Payment Service calls updateLimitsAfterTransaction
10. Limits Service updates remaining daily limit
```

## Data Sources

### CSV: `limits.csv`

Initial limits data (loaded on startup):

```csv
account_id,per_txn_limit,daily_limit,remaining_today,currency
CHK-001,50000.00,200000.00,200000.00,THB
CHK-002,50000.00,200000.00,200000.00,THB
...
```

### JSON: `data/limits_updates.json`

Runtime updates (persisted after transactions):

```json
{
  "CHK-001": {
    "account_id": "CHK-001",
    "per_txn_limit": 50000.00,
    "daily_limit": 200000.00,
    "remaining_today": 195000.00,
    "currency": "THB"
  }
}
```

## Default Limits

If no CSV data is available, the service uses these defaults:

- **Per-Transaction Limit**: 50,000 THB
- **Daily Limit**: 200,000 THB
- **Currency**: THB

## Running the Service

### Development Mode (port 8073)

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

- **BalancePersistenceService**: Used to check current account balance during limits validation
- **Payment Service**: Calls Limits Service after successful payment to update daily limits

### Consumed By

- **Payment Agent**: Calls `checkLimits` for Policy Gate validation before presenting TRANSFER_APPROVAL
- **Account Agent**: Calls `getAccountLimits` for BALANCE_CARD display
- **Payment Service**: Calls `updateLimitsAfterTransaction` after successful payment

## Testing

Create test limits data:

```bash
mkdir -p schemas/tools-sandbox/uc1_synthetic_data
echo "account_id,per_txn_limit,daily_limit,remaining_today,currency" > schemas/tools-sandbox/uc1_synthetic_data/limits.csv
echo "CHK-001,50000.00,200000.00,200000.00,THB" >> schemas/tools-sandbox/uc1_synthetic_data/limits.csv
```

Test the service:

```bash
# Start the service
PROFILE=dev python main.py

# Test with MCP client (from another terminal)
curl -X POST http://localhost:8073/mcp/tools/checkLimits \
  -H "Content-Type: application/json" \
  -d '{"accountId": "CHK-001", "amount": 5000.00, "currency": "THB"}'
```

## Daily Limit Reset

**Note:** Daily limit reset is not yet implemented. In production, a scheduled job should call `reset_daily_limits()` at midnight (Asia/Bangkok timezone).

For now, daily limits persist across sessions and only reset when:
1. The service is restarted AND
2. The `limits_updates.json` file is deleted

## Future Enhancements

1. **Scheduled Daily Reset**: Add cron job or Azure Function to reset limits at midnight
2. **Custom Limits**: Support per-customer custom limits (VIP customers, business accounts)
3. **Monthly Limits**: Add monthly transaction limits
4. **Limit History**: Track limit usage history for analytics
5. **Dynamic Limit Adjustment**: AI-based dynamic limit adjustment based on user behavior
