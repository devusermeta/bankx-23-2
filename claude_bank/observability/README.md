# Local Observability Logs

This directory contains local JSON logs for debugging and reference purposes. These logs complement Application Insights telemetry.

## 📁 Log Files

Daily log files are created automatically:

- **`user_messages_YYYY-MM-DD.json`** - ALL user queries (including follow-ups that don't trigger routing) ⭐ NEW
- **`agent_decisions_YYYY-MM-DD.json`** - Agent routing decisions (when specialist agents are invoked)
- **`triage_rules_YYYY-MM-DD.json`** - Triage rule matches that determine agent routing
- **`errors_YYYY-MM-DD.json`** - All errors and exceptions

## 📄 File Format

All logs use **NDJSON** (newline-delimited JSON) format - one JSON object per line:

```json
{"timestamp": "2025-11-11T14:23:10.123456", "agent_name": "AccountAgent", "user_query": "What is my balance?", ...}
{"timestamp": "2025-11-11T14:25:30.555555", "agent_name": "TransactionAgent", "user_query": "Show transactions", ...}
```

### Why NDJSON?
- ✅ Easy to append (no need to parse entire file)
- ✅ Easy to search with `grep`, `findstr`, or PowerShell
- ✅ No corruption if app crashes mid-write
- ✅ Can process line-by-line with standard tools

## 🔍 How to Use

### View Today's Agent Decisions
```powershell
# PowerShell
Get-Content observability/agent_decisions_2025-11-11.json | ConvertFrom-Json | Format-Table timestamp, agent_name, triage_rule, duration_seconds
```

```bash
# Linux/Mac
cat observability/agent_decisions_2025-11-11.json | jq '.agent_name, .triage_rule, .duration_seconds'
```

### Search for Specific Agent
```powershell
# PowerShell - Find all AccountAgent decisions
Select-String -Path observability/agent_decisions_*.json -Pattern "AccountAgent"
```

```bash
# Linux/Mac
grep "AccountAgent" observability/agent_decisions_*.json
```

### View All Errors
```powershell
# PowerShell - Pretty print today's errors
Get-Content observability/errors_2025-11-11.json | ConvertFrom-Json | Format-List
```

### Count Triage Rules
```powershell
# PowerShell - Count how many times each rule matched
$rules = Get-Content observability/triage_rules_*.json | ConvertFrom-Json
$rules | Group-Object rule_name | Select-Object Name, Count | Sort-Object Count -Descending
```

## 🧹 Cleanup

Delete old logs manually or use the cleanup script:

```powershell
# Delete logs older than 1 day (default)
python observability/cleanup_logs.py

# Delete logs older than 7 days
python observability/cleanup_logs.py --days 7

# Dry run (see what would be deleted without actually deleting)
python observability/cleanup_logs.py --dry-run
```

## 🔐 Security Notes

- ⚠️ **DO NOT COMMIT** these logs to Git (already in `.gitignore`)
- 🔒 Logs may contain sensitive data (user queries, account info)
- 🗑️ Delete logs after debugging (run cleanup daily)
- 📋 For compliance audit, use Application Insights (retained securely)

## 📊 Log Contents

### agent_decisions_*.json
```json
{
  "timestamp": "2025-11-11T14:23:10.123456",
  "agent_name": "AccountAgent",
  "thread_id": "thread_xyz",
  "user_query": "What is my balance?",
  "triage_rule": "UC1_ACCOUNT_BALANCE",
  "reasoning": "User query classified as account-related: balance_inquiry",
  "tools_considered": ["get_accounts"],
  "tools_invoked": [{"tool": "get_accounts", "parameters": {"user": "alice"}}],
  "result_status": "success",
  "result_summary": "Response length: 150 chars",
  "context": {"use_case": "UC1"},
  "duration_seconds": 1.243,
  "message_type": "inquiry"
}
```

### triage_rules_*.json
```json
{
  "timestamp": "2025-11-11T14:23:10.098765",
  "rule_name": "UC1_ACCOUNT_BALANCE",
  "target_agent": "AccountAgent",
  "user_query": "What is my balance?",
  "confidence": 1.0
}
```

### errors_*.json
```json
{
  "timestamp": "2025-11-11T14:25:30.555555",
  "error_type": "AgentDecisionError",
  "agent_name": "PaymentAgent",
  "error_message": "Failed to connect to payment MCP",
  "user_query": "Pay 1000 THB to Bob",
  "thread_id": "thread_abc"
}
```

## 🔄 Dual Telemetry Architecture

```
User Query
    ↓
Agent Decision
    ↓
    ├─→ Application Insights (Cloud) ✅
    │   - Dashboards, alerts, analytics
    │   - 2-3 minute ingestion delay
    │   - Secure retention
    │
    └─→ Local JSON Logs (Filesystem) ✅
        - Instant access for debugging
        - No network dependency
        - Manual cleanup required
```

## 💡 Tips

1. **Check logs first** for fast debugging (no Azure Portal login needed)
2. **Use grep/Select-String** for quick searches
3. **Run cleanup daily** to avoid disk space issues
4. **Keep 1 day** of logs for development
5. **Use Application Insights** for production monitoring and long-term analysis

## 🆘 Troubleshooting

### No log files created?
- Check that `observability/` directory exists
- Verify Copilot is running and processing queries
- Check file permissions (should auto-create)

### Log files too large?
- Run `cleanup_logs.py` to delete old files
- Reduce `days_to_keep` parameter
- Consider filtering what gets logged

### Can't read JSON?
- Files are NDJSON (one object per line)
- Use `ConvertFrom-Json` (PowerShell) or `jq` (Linux/Mac)
- Don't try to parse as single JSON array

## 📚 Related Documentation

- [Application Insights Queries](../docs/OBSERVABILITY.md) - KQL queries for cloud telemetry
- [Agent Framework Observability](https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-observability) - Microsoft docs
- [Triage Rules Reference](../app/copilot/app/agents/foundry/supervisor_agent_foundry.py) - See `_determine_triage_rule()` method

---

**Last Updated:** November 11, 2025
