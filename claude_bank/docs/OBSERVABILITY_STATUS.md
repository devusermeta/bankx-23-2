# MCP Observability Implementation Status

## Overview
Comprehensive OpenTelemetry + Application Insights observability for all 8 MCP servers.

## Completed Work

### ✅ Task 1: Shared Observability Module (COMPLETED)

**File:** `app/common/observability/mcp_observability.py` (340 lines)

**Functions:**
- `setup_mcp_observability(service_name, port, service_description)`: Initialize App Insights for MCP server
- `trace_mcp_tool(tool_name, query, additional_attributes)`: Context manager for distributed tracing
- `instrument_mcp_tool(func)`: Decorator for automatic function instrumentation
- `log_custom_event(event_name, properties, measurements)`: Custom business intelligence events
- `should_redact()`, `redact_if_needed()`: Environment-aware sensitive data handling

**MCPMetrics Class:**
- Counters: `tool_invocations`, `tool_errors`, `azure_api_calls`
- Histograms: `tool_duration`, `search_latency`, `embedding_latency`, `cost_tracker`
- Methods: `record_tool_invocation()`, `record_search_query()`, `record_embedding_generation()`, `record_cost()`

**Exports:** Updated `app/common/observability/__init__.py` to export all MCP functions

---

### ✅ Task 2: UC3 (AIMoneyCoach) Observability (COMPLETED)

**Modified Files:**

1. **`app/business-api/python/ai_money_coach/main.py`**
   - Added sys.path setup for common imports
   - Imported `setup_mcp_observability`, `MCPMetrics`
   - Called `setup_mcp_observability("ai-money-coach", port=8077)` after FastMCP init
   - Created global `metrics` instance

2. **`app/business-api/python/ai_money_coach/services.py`**
   - Added `get_metrics()` function for module-level metrics instance
   - **`get_embedding()`**: Tracks embedding generation duration, token count, cost ($0.13/1M tokens for text-embedding-3-large)
   - **`search_money_coach_content()`**: Tracks search latency, result count, Azure AI Search cost ($5/1000 queries)

3. **`app/business-api/python/ai_money_coach/mcp_tools.py`**
   - Added `trace_mcp_tool` context manager to `ai_search_rag_results` tool
   - Added `trace_mcp_tool` context manager to `ai_foundry_content_understanding` tool
   - Added custom event `uc3_search_completed` with properties (query, result_count, top_chapter) and measurements (confidence)

**Metrics Tracked:**
- ✅ Tool invocation count and duration (both tools)
- ✅ Search latency (hybrid search: text + vector)
- ✅ Embedding generation time and token count
- ✅ OpenAI API cost (embeddings: $0.13/1M tokens)
- ✅ Azure AI Search cost (search: $5/1000 queries)
- ✅ Search result count and confidence scores
- ✅ Custom event: uc3_search_completed

**Distributed Tracing:**
- ✅ Spans created for tool invocations (ai_search_rag_results, ai_foundry_content_understanding)
- ✅ Attributes: tool_name, query, chapter_filter, top_k, use_case (UC3), content_understanding_enabled
- ✅ Duration tracking with automatic error capture

---

### 🔄 Task 3: UC2 (ProdInfoFAQ) Observability (50% COMPLETED)

**Modified Files:**

1. **`app/business-api/python/prodinfo_faq/main.py`** ✅
   - Added sys.path setup for common imports
   - Imported `setup_mcp_observability`, `MCPMetrics`
   - Called `setup_mcp_observability("prodinfo-faq", port=8076)` after FastMCP init
   - Created global `metrics` instance

**Still TODO:**
- ⏳ Add metrics tracking to `services.py` (search, CosmosDB operations)
- ⏳ Add distributed tracing to `mcp_tools.py` (search_documents, get_content_understanding, write_to_cosmosdb)
- ⏳ Add custom events (ticket_created, grounding_validation)

---

### ⏳ Task 4: UC1 MCP Servers (6 servers) - NOT STARTED

**Servers to Instrument:**
1. Account (port 8070) - account operations, balance queries
2. Transaction (port 8071) - transaction retrieval, filtering
3. Payment (port 8072) - payment processing, validation
4. Limits (port 8073) - limit checks
5. Contacts (port 8074) - contact lookups
6. Audit (port 8075) - audit log writes

**Pattern to Apply (same as UC3):**
- Add sys.path + import observability to main.py
- Call `setup_mcp_observability(service_name, port)` in main.py
- Add metrics tracking to services.py (tool-specific operations)
- Add `trace_mcp_tool` to mcp_tools.py for all tools

---

### ⏳ Task 5: Application Insights Dashboards - NOT STARTED

**Unified Dashboard** (All Use Cases):
- System Health: 8 MCP server status (requests, errors, latency)
- Agent Usage: UC1 vs UC2 vs UC3 request distribution
- Performance: P50/P95/P99 latencies per server
- Error Rates: Last 24h error trends
- Cost Tracking: OpenAI tokens, Azure AI Search RUs

**UC1 Dashboard** (Financial Operations):
- 6 MCP servers breakdown
- Operation types (balance, transaction, payment, limits, contacts, audit)
- Success rates per operation

**UC2 Dashboard** (Product Info & Search):
- Search latency (uc2_docs index)
- Grounding validation success rate
- Ticket creation events
- Content Understanding fallback usage

**UC3 Dashboard** (AI Money Coach & Multimodal):
- Hybrid search performance (text vs vector vs combined)
- Embedding generation time
- Vector similarity score distribution
- Most common financial topics

---

### ⏳ Task 6: Alerts Configuration - NOT STARTED

**Critical Alerts:**
1. **MCP Server Down**: No requests for 2 minutes on any port 8070-8077 (Severity: Critical)
2. **High Error Rate**: Error rate > 5% for 5 minutes (Severity: High)
3. **Slow Response**: P95 latency > 1 second for 5 minutes (Severity: Medium)
4. **Azure AI Search Throttling**: 503 errors from Azure AI Search (Severity: High)
5. **OpenAI Rate Limit**: 429 errors from OpenAI API (Severity: High)
6. **Cost Threshold**: Daily cost exceeds threshold (Severity: Medium)

---

### ⏳ Task 7: End-to-End Testing - NOT STARTED

**Test Plan:**
1. Start all 8 MCP servers
2. Run test queries for each use case:
   - UC1: Balance query, transaction history, payment, limit check, contact lookup, audit log
   - UC2: Product info search, ticket creation
   - UC3: Financial coaching query
3. Verify telemetry in Azure Portal:
   - Live Metrics: Real-time request count, latency
   - Traces: Distributed calls (Copilot → Agent → MCP → Azure)
   - Metrics: Tool invocations, search latency, costs
   - Custom Events: Tickets, searches, debt plans
4. Trigger alerts (stop MCP server, verify notification)

---

### ⏳ Task 8: Documentation - NOT STARTED

**`docs/OBSERVABILITY.md`** (To Create):
- How to view dashboards in Azure Portal
- How to interpret metrics
- How to respond to alerts
- How to add observability to new MCP servers
- Cost estimation formulas
- Troubleshooting common issues

**README.md Update:**
- Add observability section with links

---

## Testing

### Test Script Created

**`scripts/test_uc3_observability.py`** ✅
- Tests UC3 MCP server connectivity
- Sends test query: "How much should I save for emergency fund?"
- Waits 10 seconds for telemetry propagation
- Provides Azure Portal KQL queries to verify:
  - Traces with `service_name == 'ai-money-coach'`
  - Custom events: `uc3_search_completed`
  - Metrics: `mcp.*` counters and histograms

**To Run:**
```powershell
python scripts\test_uc3_observability.py
```

**Expected Output:**
- ✅ UC3 server connectivity
- ✅ Search query returns results
- ✅ InstrumentationKey displayed
- 📊 Azure Portal links and KQL queries provided

---

## Next Steps (Priority Order)

1. **IMMEDIATE**: Complete UC2 observability
   - Add metrics to `prodinfo_faq/services.py`
   - Add tracing to `prodinfo_faq/mcp_tools.py`
   - Test UC2 with `scripts/test_uc2_observability.py` (to create)

2. **HIGH**: Instrument 6 UC1 MCP servers
   - Apply same pattern to all 6 servers (Account, Transaction, Payment, Limits, Contacts, Audit)
   - Test each server

3. **MEDIUM**: Create dashboards in Azure Portal
   - Unified dashboard (all 8 servers)
   - UC1 detailed dashboard
   - UC2 detailed dashboard
   - UC3 detailed dashboard

4. **HIGH**: Configure alerts
   - Server down alerts
   - High error rate alerts
   - Slow response alerts
   - Azure service throttling alerts
   - Cost threshold alerts

5. **HIGH**: End-to-end testing
   - Test all 8 servers
   - Verify all telemetry flowing
   - Validate dashboards
   - Test alert triggering

6. **LOW**: Documentation
   - Create `docs/OBSERVABILITY.md`
   - Update README.md

---

## Verification Checklist

### UC3 (AIMoneyCoach)
- [x] main.py: setup_mcp_observability() called
- [x] services.py: Embedding metrics (duration, tokens, cost)
- [x] services.py: Search metrics (latency, result count, cost)
- [x] mcp_tools.py: Distributed tracing (ai_search_rag_results)
- [x] mcp_tools.py: Distributed tracing (ai_foundry_content_understanding)
- [x] mcp_tools.py: Custom event (uc3_search_completed)
- [x] Test script created (test_uc3_observability.py)

### UC2 (ProdInfoFAQ)
- [x] main.py: setup_mcp_observability() called
- [ ] services.py: Search metrics
- [ ] services.py: CosmosDB metrics
- [ ] mcp_tools.py: Distributed tracing (search_documents)
- [ ] mcp_tools.py: Distributed tracing (get_content_understanding)
- [ ] mcp_tools.py: Distributed tracing (write_to_cosmosdb)
- [ ] mcp_tools.py: Custom events (ticket_created, grounding_validation)
- [ ] Test script created

### UC1 (6 servers)
- [ ] All 6 servers: main.py instrumented
- [ ] All 6 servers: services.py metrics
- [ ] All 6 servers: mcp_tools.py tracing
- [ ] Test scripts created

### Infrastructure
- [x] Shared module created (mcp_observability.py)
- [x] Shared module exported (__init__.py)
- [x] Verification scripts passed (verify_config, verify_observability, verify_content_understanding)
- [ ] Unified dashboard created
- [ ] UC1 dashboard created
- [ ] UC2 dashboard created
- [ ] UC3 dashboard created
- [ ] Alerts configured
- [ ] Documentation created

---

## Telemetry Schema

### Traces (Distributed Tracing)
```
traces
├── service_name: "ai-money-coach", "prodinfo-faq", "account", etc.
├── tool_name: "ai_search_rag_results", "search_documents", etc.
├── query: User's search query
├── duration_ms: Tool execution time
├── use_case: "UC1", "UC2", "UC3"
└── additional_attributes: Tool-specific metadata
```

### Metrics
```
customMetrics
├── mcp.tool.invocations (Counter)
├── mcp.tool.errors (Counter)
├── mcp.azure_api.calls (Counter)
├── mcp.tool.duration (Histogram, ms)
├── mcp.search.latency (Histogram, ms)
├── mcp.embedding.latency (Histogram, ms)
└── mcp.cost (Histogram, USD)
```

### Custom Events
```
customEvents
├── uc3_search_completed
│   ├── properties: {query, result_count, top_chapter}
│   └── measurements: {confidence}
├── ticket_created (UC2)
│   ├── properties: {category, priority, ticket_id}
│   └── measurements: {-}
├── debt_plan_generated (UC3)
│   ├── properties: {user_id, plan_type}
│   └── measurements: {total_debt}
└── payment_processed (UC1)
    ├── properties: {payment_id, status}
    └── measurements: {amount}
```

---

## Cost Tracking

### Per Service Costs
- **OpenAI Embeddings**: $0.13 per 1M tokens (text-embedding-3-large)
- **OpenAI Chat**: $0.15 per 1M input tokens, $0.60 per 1M output tokens (gpt-4.1-mini)
- **Azure AI Search**: ~$5 per 1000 queries (estimate)
- **Application Insights**: $2.30 per GB ingested

### Cost Estimation Formulas
```python
# Embedding cost
tokens = len(text) // 4  # Rough estimate
cost_usd = (tokens / 1_000_000) * 0.13

# Search cost
cost_per_query = 0.005  # $5 / 1000 queries

# Total daily cost
SELECT SUM(cost_usd) FROM customMetrics WHERE name = 'mcp.cost'
```

---

## Environment-Aware Logging

- **Development** (`PROFILE=dev`): Full logging, no redaction
- **Production** (`PROFILE=prod`): Redacted logging (PII masked)

```python
if should_redact():
    query = redact_if_needed(query, ["query", "user_id"])
```

---

## Summary

**Completed:** 2.5 / 8 tasks (31%)
- ✅ Shared observability module (100%)
- ✅ UC3 observability (100%)
- 🔄 UC2 observability (50%)

**Remaining:** 5.5 tasks
- ⏳ UC2 completion (50%)
- ⏳ UC1 6 servers (0%)
- ⏳ Dashboards (0%)
- ⏳ Alerts (0%)
- ⏳ Testing (0%)
- ⏳ Documentation (0%)

**Estimated Time:**
- UC2 completion: 15 minutes
- UC1 6 servers: 90 minutes (15 min × 6)
- Dashboards: 30 minutes
- Alerts: 20 minutes
- Testing: 30 minutes
- Documentation: 15 minutes
**Total remaining: ~3 hours**

---

Last Updated: 2024
Status: Work in Progress
