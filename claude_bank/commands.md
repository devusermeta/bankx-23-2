# BankX Services Startup Commands

## 🐳 Docker (Recommended - All Services Together)

### Quick Start
```powershell
# Start all services
docker-compose -f docker-compose.backend.yml up -d

# Check status
docker ps --format "table {{.Names}}\t{{.Status}}"

# View logs
docker-compose -f docker-compose.backend.yml logs -f

# Stop all services
docker-compose -f docker-compose.backend.yml down
```

### First Time Setup
```powershell
# 1. Copy environment file
Copy-Item envsample.env .env

# 2. Edit .env with your Azure credentials
notepad .env

# 3. Build images
docker-compose -f docker-compose.backend.yml build

# 4. Start services
docker-compose -f docker-compose.backend.yml up -d
```

### Service Management
```powershell
# Restart all services
docker-compose -f docker-compose.backend.yml restart

# Restart specific service
docker-compose -f docker-compose.backend.yml restart copilot

# View specific service logs
docker logs bankx-copilot --tail 50

# Update after code changes
docker-compose -f docker-compose.backend.yml build
docker-compose -f docker-compose.backend.yml up -d --force-recreate
```

**See:** `DOCKER_QUICKSTART.md` for quick reference | `DOCKER_DEPLOYMENT.md` for full guide

---

## 🎫 Quick Start: Escalation Agent A2A Flow (UC4)

### Required Services (Start in order):
```powershell
# 1. Escalation Comms MCP Server (Port 8078) - Ticket management + Email
cd claude_bank\app/business-api/python/escalation_comms; .\.venv\Scripts\Activate.ps1;$env:PROFILE="dev"; python main.py

# 2. Escalation Agent A2A (Port 9006) - Foundry Agent with A2A protocol
cd claude_bank\app/agents/escalation-agent-a2a; uv run --prerelease=allow python main.py

# 3. Copilot Backend (Port 8080) - Must have ENABLE_A2A_ESCALATION=True
cd claude_bank\app\copilot;$env:PROFILE="dev";uv run --prerelease=allow uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Test Flow:
1. Ask Product Info/AI Coach a question they can't answer
2. Agent offers to create ticket → Click "Confirm"
3. Email sent to customer + CC: `purohitabhinav2001@gmail.com`
4. Check Agent System Map for Escalation Agent highlight 🎫

---

## DOCKER IMAGE MAKING:
docker-compose -f docker-compose.backend.yml up -d; docker-compose up -d

## 💻 Local Development (Individual Services)

### ⚡ Recommended Startup Order (A2A Mode)
```powershell
# 1. Start MCP Services first (ports 8070-8078)
# 2. Start A2A Specialist Agents (ports 9001-9006)
# 3. Start Copilot Backend (port 8080) - will route to A2A agents
# 4. Start Frontend (port 8081)
```

### MCP Services (FastMCP - use python main.py)

### Account Service (Port 8070)
cd claude_bank\app\business-api\python\account;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";python main.py

### Transaction Service (Port 8071)
cd claude_bank\app\business-api\python\transaction;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";python main.py

### Payment Service (Port 8072)
cd claude_bank\app\business-api\python\payment;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";$env:TRANSACTIONS_API_URL="http://localhost:8071";python main.py

### Limits Service (Port 8073)
cd claude_bank\app\business-api\python\limits;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";python main.py

### Contacts Service (Port 8074)
cd claude_bank\app\business-api\python\contacts;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";python main.py

### Audit Service (Port 8075)
cd claude_bank\app\business-api\python\audit;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";python main.py

### Prodinfo Service (Port 8076)
cd claude_bank\app/business-api/python/prodinfo_faq; .\.venv\Scripts\Activate.ps1; $env:PROFILE="dev"; python main.py

### AI money coach Service (Port 8077)
cd claude_bank\app/business-api/python/ai_money_coach; .\.venv\Scripts\Activate.ps1;$env:PROFILE="dev"; python main.py

### EscalationComms Service (Port 8078)
cd claude_bank\app/business-api/python/escalation_comms; .\.venv\Scripts\Activate.ps1;$env:PROFILE="dev"; python main.py

### Cache Service (Port 8079)
cd claude_bank\app\business-api\python\cache;.venv\Scripts\Activate.ps1;$env:PROFILE="dev";python main.py

---

## A2A Specialist Agents (Standalone - Required for A2A Mode)

### Account Agent A2A Service (Port 9001) - PHASE 1 A2A MIGRATION
cd claude_bank\app/agents/account-agent-a2a; uv run --prerelease=allow python main.py

### Transaction Agent A2A Service (Port 9002) - UC1 A2A MIGRATION
cd claude_bank\app/agents/transaction-agent-a2a; uv run --prerelease=allow python main.py

### Payment Agent A2A Service (Port 9003) - UC1 A2A MIGRATION
cd claude_bank\app/agents/payment-agent-a2a; uv run --prerelease=allow python main.py

### ProdInfo FAQ Agent A2A Service (Port 9004) - UC2 A2A MIGRATION
cd claude_bank\app/agents/prodinfo-faq-agent-a2a; uv run --prerelease=allow python main.py

### AI Money Coach Agent A2A Service (Port 9005) - UC3 A2A MIGRATION
cd claude_bank\app/agents/ai-money-coach-agent-a2a; uv run --prerelease=allow python main.py

### Escalation Agent A2A Service (Port 9006) - UC4 A2A MIGRATION
cd claude_bank\app/agents/escalation-agent-a2a; uv run --prerelease=allow python main.py

---

## Copilot Backend (FastAPI - Orchestrates agents in A2A mode)

### Copilot Backend (Port 8080) - A2A Mode Enabled
cd claude_bank\app\copilot;$env:PROFILE="dev";uv run --prerelease=allow uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

---

## Frontend (Vite - has auto-reload built-in)

### Frontend (Port 8081)
cd claude_bank\app\frontend;npm run dev

---

## Notes:
- **MCP Services**: Use `python main.py` (FastMCP has built-in server, no uvicorn)
- **A2A Agents**: Use `uv run --prerelease=allow python main.py` for consistency
- **Copilot Backend**: Uses `uv run` with `--prerelease=allow` flag
- **Frontend**: Vite has HMR (Hot Module Replacement) built-in
- **Startup Order**: MCP servers → A2A agents → Copilot → Frontend
- **A2A Mode**: Copilot routes to standalone A2A agents (ports 9001-9006)
- **To reload MCP services**: You need to manually restart them (Ctrl+C and re-run)


cd app/business-api/python/prodinfo_faq; uv venv; .\.venv\Scripts\Activate.ps1; uv sync --prerelease=allow; $env:PROFILE="dev"; python main.py




az ad user create --display-name "Anan Chaiyaporn" --user-principal-name "anan@bankxthb.onmicrosoft.com" --password "BankX2025!Ch41" --force-change-password-next-sign-in false --output json
az ad user create --display-name "Pimchanok Thongchai" --user-principal-name "pimchanok@bankxthb.onmicrosoft.com" --password "BankX2025!Pim" --force-change-password-next-sign-in false --output json