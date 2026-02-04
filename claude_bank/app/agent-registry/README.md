# BankX Agent Registry Service

The Agent Registry is a centralized service discovery system for the BankX Multi-Agent Banking System. It enables agents to register themselves, discover other agents, and maintain health status.

## Features

- **Agent Registration**: Agents can register themselves with capabilities and endpoints
- **Service Discovery**: Discover agents by capability, type, or status
- **Health Monitoring**: Automatic health checks and stale agent removal
- **Dual Storage**: Redis for fast lookups + Cosmos DB for persistence
- **Authentication**: JWT-based authentication for agent-to-agent security
- **Metrics**: Prometheus-compatible metrics endpoint

## Quick Start

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export REDIS_URL="redis://localhost:6379"
export AZURE_COSMOS_ENDPOINT="https://your-cosmos.documents.azure.com:443/"
export AZURE_COSMOS_KEY="your-key"
export A2A_JWT_SECRET_KEY="your-secret-key"

# Run the service
python -m uvicorn main:app --host 0.0.0.0 --port 9000 --reload
```

### Docker

```bash
# Build image
docker build -t bankx/agent-registry:1.0.0 .

# Run container
docker run -d \
  --name agent-registry \
  -p 9000:9000 \
  -e REDIS_URL=redis://redis:6379 \
  -e AZURE_COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/ \
  -e AZURE_COSMOS_KEY=your-key \
  bankx/agent-registry:1.0.0
```

## API Endpoints

### Register Agent
```http
POST /api/v1/agents/register
Content-Type: application/json

{
  "agent_name": "AccountAgent",
  "agent_type": "domain",
  "version": "1.0.0",
  "capabilities": ["account.balance", "account.limits"],
  "endpoints": {
    "http": "http://localhost:8100",
    "health": "http://localhost:8100/health",
    "a2a": "http://localhost:8100/a2a/invoke"
  }
}
```

### Discover Agents
```http
GET /api/v1/agents/discover?capability=account.balance&status=active
```

### Heartbeat
```http
POST /api/v1/agents/{agent_id}/heartbeat
```

### Get Agent
```http
GET /api/v1/agents/{agent_id}
```

### Deregister Agent
```http
DELETE /api/v1/agents/{agent_id}
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `AZURE_COSMOS_ENDPOINT` | Cosmos DB endpoint | None |
| `AZURE_COSMOS_KEY` | Cosmos DB key | None |
| `A2A_JWT_SECRET_KEY` | JWT secret key | (change in production) |
| `A2A_HEALTH_CHECK_ENABLED` | Enable health checks | `true` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Health Check

```bash
curl http://localhost:9000/health
```

## Metrics

```bash
curl http://localhost:9000/metrics
```

Returns:
```json
{
  "total_agents": 5,
  "active_agents": 4,
  "inactive_agents": 0,
  "degraded_agents": 1,
  "agents_by_type": {
    "supervisor": 1,
    "domain": 3,
    "knowledge": 1
  }
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│       Agent Registry Service            │
│                                         │
│  ┌──────────────┐   ┌───────────────┐ │
│  │   FastAPI    │   │  Health       │ │
│  │   REST API   │   │  Monitor      │ │
│  └──────┬───────┘   └───────┬───────┘ │
│         │                   │         │
│  ┌──────▼───────────────────▼───────┐ │
│  │    Registry Service              │ │
│  │  (Business Logic)                │ │
│  └──────┬───────────────────┬───────┘ │
│         │                   │         │
│  ┌──────▼──────┐     ┌─────▼──────┐  │
│  │ Redis Store │     │ Cosmos DB  │  │
│  │ (Cache)     │     │ (Persist)  │  │
│  └─────────────┘     └────────────┘  │
└─────────────────────────────────────────┘
```

## Deployment

### Azure Container Apps

```bash
# Create container app
az containerapp create \
  --name agent-registry \
  --resource-group bankx-dev-rg \
  --environment bankx-agent-env \
  --image bankx/agent-registry:1.0.0 \
  --target-port 9000 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 5 \
  --env-vars \
    REDIS_URL=redis://bankx-redis:6379 \
    AZURE_COSMOS_ENDPOINT=https://bankx-cosmos.documents.azure.com:443/ \
    A2A_HEALTH_CHECK_ENABLED=true
```

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## License

Copyright © 2025 BankX
