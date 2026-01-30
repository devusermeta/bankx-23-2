# Dynamic Data Directory

This directory contains runtime JSON files generated from CSV seed data.

## Files

- `accounts.json` - Account balances and details (updated on transactions)
- `limits.json` - Transaction limits (updated on transactions)
- `customers.json` - Customer information

## Initialization

These files are created by running:

```powershell
cd ..\scripts
python init_data.py
```

## Purpose

JSON files provide persistent runtime state:
- Account balances update when transfers occur
- Daily limits decrease as transactions are made
- All changes persist across server restarts

## Resetting Data

To reset to initial state from CSVs:

```powershell
cd ..\scripts
python init_data.py
```

This will regenerate all JSON files from the CSV seed data in `../InitialData/`.

## Schema

Each JSON file includes:
- `_metadata` - Source information and last updated timestamp
- Data array - List of records

See example files after running `init_data.py`.
