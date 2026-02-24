"""
Payment Agent V3 Handler - Azure AI Foundry with Agent Framework

2-tool flow:
  1. prepareTransfer  → validates + returns all confirmation data (READ-ONLY)
  2. executeTransfer  → executes AFTER user says yes (WRITE)
"""

import logging
from typing import AsyncGenerator

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

from audited_mcp_tool import AuditedMCPTool
from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    PAYMENT_AGENT_NAME,
    PAYMENT_AGENT_VERSION,
    PAYMENT_AGENT_MODEL_DEPLOYMENT,
    PAYMENT_UNIFIED_MCP_URL,
    PAYMENT_AGENT_CONFIG,
)

logger = logging.getLogger(__name__)


class PaymentAgentV3Handler:
    """
    Payment Agent V3 Handler using Agent Framework with Azure AI Foundry.

    2-tool design:
    - prepareTransfer  : READ-ONLY, safe to auto-approve - validates and returns preview data
    - executeTransfer  : WRITE, requires explicit user approval - moves real money
    """

    # Class-level in-memory cache (fast access within a single process run)
    _thread_cache: dict[str, dict] = {}

    # File-backed store path — persists across watchfiles reloads
    _STORE_PATH = "thread_state.json"

    @classmethod
    def _load_thread_state(cls, thread_id: str) -> dict:
        """Load thread state from JSON file (fallback to in-memory cache)."""
        # Check memory cache first
        if thread_id in cls._thread_cache:
            return dict(cls._thread_cache[thread_id])
        # Try disk
        import json, os
        if os.path.exists(cls._STORE_PATH):
            try:
                with open(cls._STORE_PATH, "r", encoding="utf-8") as f:
                    store = json.load(f)
                if thread_id in store:
                    cls._thread_cache[thread_id] = store[thread_id]
                    return dict(store[thread_id])
            except Exception as e:
                logger.warning(f"[THREAD STORE] Failed to read {cls._STORE_PATH}: {e}")
        return {}

    @classmethod
    def _save_thread_state(cls, thread_id: str, state: dict) -> None:
        """Save thread state to JSON file and in-memory cache."""
        import json, os
        # Persist only JSON-serialisable parts (skip agent_thread bytes)
        import copy
        serialisable = {}
        for k, v in state.items():
            if k == "agent_thread":
                continue  # not needed across reloads — a fresh thread is fine
            try:
                json.dumps(v)
                serialisable[k] = v
            except (TypeError, ValueError):
                pass
        cls._thread_cache[thread_id] = state  # keep full state in memory
        # Read → merge → write
        store = {}
        if os.path.exists(cls._STORE_PATH):
            try:
                with open(cls._STORE_PATH, "r", encoding="utf-8") as f:
                    store = json.load(f)
            except Exception:
                store = {}
        store[thread_id] = serialisable
        try:
            with open(cls._STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(store, f, indent=2)
        except Exception as e:
            logger.warning(f"[THREAD STORE] Failed to write {cls._STORE_PATH}: {e}")

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        self.project_client = None

        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}

        # MCP tool caching (shared across threads)
        self._mcp_tools_cache: list | None = None

        logger.info("PaymentAgentV3Handler initialized")

    async def initialize(self):
        """Initialize Azure AI resources"""
        self.credential = AzureCliCredential()

        self.project_client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=self.credential
        )

        # Load instructions from prompts file
        with open("prompts/payment_agent.md", "r", encoding="utf-8") as f:
            self.instructions = f.read()

        logger.info("✅ PaymentAgentV3Handler initialized (credential + client + instructions loaded)")

    async def _create_mcp_tools(self, customer_id: str | None = None, thread_id: str | None = None) -> list:
        """Create MCP tool connection to payment-unified MCP server"""
        logger.info(f"Creating payment MCP connection for thread={thread_id}")

        payment_mcp_tool = AuditedMCPTool(
            name="Payment MCP Server",
            url=PAYMENT_UNIFIED_MCP_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="payment",
            headers={},
            description="Execute bank transfers using prepareTransfer and executeTransfer tools",
            # Override Foundry portal "Always approval all tools" — human confirmation is already
            # handled in Python (Turn 1 HTML table + Turn 2 "yes" confirmation). The Foundry-level
            # approval gate causes the LLM to hallucinate results because run_stream does not
            # handle the requires_action event. Setting never_require bypasses it cleanly.
            approval_mode="never_require",
        )
        await payment_mcp_tool.connect()

        logger.info("✅ Payment MCP connection established")
        return [payment_mcp_tool]

    async def _get_user_email(self, customer_id: str) -> str:
        """Get user email from customer_id"""
        try:
            import sys
            from pathlib import Path

            copilot_path = Path(__file__).parent.parent.parent / "copilot"
            if str(copilot_path) not in sys.path:
                sys.path.insert(0, str(copilot_path))

            from app.auth.user_mapper import get_user_mapper

            user_mapper = get_user_mapper()
            customer_info = user_mapper.get_customer_info(customer_id)

            if customer_info:
                user_mail = customer_info.get("bankx_email") or customer_info.get("email")
                logger.info(f"📧 [UserMapper] {customer_id} → {user_mail}")
                return user_mail
        except Exception as e:
            logger.warning(f"⚠️ [UserMapper] Error: {e}, using fallback")

        # Fallback static mapping
        customer_email_map = {
            "CUST-001": "somchai@bankxthb.onmicrosoft.com",
            "CUST-002": "nattaporn@bankxthb.onmicrosoft.com",
            "CUST-003": "pimchanok@bankxthb.onmicrosoft.com",
            "CUST-004": "anan@bankxthb.onmicrosoft.com",
        }
        user_mail = customer_email_map.get(customer_id, "somchai@bankxthb.onmicrosoft.com")
        logger.info(f"📧 [Fallback] {customer_id} → {user_mail}")
        return user_mail

    async def get_agent(self, thread_id: str, customer_id: str) -> ChatAgent:
        """Get or create ChatAgent for this thread"""
        if thread_id in self._cached_agents:
            logger.info(f"⚡ [CACHE HIT] Reusing cached PaymentAgentV3 for thread={thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"Building new PaymentAgentV3 for thread={thread_id}, customer={customer_id}")

        # Reuse MCP tools if already created
        if self._mcp_tools_cache is None:
            logger.info("🔧 [MCP INIT] Creating MCP connection (first time)...")
            self._mcp_tools_cache = await self._create_mcp_tools(customer_id=customer_id, thread_id=thread_id)
            logger.info("✅ [MCP INIT] MCP connection created and cached")
        else:
            logger.info("⚡ [MCP CACHE] Reusing existing MCP connection")

        mcp_tools = self._mcp_tools_cache

        # Inject user email into instructions
        user_email = await self._get_user_email(customer_id)
        full_instructions = self.instructions.replace("{user_email}", user_email)

        # Reference the existing Foundry agent
        azure_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=PAYMENT_AGENT_NAME,
            agent_version=PAYMENT_AGENT_VERSION,
        )
        logger.info(f"✅ AzureAIClient referencing agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")

        chat_agent = azure_client.create_agent(
            name=PAYMENT_AGENT_NAME,
            tools=mcp_tools,
            instructions=full_instructions,
        )

        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 [CACHE STORED] PaymentAgentV3 cached for thread={thread_id}")

        return chat_agent

    def _is_confirmation(self, message: str) -> bool:
        """Check if the message is a user confirming a pending transfer."""
        msg = message.lower().strip()
        # Strip username prefix injected by copilot: "my username is <email>, <actual message>"
        if msg.startswith("my username is "):
            comma_idx = msg.find(", ", 15)
            if comma_idx != -1:
                msg = msg[comma_idx + 2:].strip()
        confirmation_phrases = [
            "yes", "confirm", "proceed", "ok", "okay", "sure",
            "yes confirm", "yes please", "go ahead", "do it", "approve",
            "yes, confirm", "yes,confirm"
        ]
        return any(msg == phrase or msg.startswith(phrase) for phrase in confirmation_phrases)

    def _parse_mcp_result(self, result) -> dict:
        """Parse MCP tool result into a dict regardless of format."""
        import json, ast
        logger.info(f"[MCP PARSE] Raw result type: {type(result)}, value: {repr(result)[:500]}")

        def try_parse(text: str) -> dict | None:
            """Try JSON first, then ast.literal_eval for Python dict strings."""
            if not text:
                return None
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            return None

        # Already a dict
        if isinstance(result, dict):
            return result

        # List of content objects (agent_framework._types.TextContent, etc.)
        if isinstance(result, list):
            for item in result:
                # Try .text attribute first
                text = getattr(item, 'text', None)
                logger.info(f"[MCP PARSE] Item .text value: {repr(text)[:500]}")
                if text:
                    parsed = try_parse(text)
                    if parsed:
                        logger.info(f"[MCP PARSE] Parsed from .text: {list(parsed.keys())}")
                        return parsed
                    logger.warning(f"[MCP PARSE] try_parse failed on .text: {repr(text)[:300]}")
                # Also try to_dict() if available
                if hasattr(item, 'to_dict'):
                    d = item.to_dict()
                    logger.info(f"[MCP PARSE] to_dict(): {repr(d)[:300]}")
                    if isinstance(d, dict) and d:
                        return d
                # Try raw_representation
                raw = getattr(item, 'raw_representation', None)
                if raw:
                    logger.info(f"[MCP PARSE] raw_representation: {repr(raw)[:300]}")
                    parsed = try_parse(str(raw))
                    if parsed:
                        return parsed
                # Try item itself if string
                if isinstance(item, str):
                    parsed = try_parse(item)
                    if parsed:
                        logger.info(f"[MCP PARSE] Parsed from string item: {list(parsed.keys())}")
                        return parsed
                logger.info(f"[MCP PARSE] Item repr: {repr(item)[:300]}")

        # Direct string
        if isinstance(result, str):
            parsed = try_parse(result)
            if parsed:
                return parsed

        # Object with .text
        text = getattr(result, 'text', None)
        if text:
            parsed = try_parse(text)
            if parsed:
                return parsed

        logger.warning(f"[MCP PARSE] Could not parse result, returning empty dict. Full repr: {repr(result)[:1000]}")
        return {}

    def _clear_session_cache(self, thread_id: str) -> None:
        """Clear cached MCP tools and agent for a thread (used on session errors)."""
        logger.warning(f"[SESSION] Clearing MCP + agent cache for thread={thread_id}")
        self._mcp_tools_cache = None
        if thread_id in self._cached_agents:
            del self._cached_agents[thread_id]

    async def _call_prepare_transfer(self, user_email: str, recipient: str, amount: float, thread_id: str, customer_id: str) -> dict:
        """Call prepareTransfer MCP tool directly — no LLM involved."""

        async def _do_call() -> list:
            if self._mcp_tools_cache is None:
                self._mcp_tools_cache = await self._create_mcp_tools(customer_id=customer_id, thread_id=thread_id)
            mcp_tool = self._mcp_tools_cache[0]
            logger.info(f"[DIRECT MCP] Calling prepareTransfer: username={user_email}, recipient={recipient}, amount={amount}")
            return await mcp_tool.call_tool(
                "prepareTransfer",
                username=user_email,
                recipient_identifier=recipient,
                amount=amount,
            )

        try:
            result = await _do_call()
        except Exception as e:
            if "session terminated" in str(e).lower():
                logger.warning(f"[DIRECT MCP] Session terminated — clearing cache and retrying (1/1)...")
                self._clear_session_cache(thread_id)
                result = await _do_call()  # retry once with fresh connection
            else:
                raise

        return self._parse_mcp_result(result)

    async def _call_execute_transfer(self, sender_account_id: str, recipient_account_id: str, amount: float, description: str, thread_id: str, customer_id: str) -> dict:
        """Call executeTransfer MCP tool directly — no LLM involved.

        Mirrors _call_prepare_transfer exactly. Bypasses the Foundry agent run entirely
        so approval_mode / requires_action can never block or hallucinate the result.
        """

        async def _do_call() -> list:
            if self._mcp_tools_cache is None:
                self._mcp_tools_cache = await self._create_mcp_tools(customer_id=customer_id, thread_id=thread_id)
            mcp_tool = self._mcp_tools_cache[0]
            logger.info(
                f"[DIRECT MCP] Calling executeTransfer: "
                f"sender={sender_account_id}, recipient={recipient_account_id}, "
                f"amount={amount}, description={description!r}"
            )
            return await mcp_tool.call_tool(
                "executeTransfer",
                sender_account_id=sender_account_id,
                recipient_account_id=recipient_account_id,
                amount=amount,
                description=description,
            )

        try:
            result = await _do_call()
        except Exception as e:
            if "session terminated" in str(e).lower():
                logger.warning(f"[DIRECT MCP executeTransfer] Session terminated — clearing cache and retrying (1/1)...")
                self._clear_session_cache(thread_id)
                result = await _do_call()
            else:
                raise

        return self._parse_mcp_result(result)

    def _format_transfer_success(self, result: dict, pending: dict) -> str:
        """Format executeTransfer result as a clean success message.

        executeTransfer returns:
          {"success": True, "transaction": {"transaction_id": "T000XXX", "sender_new_balance": ..., ...}}
        or on failure:
          {"success": False, "message": "..."}
        """
        # Check for error
        if not result.get("success", True):
            error_msg = result.get("message", "Unknown error")
            logger.error(f"[TURN 2] executeTransfer returned failure: {error_msg}")
            return f"❌ Transfer failed: {error_msg}"

        # Extract nested transaction object
        txn = result.get("transaction", result)  # fallback to top-level if no 'transaction' key
        txn_id = txn.get("transaction_id") or txn.get("txn_id") or result.get("transaction_id", "N/A")
        sender_new_balance = txn.get("sender_new_balance", 0)
        amount = pending.get("amount", 0)
        description = pending.get("description", "")
        # Extract recipient name from description ("Transfer to <name>")
        recipient = description.replace("Transfer to ", "").strip() if description.startswith("Transfer to ") else description

        return (
            f"✅ Transfer Successful!\n\n"
            f"**Transaction ID:** {txn_id}\n"
            f"**Amount:** {amount:,.2f} THB\n"
            f"**Recipient:** {recipient}\n"
            f"**New Balance:** {sender_new_balance:,.2f} THB\n\n"
            f"Your transfer has been processed successfully."
        )

    def _format_confirmation_table(self, data: dict) -> str:
        """Format the prepareTransfer result as an HTML confirmation table."""
        amount = data.get("amount", 0)
        currency = data.get("currency", "THB")
        recipient_name = data.get("recipient_name", "Unknown")
        recipient_account_no = data.get("recipient_account_no", "Unknown")
        payment_method = data.get("payment_method", "Bank Transfer")
        current_balance = data.get("current_balance", 0)
        new_balance_preview = data.get("new_balance_preview", 0)

        return (
            f"\u26a0\ufe0f PAYMENT CONFIRMATION REQUIRED \u26a0\ufe0f\n\n"
            f"Please confirm to proceed with this payment:\n\n"
            f"<table>\n"
            f"<tr><td><strong>Amount</strong></td><td>{amount:,.2f} {currency}</td></tr>\n"
            f"<tr><td><strong>Recipient</strong></td><td>{recipient_name}</td></tr>\n"
            f"<tr><td><strong>Account</strong></td><td>{recipient_account_no}</td></tr>\n"
            f"<tr><td><strong>Payment Method</strong></td><td>{payment_method}</td></tr>\n"
            f"<tr><td><strong>Current Balance</strong></td><td>{current_balance:,.2f} {currency}</td></tr>\n"
            f"<tr><td><strong>New Balance (Preview)</strong></td><td>{new_balance_preview:,.2f} {currency}</td></tr>\n"
            f"</table>\n\n"
            f"Reply 'Yes' or 'Confirm' to proceed with the payment."
        )

    async def process_message(
        self,
        message: str,
        thread_id: str,
        customer_id: str,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Process a payment message.

        Turn 1 — Transfer request:
          Python calls prepareTransfer MCP directly (no LLM tool calling).
          Formats HTML table in Python code. Stores pending transfer data.

        Turn 2 — Confirmation (user says "yes"):
          Passes stored transfer params explicitly to agent.
          Agent's only job: call executeTransfer with the provided IDs.
        """
        import time
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
        from a2a_banking_telemetry import get_a2a_telemetry

        start_time = time.time()
        logger.info(f"Processing message for thread={thread_id}, customer={customer_id}")
        telemetry = get_a2a_telemetry("PaymentAgentV3")

        full_response = ""

        try:
            thread_state = PaymentAgentV3Handler._load_thread_state(thread_id)
            pending = thread_state.get("pending_transfer")

            # ── TURN 2: User confirmed ────────────────────────────────────────────
            if pending and self._is_confirmation(message):
                logger.info(f"[TURN 2] Confirmation received — calling executeTransfer directly in Python")
                logger.info(f"[TURN 2] Params: {pending}")

                # Call executeTransfer directly — NO agent, NO LLM, NO hallucination possible.
                # Mirrors the same pattern used for prepareTransfer in Turn 1.
                execute_result = await self._call_execute_transfer(
                    sender_account_id=pending["sender_account_id"],
                    recipient_account_id=pending["recipient_account_id"],
                    amount=pending["amount"],
                    description=pending["description"],
                    thread_id=thread_id,
                    customer_id=customer_id,
                )

                logger.info(f"[TURN 2] executeTransfer result: {execute_result}")

                # Format a clean success response
                full_response = self._format_transfer_success(execute_result, pending)

                if stream:
                    yield full_response
                else:
                    yield full_response

                # Clear pending transfer — done
                thread_state.pop("pending_transfer", None)
                PaymentAgentV3Handler._save_thread_state(thread_id, thread_state)
                logger.info(f"[TURN 2] Transfer executed, pending cleared for thread={thread_id}")

            # ── TURN 1: Transfer request ──────────────────────────────────────────
            else:
                logger.info(f"[TURN 1] Transfer request — calling prepareTransfer directly in Python")

                user_email = await self._get_user_email(customer_id)

                # Ensure MCP is ready
                if self._mcp_tools_cache is None:
                    self._mcp_tools_cache = await self._create_mcp_tools(customer_id=customer_id, thread_id=thread_id)

                # Extract recipient and amount from message using regex — no LLM call, no hallucination
                import re
                recipient = "unknown"
                amount = 0.0

                # Pattern: "transfer <amount> [THB|baht] to <recipient>"
                # Also handles: "send <amount> to <recipient>"
                amt_match = re.search(r"(?:transfer|send)\s+(\d+(?:[.,]\d+)?)\s*(?:thb|baht)?", message, re.IGNORECASE)
                if amt_match:
                    amount = float(amt_match.group(1).replace(",", ""))
                else:
                    # Fallback: first number in message
                    amt_match2 = re.search(r"(\d+(?:\.\d+)?)", message)
                    if amt_match2:
                        amount = float(amt_match2.group(1))

                rec_match = re.search(r"\bto\s+([A-Za-z][A-Za-z\s]{2,}?)(?:\s*$|\s+\d|,)", message, re.IGNORECASE)
                if rec_match:
                    recipient = rec_match.group(1).strip()

                # Strip the username prefix if present ("my username is ..., transfer...")
                if recipient == "unknown" or amount == 0.0:
                    clean_msg = message
                    if clean_msg.lower().startswith("my username is "):
                        ci = clean_msg.find(", ", 15)
                        if ci != -1:
                            clean_msg = clean_msg[ci + 2:]
                    if amount == 0.0:
                        m = re.search(r"(\d+(?:\.\d+)?)", clean_msg)
                        if m:
                            amount = float(m.group(1))
                    if recipient == "unknown":
                        m2 = re.search(r"\bto\s+([A-Za-z][A-Za-z\s]{2,}?)(?:\s*$|\s+\d|,)", clean_msg, re.IGNORECASE)
                        if m2:
                            recipient = m2.group(1).strip()

                logger.info(f"[TURN 1] Extracted via regex: recipient={recipient!r}, amount={amount}")

                # Ensure agent is initialised (MCP connection needed for prepareTransfer)
                agent = await self.get_agent(thread_id=thread_id, customer_id=customer_id)

                # Call prepareTransfer directly — real data, no hallucination possible
                prepare_result = await self._call_prepare_transfer(
                    user_email=user_email,
                    recipient=recipient,
                    amount=amount,
                    thread_id=thread_id,
                    customer_id=customer_id,
                )

                logger.info(f"[TURN 1] prepareTransfer raw result keys: {list(prepare_result.keys())}")
                logger.info(f"[TURN 1] prepareTransfer result: {prepare_result}")

                if prepare_result.get("validation_status") == "error":
                    error_msg = prepare_result.get("error_message", "Transfer validation failed.")
                    full_response = f"Sorry, I couldn't process that transfer: {error_msg}"
                    yield full_response
                elif not prepare_result.get("sender_account_id") or not prepare_result.get("recipient_account_id"):
                    logger.error(f"[TURN 1] Missing account IDs in prepareTransfer result: {prepare_result}")
                    full_response = f"Sorry, I couldn't retrieve the account details. Please try again."
                    yield full_response
                else:
                    # Format table in Python — guaranteed real data
                    full_response = self._format_confirmation_table(prepare_result)

                    # Store pending transfer for Turn 2
                    thread_state["pending_transfer"] = {
                        "sender_account_id": prepare_result["sender_account_id"],
                        "recipient_account_id": prepare_result["recipient_account_id"],
                        "amount": prepare_result["amount"],
                        "description": f"Transfer to {prepare_result.get('recipient_name', recipient)}",
                    }
                    PaymentAgentV3Handler._save_thread_state(thread_id, thread_state)
                    logger.info(f"[TURN 1] Pending transfer stored for thread={thread_id}: {thread_state['pending_transfer']}")

                    if stream:
                        yield full_response
                    else:
                        yield full_response

            # Telemetry
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC2_PAYMENT_AGENT_V3",
                reasoning="Payment transfer handled by PaymentAgentV3 via A2A",
                tools_considered=["prepareTransfer", "executeTransfer"],
                tools_invoked=[{"tool": "payment_mcp", "status": "success"}],
                result_status="success",
                result_summary=f"Response generated ({len(full_response)} chars)",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a"}
            )
            telemetry.log_user_message(
                thread_id=thread_id,
                user_query=message,
                response_text=full_response,
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC2_PAYMENT_AGENT_V3",
                reasoning="Payment transfer failed in PaymentAgentV3",
                tools_considered=["prepareTransfer", "executeTransfer"],
                tools_invoked=[],
                result_status="error",
                result_summary=f"Error: {str(e)}",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "error": str(e)}
            )
            raise

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up PaymentAgentV3Handler resources")
        self._cached_agents.clear()

        if self.project_client:
            await self.project_client.close()
            logger.info("✅ AIProjectClient closed")

        if self.credential:
            await self.credential.close()
            logger.info("✅ Azure credential closed")


# Global singleton
_handler: PaymentAgentV3Handler | None = None


async def get_payment_agent_v3_handler() -> PaymentAgentV3Handler:
    """Get or create the global PaymentAgentV3Handler instance"""
    global _handler

    if _handler is None:
        _handler = PaymentAgentV3Handler()
        await _handler.initialize()
        logger.info("PaymentAgentV3Handler singleton initialized")

    return _handler


async def cleanup_handler():
    """Cleanup the global handler"""
    global _handler

    if _handler is not None:
        await _handler.cleanup()
        _handler = None
        logger.info("PaymentAgentV3Handler singleton cleaned up")
