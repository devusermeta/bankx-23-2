# Cache MCP Service

FastMCP-based service for cache invalidation in the banking assistant.

## Features

- **invalidateCache**: Delete user cache to force fresh data retrieval after data modifications

## Port

- **8079** (default)

## Usage

```bash
# Start the service
cd claude_bank\app\business-api\python\cache
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

## Environment Variables

- `PROFILE`: Environment profile (dev/prod)
- `PORT`: Service port (default: 8079)

## Dependencies

- fastmcp
- pydantic
- filelock
