"""Dependency injection container configuration."""

import os
from dependency_injector import containers, providers
from azure.ai.projects import AIProjectClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.storage.blob import BlobServiceClient
from app.helpers.blob_proxy import BlobStorageProxy
from app.helpers.document_intelligence_scanner import DocumentIntelligenceInvoiceScanHelper
from app.config.azure_credential import get_azure_credential, get_azure_credential_async
from app.config.settings import settings
from app.cache import get_cache_manager

# Azure AI Foundry based agent dependencies
from app.agents.foundry.account_agent_foundry import AccountAgent
from app.agents.foundry.transaction_agent_foundry import TransactionAgent
from app.agents.foundry.payment_agent_foundry import PaymentAgent

# UC2 & UC3: ACTIVE VERSION - Using native file search (Azure AI Foundry vector store) with V2 format
from app.agents.foundry.prodinfo_faq_agent_knowledge_base_foundry import ProdInfoFAQAgentKnowledgeBase
from app.agents.foundry.ai_money_coach_agent_knowledge_base_foundry import AIMoneyCoachKnowledgeBaseAgent

# UC2 & UC3: OLD VERSION - Using MCP server RAG (COMMENTED OUT)
# from app.agents.foundry.prodinfo_faq_agent_foundry import ProdInfoFAQAgent
# from app.agents.foundry.ai_money_coach_agent_foundry import AIMoneyCoachAgent

from app.agents.foundry.escalation_comms_agent_foundry import EscalationCommsAgent

# Supervisor: Choose between OLD (in-process) and NEW (A2A-aware) based on feature flags
if settings.USE_A2A_FOR_ACCOUNT_AGENT:
    print("🚀 Phase 1 A2A ENABLED - Using A2A-aware Supervisor")
    from app.agents.foundry.supervisor_agent_a2a import SupervisorAgentA2A as SupervisorAgent
    from app.agents.foundry.supervisor_agent_a2a import create_supervisor_with_a2a
else:
    print("📦 Phase 1 A2A DISABLED - Using traditional in-process Supervisor")
    from app.agents.foundry.supervisor_agent_foundry import SupervisorAgent

from agent_framework import MCPStreamableHTTPTool


def get_or_create_agent(foundry_client, agent_name: str, agent_description: str, model_deployment: str, agent_id: str | None = None, agent_version: str = "1"):
    """Check if agent exists by name (NEW) or ID (OLD/deprecated). Returns the agent object.
    
    Args:
        foundry_client: The Azure AI Foundry client
        agent_name: Name of the agent (used as ID in new Azure AI Foundry)
        agent_description: Description of the agent
        model_deployment: Model deployment name
        agent_id: Optional OLD FORMAT agent ID (asst_*) - DEPRECATED, use agent_name instead
        agent_version: Agent version (default: "1")
    """
    # NEW FORMAT: Use agent_name as the identifier (Azure AI Foundry V2)
    # The agent should already exist in Azure AI Foundry portal
    print(f"✅ Using agent name (V2 format): {agent_name}:v{agent_version}")
    class AgentReference:
        def __init__(self, name, version):
            self.id = f"{name}:v{version}"  # V2 format: name:version
            self.name = name
            self.version = version
    return AgentReference(agent_name, agent_version)
    
    # OLD FORMAT fallback (if needed for backward compatibility)
    # if agent_id:
    #     print(f"⚠️  Using OLD format agent ID for {agent_name}: {agent_id}")
    #     class AgentReference:
    #         def __init__(self, agent_id):
    #             self.id = agent_id
    #     return AgentReference(agent_id)


class Container(containers.DeclarativeContainer):
    """IoC container for application dependencies."""
   
    # Cache Manager - Singleton for fast UC1 responses
    _cache_manager = providers.Singleton(get_cache_manager)
   
    # Helpers
    blob_service_client = providers.Singleton(
        BlobServiceClient,
        credential = providers.Factory(get_azure_credential),
        account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"
    )

    blob_proxy = providers.Singleton(
        BlobStorageProxy,
        client = blob_service_client,
        container_name = settings.AZURE_STORAGE_CONTAINER
    )

    # Document Intelligence client singleton
    document_intelligence_client = providers.Singleton(
        DocumentIntelligenceClient,
        credential=providers.Factory(get_azure_credential),
        endpoint=f"https://{settings.AZURE_DOCUMENT_INTELLIGENCE_SERVICE}.cognitiveservices.azure.com/"
    )

    # Document Intelligence scanner singleton
    document_intelligence_scanner = providers.Singleton(
        DocumentIntelligenceInvoiceScanHelper,
        client=document_intelligence_client,
        blob_storage_proxy=blob_proxy
    )
    

     

    
    #Azure Agent Service based agents

    # Foundry Agent Creation
    _foundry_project_client = AIProjectClient(
        settings.FOUNDRY_PROJECT_ENDPOINT, 
        credential=get_azure_credential(), 
        logging_enable=True
    )
    
    # ============================================================================
    # CONDITIONAL AGENT INITIALIZATION BASED ON A2A MODE
    # ============================================================================
    # When A2A mode is enabled for ALL UC1 agents (Account, Transaction, Payment),
    # we DON'T need to initialize these in-process agents because the supervisor
    # will route to standalone A2A agents running on ports 9001-9006 instead.
    #
    # This prevents:
    # - Unnecessary agent initialization at startup
    # - SDK compatibility errors (AgentsOperations methods changed)
    # - Wasted resources creating agents we won't use
    # ============================================================================
    
    _a2a_mode_enabled = (settings.USE_A2A_FOR_ACCOUNT_AGENT and 
                          settings.USE_A2A_FOR_TRANSACTION_AGENT and 
                          settings.USE_A2A_FOR_PAYMENT_AGENT)
    
    if not _a2a_mode_enabled:
        # TRADITIONAL MODE: Initialize all in-process specialist agents
        # These agents run inside the copilot process and handle requests directly
        print("📦 Initializing IN-PROCESS specialist agents (Traditional mode)...")
        
        # Account Agent with Azure AI Foundry
        _foundry_account_agent = providers.Singleton(
            AccountAgent,
            foundry_project_client=_foundry_project_client,
            chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
            account_mcp_server_url=f"{settings.ACCOUNT_MCP_URL}/mcp",
            limits_mcp_server_url=f"{settings.LIMITS_MCP_URL}/mcp",
            foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            agent_name=settings.ACCOUNT_AGENT_NAME,
            agent_version=settings.ACCOUNT_AGENT_VERSION
        )

        # Transaction Agent with Azure AI Foundry
        _foundry_transaction_agent = providers.Singleton(
            TransactionAgent,
            foundry_project_client=_foundry_project_client,
            chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
            account_mcp_server_url=f"{settings.ACCOUNT_MCP_URL}/mcp",
            transaction_mcp_server_url=f"{settings.TRANSACTION_MCP_URL}/mcp",
            foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            agent_name=settings.TRANSACTION_AGENT_NAME,
            agent_version=settings.TRANSACTION_AGENT_VERSION
        )

        # Payment Agent with Azure AI Foundry
        _foundry_payment_agent = providers.Singleton(
            PaymentAgent,
            foundry_project_client=_foundry_project_client,
            chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
            account_mcp_server_url=f"{settings.ACCOUNT_MCP_URL}/mcp",
            transaction_mcp_server_url=f"{settings.TRANSACTION_MCP_URL}/mcp",
            payment_mcp_server_url=f"{settings.PAYMENT_MCP_URL}/mcp",
            contacts_mcp_server_url=f"{settings.CONTACTS_MCP_URL}/mcp",
            cache_mcp_server_url=f"{settings.CACHE_MCP_URL}/mcp" if settings.CACHE_MCP_URL else "http://localhost:8079/mcp",
            document_scanner_helper=document_intelligence_scanner,
            foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            agent_name=settings.PAYMENT_AGENT_NAME,
            agent_version=settings.PAYMENT_AGENT_VERSION
        )

        # ProdInfoFAQ Agent with Azure AI Foundry (UC2)
        # ACTIVE: Using native file search (Azure AI Foundry vector store)
        _foundry_prodinfo_faq_agent = providers.Singleton(
            ProdInfoFAQAgentKnowledgeBase,
            foundry_project_client=_foundry_project_client,
            chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
            escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp" if settings.ESCALATION_COMMS_MCP_URL else None,
            foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            agent_name=settings.PRODINFO_FAQ_AGENT_NAME,
            agent_version=settings.PRODINFO_FAQ_AGENT_VERSION,
            vector_store_ids=[v.strip() for v in settings.PRODINFO_FAQ_VECTOR_STORE_IDS.split(",")] if settings.PRODINFO_FAQ_VECTOR_STORE_IDS else []
        )
    else:
        # A2A MODE: Skip in-process agent initialization
        # Supervisor will route to standalone A2A agents instead
        print("🚀 A2A MODE: Skipping in-process agent initialization")
        print("   → Supervisor will route to standalone A2A agents (ports 9001-9006)")
        
        # Create dummy providers that won't be used (required by container structure)
        _foundry_account_agent = None
        _foundry_transaction_agent = None
        _foundry_payment_agent = None
        _foundry_prodinfo_faq_agent = None
    
    # OLD VERSION (COMMENTED OUT): Using Azure AI Search RAG via MCP server (port 8076)
    # _foundry_prodinfo_faq_agent = providers.Singleton(
    #     ProdInfoFAQAgent,
    #     foundry_project_client=_foundry_project_client,
    #     chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
    #     prodinfo_faq_mcp_server_url=f"{settings.PRODINFO_FAQ_MCP_URL}/mcp" if settings.PRODINFO_FAQ_MCP_URL else None,
    #     escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp" if settings.ESCALATION_COMMS_MCP_URL else None,
    #     foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
    #     agent_id=settings.PRODINFO_FAQ_AGENT_ID if hasattr(settings, 'PRODINFO_FAQ_AGENT_ID') else None
    # )

    # AIMoneyCoach and EscalationComms agents - Always initialized (needed for UC2/UC3)
    # These are not yet migrated to A2A in Phase 1
    
    # AIMoneyCoach Agent with Azure AI Foundry (UC3)
    # ACTIVE: Using native file search (Azure AI Foundry vector store)  
    _foundry_ai_money_coach_agent = providers.Singleton(
        AIMoneyCoachKnowledgeBaseAgent,
        foundry_project_client=_foundry_project_client,
        chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
        escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp" if settings.ESCALATION_COMMS_MCP_URL else None,
        foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
        agent_name=settings.AI_MONEY_COACH_AGENT_NAME,
        agent_version=settings.AI_MONEY_COACH_AGENT_VERSION,
        vector_store_ids=[v.strip() for v in settings.AI_MONEY_COACH_VECTOR_STORE_IDS.split(",")] if settings.AI_MONEY_COACH_VECTOR_STORE_IDS else []
    )
    
    # OLD VERSION (COMMENTED OUT): Using Azure AI Search RAG via MCP server (port 8077)
    # _foundry_ai_money_coach_agent = providers.Singleton(
    #     AIMoneyCoachAgent,
    #     foundry_project_client=_foundry_project_client,
    #     chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
    #     ai_money_coach_mcp_server_url=f"{settings.AI_MONEY_COACH_MCP_URL}/mcp" if settings.AI_MONEY_COACH_MCP_URL else None,
    #     escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp" if settings.ESCALATION_COMMS_MCP_URL else None,
    #     foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
    #     agent_id=settings.AI_MONEY_COACH_AGENT_ID if hasattr(settings, 'AI_MONEY_COACH_AGENT_ID') else None
    # )

    # EscalationComms Agent with Azure AI Foundry (Email Notifications - UC2/UC3/UC4)
    _foundry_escalation_comms_agent = providers.Singleton(
        EscalationCommsAgent,
        foundry_project_client=_foundry_project_client,
        chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
        escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp" if settings.ESCALATION_COMMS_MCP_URL else None,
        foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
        agent_name=settings.ESCALATION_AGENT_NAME,
        agent_version=settings.ESCALATION_AGENT_VERSION
    )

    # Get or create the native foundry supervisor agent (reuse existing if found)
    # NOTE: In A2A mode, this is just a reference - actual agents run standalone
    _foundry_supervisor_native_agent = get_or_create_agent(
        _foundry_project_client, 
        settings.SUPERVISOR_AGENT_NAME or "BankXSupervisor",  # Use name from env or default
        SupervisorAgent.description,
        settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
        agent_id=settings.SUPERVISOR_AGENT_ID,  # OLD format (deprecated)
        agent_version=settings.SUPERVISOR_AGENT_VERSION or "1"  # NEW format
    )


    # ============================================================================
    # CONVERSATION MANAGER - For both A2A and Traditional modes
    # ============================================================================
    # Import conversation manager for conversation logging
    # Note: conversation_manager contains thread locks, so we create it once
    # at module level and wrap in providers.Object() to avoid deepcopy
    _conversation_manager_instance = None
    try:
        import sys
        from pathlib import Path
        conversations_dir = Path(__file__).resolve().parent.parent.parent.parent / "conversations"
        lib_path = str(conversations_dir)
        
        print(f"[CONTAINER] 🔍 Loading conversation_manager from: {lib_path}")
        if lib_path not in sys.path:
            sys.path.insert(0, lib_path)
        
        import importlib
        conv_mod = importlib.import_module("conversation_manager")
        get_conversation_manager = getattr(conv_mod, "get_conversation_manager")
        _conversation_manager_instance = get_conversation_manager()
        print(f"[CONTAINER] ✅ conversation_manager loaded successfully")
    except Exception as e:
        print(f"[CONTAINER] ⚠️ conversation_manager not available: {e}")
        _conversation_manager_instance = None
    
    # Wrap in providers.Object() to avoid deepcopy issues
    _conversation_manager = providers.Object(_conversation_manager_instance)
    



    # ============================================================================
    # SUPERVISOR AGENT - A2A MODE vs TRADITIONAL MODE
    # ============================================================================
    # A2A MODE: Supervisor routes requests to standalone A2A agents via HTTP
    # TRADITIONAL MODE: Supervisor manages in-process specialist agents
    # ============================================================================
    if settings.USE_A2A_FOR_ACCOUNT_AGENT or settings.USE_A2A_FOR_TRANSACTION_AGENT or settings.USE_A2A_FOR_PAYMENT_AGENT:
        # ✅ A2A MODE: Supervisor routes to standalone A2A specialist agents
        print("🚀 A2A MODE ENABLED - Supervisor will route to standalone agents")
        supervisor_agent = providers.Singleton(
            create_supervisor_with_a2a,
            # A2A URLs for standalone specialist agents (ports 9001-9006)
            account_agent_a2a_url=settings.ACCOUNT_AGENT_A2A_URL,
            transaction_agent_a2a_url=settings.TRANSACTION_AGENT_A2A_URL,
            payment_agent_a2a_url=settings.PAYMENT_AGENT_A2A_URL,
            prodinfo_faq_agent_a2a_url=settings.PRODINFO_FAQ_AGENT_A2A_URL,
            ai_money_coach_agent_a2a_url=settings.AI_MONEY_COACH_AGENT_A2A_URL,
            escalation_comms_agent_a2a_url=settings.ESCALATION_COMMS_AGENT_A2A_URL,
            
            # Feature flags to enable/disable A2A routing per agent
            enable_a2a_account=settings.USE_A2A_FOR_ACCOUNT_AGENT,
            enable_a2a_transaction=settings.USE_A2A_FOR_TRANSACTION_AGENT,
            enable_a2a_payment=settings.USE_A2A_FOR_PAYMENT_AGENT,
            enable_a2a_prodinfo=True,  # Enable A2A for ProdInfo by default
            enable_a2a_ai_coach=True,  # Enable A2A for AI Coach by default
            enable_a2a_escalation=True,  # ✅ Enable A2A for Escalation Agent
            
            # Cache manager for fast UC1 responses (balance, transactions, limits, etc.)
            cache_manager=_cache_manager,

            
            # Conversation manager for logging conversations (both A2A and Traditional)
            # Wrapped in providers.Object() to avoid deepcopy issues with thread locks
            conversation_manager=_conversation_manager,            

            # Pass None for agents that are handled via A2A (not needed in-process)
            # These parameters are kept for backward compatibility but won't be used
            account_agent_old=None,
            transaction_agent_old=None,
            payment_agent_old=None,
            prodinfo_agent_old=None,
            ai_coach_agent_old=None,
            escalation_comms_agent_old=_foundry_escalation_comms_agent,
        )
    else:
        # ❌ TRADITIONAL MODE: All specialists run in-process, supervisor manages them
        print("📦 TRADITIONAL MODE - All agents running in-process")
        supervisor_agent = providers.Singleton(
            SupervisorAgent,
            foundry_project_client=_foundry_project_client,
            chat_deployment_name=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
            account_agent=_foundry_account_agent,
            transaction_agent=_foundry_transaction_agent,
            payment_agent=_foundry_payment_agent,
            escalation_comms_agent=_foundry_escalation_comms_agent,
            prodinfo_faq_agent=_foundry_prodinfo_faq_agent,
            ai_money_coach_agent=_foundry_ai_money_coach_agent,
            foundry_endpoint=settings.FOUNDRY_PROJECT_ENDPOINT,
            agent_name=_foundry_supervisor_native_agent.name,
            agent_version=_foundry_supervisor_native_agent.version,
            # Cache manager for fast UC1 responses (balance, transactions, limits, etc.)
            cache_manager=_cache_manager,
        )

   