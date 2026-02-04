# A2A SDK - Agent-to-Agent Communication Library

The A2A SDK is a Python library that enables seamless agent-to-agent communication in the BankX Multi-Agent System. It provides service discovery, circuit breaking, retry logic, and distributed tracing out of the box.

## Features

- **Service Discovery**: Automatic agent discovery through registry
- **Circuit Breaker**: Protect against cascading failures
- **Retry Logic**: Exponential backoff for transient failures
- **Distributed Tracing**: OpenTelemetry integration
- **Type Safety**: Full Pydantic models for messages
- **Async/Await**: Modern async Python API

## Installation

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
cd app/a2a-sdk
pip install -e .
```

## Quick Start

### 1. Initialize Registry Client

```python
from a2a_sdk import RegistryClient

registry_client = RegistryClient(
    registry_url="http://localhost:9000"
)

# Register your agent
registration = await registry_client.register(
    agent_name="AccountAgent",
    agent_type="domain",
    capabilities=["account.balance", "account.limits"],
    endpoints={
        "http": "http://localhost:8100",
        "health": "http://localhost:8100/health",
        "a2a": "http://localhost:8100/a2a/invoke"
    }
)

agent_id = registration["agent_id"]
```

### 2. Create A2A Client

```python
from a2a_sdk import A2AClient, A2AConfig

config = A2AConfig(
    timeout_seconds=30,
    max_retries=3,
    circuit_breaker_threshold=5
)

a2a_client = A2AClient(
    agent_id=agent_id,
    agent_name="SupervisorAgent",
    registry_client=registry_client,
    config=config
)
```

### 3. Send A2A Message

```python
# Call another agent by capability
response = await a2a_client.send_message(
    target_capability="account.balance",
    intent="account.get_balance",
    payload={
        "customer_id": "CUST-001",
        "account_id": "CHK-001"
    }
)

print(f"Status: {response.status}")
print(f"Response: {response.response}")
```

## Complete Example

```python
import asyncio
from a2a_sdk import RegistryClient, A2AClient, A2AConfig

async def main():
    # Initialize registry client
    registry = RegistryClient(registry_url="http://localhost:9000")

    # Register supervisor agent
    registration = await registry.register(
        agent_name="SupervisorAgent",
        agent_type="supervisor",
        capabilities=["intent.classify"],
        endpoints={
            "http": "http://localhost:8080",
            "health": "http://localhost:8080/health",
            "a2a": "http://localhost:8080/a2a/invoke"
        }
    )

    # Create A2A client
    a2a_client = A2AClient(
        agent_id=registration["agent_id"],
        agent_name="SupervisorAgent",
        registry_client=registry
    )

    try:
        # Call account agent
        response = await a2a_client.send_message(
            target_capability="account.balance",
            intent="account.get_balance",
            payload={"customer_id": "CUST-001"}
        )

        if response.status == "success":
            print("Balance:", response.response.get("balance"))
        else:
            print("Error:", response.error)

    finally:
        # Cleanup
        await a2a_client.close()
        await registry.deregister(registration["agent_id"])

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### A2AConfig Options

```python
A2AConfig(
    timeout_seconds=30,              # Request timeout
    max_retries=3,                   # Max retry attempts
    retry_backoff_seconds=2,         # Base backoff time
    circuit_breaker_threshold=5,     # Failures before opening circuit
    circuit_breaker_timeout_seconds=60,  # Circuit reset timeout
    enable_tracing=True              # Enable distributed tracing
)
```

## Message Format

### A2A Request
```python
{
    "message_id": "msg-abc123",
    "protocol_version": "1.0",
    "timestamp": "2025-11-07T10:00:00Z",
    "source": {
        "agent_id": "supervisor-001",
        "agent_name": "SupervisorAgent"
    },
    "target": {
        "agent_id": "account-001",
        "agent_name": "AccountAgent"
    },
    "intent": "account.get_balance",
    "payload": {
        "customer_id": "CUST-001"
    },
    "metadata": {
        "timeout_seconds": 30,
        "trace_id": "trace-xyz"
    }
}
```

### A2A Response
```python
{
    "message_id": "msg-def456",
    "correlation_id": "msg-abc123",
    "status": "success",
    "response": {
        "balance": 99650.00,
        "currency": "THB"
    },
    "metadata": {
        "processing_time_ms": 245
    }
}
```

## Circuit Breaker

The circuit breaker protects against cascading failures:

```python
from a2a_sdk import CircuitBreaker

circuit_breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    timeout_seconds=60,       # Wait 60s before retry
    half_open_max_calls=1     # Test with 1 call when half-open
)

# Check if can execute
if circuit_breaker.can_execute():
    try:
        result = await call_service()
        circuit_breaker.record_success()
    except Exception:
        circuit_breaker.record_failure()
```

## Distributed Tracing

Enable OpenTelemetry tracing:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

# Setup tracer
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(
    SimpleSpanProcessor(ConsoleSpanExporter())
)

# A2A calls are automatically traced
response = await a2a_client.send_message(
    target_capability="account.balance",
    intent="account.get_balance",
    payload={"customer_id": "CUST-001"},
    trace_id="custom-trace-id",  # Optional
    span_id="custom-span-id"     # Optional
)
```

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html
```

## License

Copyright © 2025 BankX
