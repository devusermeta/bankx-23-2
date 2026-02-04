#!/usr/bin/env python3
"""
Azure Infrastructure Provisioning Script for BankX Multi-Agent Banking System

This script checks if Azure resources exist in the specified resource group
and creates them if they don't exist. It provisions all required Azure services
for UC1, UC2, and UC3.

Usage:
    python azure_provision.py --config config.json
    python azure_provision.py --resource-group bankx-rg --location eastus
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from azure.identity import DefaultAzureCredential, AzureCliCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.cosmosdb import CosmosDBManagementClient
from azure.mgmt.search import SearchManagementClient
from azure.mgmt.communication import CommunicationServiceManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.apimanagement import ApiManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AzureResourceConfig:
    """Configuration for Azure resources."""
    subscription_id: str
    resource_group_name: str
    location: str

    # Naming conventions
    project_name: str = "bankx"
    environment: str = "dev"

    # Azure OpenAI / Cognitive Services
    openai_account_name: Optional[str] = None
    openai_deployment_name: str = "gpt-4o"
    openai_sku: str = "S0"

    # Azure AI Foundry (AI Services)
    ai_foundry_account_name: Optional[str] = None
    ai_foundry_project_name: Optional[str] = None

    # Azure AI Search
    search_service_name: Optional[str] = None
    search_sku: str = "standard"

    # Azure Cosmos DB
    cosmosdb_account_name: Optional[str] = None
    cosmosdb_database_name: str = "bankx_db"

    # Azure Storage
    storage_account_name: Optional[str] = None
    storage_container_name: str = "content"

    # Azure Document Intelligence
    doc_intelligence_name: Optional[str] = None

    # Azure Communication Services
    communication_service_name: Optional[str] = None

    # Azure API Management
    apim_name: Optional[str] = None
    apim_publisher_email: str = "admin@bankx.com"
    apim_publisher_name: str = "BankX Admin"

    # Azure SQL Database
    sql_server_name: Optional[str] = None
    sql_database_name: str = "bankx_transactions"
    sql_admin_username: str = "bankxadmin"
    sql_admin_password: Optional[str] = None

    # Azure Application Insights
    app_insights_name: Optional[str] = None

    # Azure Key Vault
    key_vault_name: Optional[str] = None

    # Azure App Service / Container Apps
    app_service_plan_name: Optional[str] = None
    app_service_sku: str = "B1"

    def __post_init__(self):
        """Generate resource names if not provided."""
        prefix = f"{self.project_name}-{self.environment}"

        if not self.openai_account_name:
            self.openai_account_name = f"{prefix}-openai"
        if not self.ai_foundry_account_name:
            self.ai_foundry_account_name = f"{prefix}-aifoundry"
        if not self.ai_foundry_project_name:
            self.ai_foundry_project_name = f"{prefix}-aiproject"
        if not self.search_service_name:
            self.search_service_name = f"{prefix}-search"
        if not self.cosmosdb_account_name:
            self.cosmosdb_account_name = f"{prefix}-cosmos"
        if not self.storage_account_name:
            # Storage account names must be lowercase and no hyphens
            self.storage_account_name = f"{self.project_name}{self.environment}storage".lower()
        if not self.doc_intelligence_name:
            self.doc_intelligence_name = f"{prefix}-docintel"
        if not self.communication_service_name:
            self.communication_service_name = f"{prefix}-commservice"
        if not self.apim_name:
            self.apim_name = f"{prefix}-apim"
        if not self.sql_server_name:
            self.sql_server_name = f"{prefix}-sqlserver"
        if not self.app_insights_name:
            self.app_insights_name = f"{prefix}-appinsights"
        if not self.key_vault_name:
            # Key Vault names must be 3-24 characters, alphanumeric and hyphens
            self.key_vault_name = f"{prefix}-kv"
        if not self.app_service_plan_name:
            self.app_service_plan_name = f"{prefix}-appplan"


class AzureInfrastructureProvisioner:
    """Manages Azure infrastructure provisioning for BankX."""

    def __init__(self, config: AzureResourceConfig):
        """Initialize with configuration and Azure credentials."""
        self.config = config
        try:
            # Try DefaultAzureCredential first (works for managed identity, Azure CLI, etc.)
            self.credential = DefaultAzureCredential()
        except Exception as e:
            logger.warning(f"DefaultAzureCredential failed: {e}. Trying AzureCliCredential...")
            self.credential = AzureCliCredential()

        # Initialize management clients
        self.resource_client = ResourceManagementClient(
            self.credential,
            config.subscription_id
        )

    def ensure_resource_group(self) -> bool:
        """Ensure resource group exists, create if it doesn't."""
        try:
            rg = self.resource_client.resource_groups.get(
                self.config.resource_group_name
            )
            logger.info(f"✓ Resource group '{self.config.resource_group_name}' already exists")
            return True
        except ResourceNotFoundError:
            logger.info(f"Creating resource group '{self.config.resource_group_name}'...")
            rg_params = {
                "location": self.config.location,
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment,
                    "managed_by": "azure_provision.py"
                }
            }
            self.resource_client.resource_groups.create_or_update(
                self.config.resource_group_name,
                rg_params
            )
            logger.info(f"✓ Resource group '{self.config.resource_group_name}' created")
            return True

    def provision_azure_openai(self) -> Dict[str, str]:
        """Provision Azure OpenAI service."""
        logger.info(f"Provisioning Azure OpenAI: {self.config.openai_account_name}")

        cognitive_client = CognitiveServicesManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if account exists
            account = cognitive_client.accounts.get(
                self.config.resource_group_name,
                self.config.openai_account_name
            )
            logger.info(f"✓ Azure OpenAI account '{self.config.openai_account_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Azure OpenAI account '{self.config.openai_account_name}'...")

            account_params = {
                "location": self.config.location,
                "kind": "OpenAI",
                "sku": {"name": self.config.openai_sku},
                "properties": {
                    "custom_sub_domain_name": self.config.openai_account_name,
                    "public_network_access": "Enabled"
                },
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = cognitive_client.accounts.begin_create(
                self.config.resource_group_name,
                self.config.openai_account_name,
                account_params
            )
            account = operation.result()
            logger.info(f"✓ Azure OpenAI account created")

        # Get endpoint and keys
        endpoint = f"https://{account.properties.endpoint}"
        keys = cognitive_client.accounts.list_keys(
            self.config.resource_group_name,
            self.config.openai_account_name
        )

        return {
            "AZURE_OPENAI_ENDPOINT": endpoint,
            "AZURE_OPENAI_API_KEY": keys.key1,
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": self.config.openai_deployment_name
        }

    def provision_ai_search(self) -> Dict[str, str]:
        """Provision Azure AI Search service."""
        logger.info(f"Provisioning Azure AI Search: {self.config.search_service_name}")

        search_client = SearchManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if search service exists
            service = search_client.services.get(
                self.config.resource_group_name,
                self.config.search_service_name
            )
            logger.info(f"✓ Azure AI Search service '{self.config.search_service_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Azure AI Search service '{self.config.search_service_name}'...")

            search_params = {
                "location": self.config.location,
                "sku": {"name": self.config.search_sku},
                "replica_count": 1,
                "partition_count": 1,
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = search_client.services.begin_create_or_update(
                self.config.resource_group_name,
                self.config.search_service_name,
                search_params
            )
            service = operation.result()
            logger.info(f"✓ Azure AI Search service created")

        # Get admin keys
        keys = search_client.admin_keys.get(
            self.config.resource_group_name,
            self.config.search_service_name
        )

        endpoint = f"https://{self.config.search_service_name}.search.windows.net"

        return {
            "AZURE_SEARCH_ENDPOINT": endpoint,
            "AZURE_SEARCH_API_KEY": keys.primary_key,
            "AZURE_SEARCH_SERVICE_NAME": self.config.search_service_name
        }

    def provision_cosmos_db(self) -> Dict[str, str]:
        """Provision Azure Cosmos DB account."""
        logger.info(f"Provisioning Azure Cosmos DB: {self.config.cosmosdb_account_name}")

        cosmos_client = CosmosDBManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if Cosmos DB account exists
            account = cosmos_client.database_accounts.get(
                self.config.resource_group_name,
                self.config.cosmosdb_account_name
            )
            logger.info(f"✓ Cosmos DB account '{self.config.cosmosdb_account_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Cosmos DB account '{self.config.cosmosdb_account_name}'...")

            cosmos_params = {
                "location": self.config.location,
                "locations": [{
                    "location_name": self.config.location,
                    "failover_priority": 0
                }],
                "database_account_offer_type": "Standard",
                "kind": "GlobalDocumentDB",
                "capabilities": [{"name": "EnableServerless"}],
                "consistency_policy": {
                    "default_consistency_level": "Session"
                },
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = cosmos_client.database_accounts.begin_create_or_update(
                self.config.resource_group_name,
                self.config.cosmosdb_account_name,
                cosmos_params
            )
            account = operation.result()
            logger.info(f"✓ Cosmos DB account created")

        # Get connection strings
        keys = cosmos_client.database_accounts.list_keys(
            self.config.resource_group_name,
            self.config.cosmosdb_account_name
        )

        endpoint = f"https://{self.config.cosmosdb_account_name}.documents.azure.com:443/"

        return {
            "AZURE_COSMOS_ENDPOINT": endpoint,
            "AZURE_COSMOS_KEY": keys.primary_master_key,
            "AZURE_COSMOS_DATABASE_NAME": self.config.cosmosdb_database_name
        }

    def provision_storage_account(self) -> Dict[str, str]:
        """Provision Azure Storage account."""
        logger.info(f"Provisioning Azure Storage: {self.config.storage_account_name}")

        storage_client = StorageManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if storage account exists
            account = storage_client.storage_accounts.get_properties(
                self.config.resource_group_name,
                self.config.storage_account_name
            )
            logger.info(f"✓ Storage account '{self.config.storage_account_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Storage account '{self.config.storage_account_name}'...")

            storage_params = {
                "location": self.config.location,
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2",
                "properties": {
                    "access_tier": "Hot",
                    "encryption": {
                        "services": {
                            "blob": {"enabled": True},
                            "file": {"enabled": True}
                        },
                        "key_source": "Microsoft.Storage"
                    },
                    "supports_https_traffic_only": True
                },
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = storage_client.storage_accounts.begin_create(
                self.config.resource_group_name,
                self.config.storage_account_name,
                storage_params
            )
            account = operation.result()
            logger.info(f"✓ Storage account created")

        # Get account keys
        keys = storage_client.storage_accounts.list_keys(
            self.config.resource_group_name,
            self.config.storage_account_name
        )

        return {
            "AZURE_STORAGE_ACCOUNT": self.config.storage_account_name,
            "AZURE_STORAGE_KEY": keys.keys[0].value,
            "AZURE_STORAGE_CONTAINER": self.config.storage_container_name,
            "AZURE_STORAGE_CONNECTION_STRING":
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={self.config.storage_account_name};"
                f"AccountKey={keys.keys[0].value};"
                f"EndpointSuffix=core.windows.net"
        }

    def provision_document_intelligence(self) -> Dict[str, str]:
        """Provision Azure Document Intelligence (Form Recognizer)."""
        logger.info(f"Provisioning Azure Document Intelligence: {self.config.doc_intelligence_name}")

        cognitive_client = CognitiveServicesManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if account exists
            account = cognitive_client.accounts.get(
                self.config.resource_group_name,
                self.config.doc_intelligence_name
            )
            logger.info(f"✓ Document Intelligence '{self.config.doc_intelligence_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Document Intelligence '{self.config.doc_intelligence_name}'...")

            account_params = {
                "location": self.config.location,
                "kind": "FormRecognizer",
                "sku": {"name": "S0"},
                "properties": {
                    "custom_sub_domain_name": self.config.doc_intelligence_name,
                    "public_network_access": "Enabled"
                },
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = cognitive_client.accounts.begin_create(
                self.config.resource_group_name,
                self.config.doc_intelligence_name,
                account_params
            )
            account = operation.result()
            logger.info(f"✓ Document Intelligence created")

        # Get endpoint and keys
        endpoint = account.properties.endpoint
        keys = cognitive_client.accounts.list_keys(
            self.config.resource_group_name,
            self.config.doc_intelligence_name
        )

        return {
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": endpoint,
            "AZURE_DOCUMENT_INTELLIGENCE_KEY": keys.key1,
            "AZURE_DOCUMENT_INTELLIGENCE_SERVICE": self.config.doc_intelligence_name
        }

    def provision_communication_services(self) -> Dict[str, str]:
        """Provision Azure Communication Services."""
        logger.info(f"Provisioning Azure Communication Services: {self.config.communication_service_name}")

        comm_client = CommunicationServiceManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if communication service exists
            service = comm_client.communication_services.get(
                self.config.resource_group_name,
                self.config.communication_service_name
            )
            logger.info(f"✓ Communication Services '{self.config.communication_service_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Communication Services '{self.config.communication_service_name}'...")

            comm_params = {
                "location": "global",  # Communication Services is global
                "data_location": "United States",
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = comm_client.communication_services.begin_create_or_update(
                self.config.resource_group_name,
                self.config.communication_service_name,
                comm_params
            )
            service = operation.result()
            logger.info(f"✓ Communication Services created")

        # Get connection string
        keys = comm_client.communication_services.list_keys(
            self.config.resource_group_name,
            self.config.communication_service_name
        )

        return {
            "AZURE_COMMUNICATION_SERVICE_CONNECTION_STRING": keys.primary_connection_string,
            "AZURE_COMMUNICATION_SERVICE_NAME": self.config.communication_service_name
        }

    def provision_application_insights(self) -> Dict[str, str]:
        """Provision Azure Application Insights."""
        logger.info(f"Provisioning Azure Application Insights: {self.config.app_insights_name}")

        # Note: Application Insights requires azure-mgmt-applicationinsights package
        # For now, we'll provide placeholder - implement based on your specific needs

        logger.warning("Application Insights provisioning requires azure-mgmt-applicationinsights package")
        logger.info("Please provision manually or install the package and implement")

        return {
            "APPLICATIONINSIGHTS_CONNECTION_STRING": "InstrumentationKey=<your-key>;IngestionEndpoint=https://<region>.in.applicationinsights.azure.com/",
            "AZURE_APP_INSIGHTS_NAME": self.config.app_insights_name
        }

    def provision_key_vault(self) -> Dict[str, str]:
        """Provision Azure Key Vault."""
        logger.info(f"Provisioning Azure Key Vault: {self.config.key_vault_name}")

        kv_client = KeyVaultManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if key vault exists
            vault = kv_client.vaults.get(
                self.config.resource_group_name,
                self.config.key_vault_name
            )
            logger.info(f"✓ Key Vault '{self.config.key_vault_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating Key Vault '{self.config.key_vault_name}'...")

            # Get current user object ID for access policy
            import os
            tenant_id = os.getenv("AZURE_TENANT_ID", "<your-tenant-id>")

            vault_params = {
                "location": self.config.location,
                "properties": {
                    "tenant_id": tenant_id,
                    "sku": {"name": "standard", "family": "A"},
                    "access_policies": [],
                    "enabled_for_deployment": True,
                    "enabled_for_disk_encryption": True,
                    "enabled_for_template_deployment": True,
                    "enable_rbac_authorization": True
                },
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = kv_client.vaults.begin_create_or_update(
                self.config.resource_group_name,
                self.config.key_vault_name,
                vault_params
            )
            vault = operation.result()
            logger.info(f"✓ Key Vault created")

        return {
            "AZURE_KEY_VAULT_NAME": self.config.key_vault_name,
            "AZURE_KEY_VAULT_URL": f"https://{self.config.key_vault_name}.vault.azure.net/"
        }

    def provision_apim(self) -> Dict[str, str]:
        """Provision Azure API Management for MCP tool gateway."""
        logger.info(f"Provisioning Azure API Management: {self.config.apim_name}")

        apim_client = ApiManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if APIM service exists
            service = apim_client.api_management_service.get(
                self.config.resource_group_name,
                self.config.apim_name
            )
            logger.info(f"✓ API Management '{self.config.apim_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating API Management '{self.config.apim_name}'...")
            logger.warning("⚠️ APIM provisioning can take 30-45 minutes...")

            apim_params = {
                "location": self.config.location,
                "sku": {
                    "name": "Developer",  # Use Developer for dev, change to Standard/Premium for prod
                    "capacity": 1
                },
                "publisher_email": self.config.apim_publisher_email,
                "publisher_name": self.config.apim_publisher_name,
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = apim_client.api_management_service.begin_create_or_update(
                self.config.resource_group_name,
                self.config.apim_name,
                apim_params
            )
            service = operation.result()  # This will wait for completion
            logger.info(f"✓ API Management created")

        # Get subscription keys
        try:
            subscription_list = list(apim_client.subscription.list(
                self.config.resource_group_name,
                self.config.apim_name
            ))

            # Get built-in subscription or create one
            if subscription_list:
                subscription = subscription_list[0]
                keys = apim_client.subscription.list_secrets(
                    self.config.resource_group_name,
                    self.config.apim_name,
                    subscription.name
                )
                primary_key = keys.primary_key
            else:
                # Create a new subscription
                logger.info("Creating APIM subscription...")
                subscription_params = {
                    "scope": f"/subscriptions/{self.config.subscription_id}/resourceGroups/{self.config.resource_group_name}/providers/Microsoft.ApiManagement/service/{self.config.apim_name}/apis",
                    "display_name": "BankX MCP Tools Subscription",
                    "state": "active"
                }
                subscription = apim_client.subscription.create_or_update(
                    self.config.resource_group_name,
                    self.config.apim_name,
                    "bankx-mcp-subscription",
                    subscription_params
                )
                keys = apim_client.subscription.list_secrets(
                    self.config.resource_group_name,
                    self.config.apim_name,
                    "bankx-mcp-subscription"
                )
                primary_key = keys.primary_key
        except Exception as e:
            logger.warning(f"Could not retrieve APIM keys: {e}")
            primary_key = "<retrieve-from-portal>"

        endpoint = f"https://{self.config.apim_name}.azure-api.net"

        return {
            "AZURE_APIM_ENDPOINT": endpoint,
            "AZURE_APIM_SUBSCRIPTION_KEY": primary_key,
            "AZURE_APIM_NAME": self.config.apim_name
        }

    def provision_sql_database(self) -> Dict[str, str]:
        """Provision Azure SQL Database (optional for production)."""
        logger.info(f"Provisioning Azure SQL: {self.config.sql_server_name}")

        sql_client = SqlManagementClient(
            self.credential,
            self.config.subscription_id
        )

        try:
            # Check if SQL server exists
            server = sql_client.servers.get(
                self.config.resource_group_name,
                self.config.sql_server_name
            )
            logger.info(f"✓ SQL Server '{self.config.sql_server_name}' already exists")
        except ResourceNotFoundError:
            if not self.config.sql_admin_password:
                logger.warning("⚠️ SQL admin password not provided in config")
                logger.warning("⚠️ Skipping SQL Server provisioning - provision manually or add password to config")
                return {
                    "AZURE_SQL_SERVER": f"{self.config.sql_server_name}.database.windows.net",
                    "AZURE_SQL_DATABASE": self.config.sql_database_name,
                    "AZURE_SQL_USERNAME": self.config.sql_admin_username,
                    "AZURE_SQL_PASSWORD": "<set-manually>",
                }

            logger.info(f"Creating SQL Server '{self.config.sql_server_name}'...")

            server_params = {
                "location": self.config.location,
                "administrator_login": self.config.sql_admin_username,
                "administrator_login_password": self.config.sql_admin_password,
                "version": "12.0",
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = sql_client.servers.begin_create_or_update(
                self.config.resource_group_name,
                self.config.sql_server_name,
                server_params
            )
            server = operation.result()
            logger.info(f"✓ SQL Server created")

            # Create firewall rule to allow Azure services
            logger.info("Creating firewall rule for Azure services...")
            firewall_params = {
                "start_ip_address": "0.0.0.0",
                "end_ip_address": "0.0.0.0"
            }
            sql_client.firewall_rules.create_or_update(
                self.config.resource_group_name,
                self.config.sql_server_name,
                "AllowAzureServices",
                firewall_params
            )

        # Create database if it doesn't exist
        try:
            database = sql_client.databases.get(
                self.config.resource_group_name,
                self.config.sql_server_name,
                self.config.sql_database_name
            )
            logger.info(f"✓ SQL Database '{self.config.sql_database_name}' already exists")
        except ResourceNotFoundError:
            logger.info(f"Creating SQL Database '{self.config.sql_database_name}'...")

            database_params = {
                "location": self.config.location,
                "sku": {
                    "name": "Basic",  # Change to Standard or Premium for production
                    "tier": "Basic"
                },
                "tags": {
                    "project": self.config.project_name,
                    "environment": self.config.environment
                }
            }

            operation = sql_client.databases.begin_create_or_update(
                self.config.resource_group_name,
                self.config.sql_server_name,
                self.config.sql_database_name,
                database_params
            )
            database = operation.result()
            logger.info(f"✓ SQL Database created")

        connection_string = (
            f"Server=tcp:{self.config.sql_server_name}.database.windows.net,1433;"
            f"Database={self.config.sql_database_name};"
            f"User ID={self.config.sql_admin_username};"
            f"Password={self.config.sql_admin_password or '<your-password>'};"
            f"Encrypt=true;TrustServerCertificate=false;Connection Timeout=30;"
        )

        return {
            "AZURE_SQL_SERVER": f"{self.config.sql_server_name}.database.windows.net",
            "AZURE_SQL_DATABASE": self.config.sql_database_name,
            "AZURE_SQL_USERNAME": self.config.sql_admin_username,
            "AZURE_SQL_PASSWORD": self.config.sql_admin_password or "<set-manually>",
            "AZURE_SQL_CONNECTION_STRING": connection_string
        }

    def provision_all(self) -> Dict[str, str]:
        """Provision all Azure resources and return environment variables."""
        logger.info("=" * 80)
        logger.info("Starting BankX Azure Infrastructure Provisioning")
        logger.info("=" * 80)

        env_vars = {}

        # Ensure resource group exists first
        self.ensure_resource_group()

        # Provision all services
        services = [
            ("Azure OpenAI", self.provision_azure_openai),
            ("Azure AI Search", self.provision_ai_search),
            ("Azure Cosmos DB", self.provision_cosmos_db),
            ("Azure Storage", self.provision_storage_account),
            ("Azure Document Intelligence", self.provision_document_intelligence),
            ("Azure Communication Services", self.provision_communication_services),
            ("Azure Application Insights", self.provision_application_insights),
            ("Azure Key Vault", self.provision_key_vault),
            ("Azure API Management", self.provision_apim),
            ("Azure SQL Database", self.provision_sql_database),
        ]

        for service_name, provision_func in services:
            try:
                logger.info(f"\n{'=' * 80}")
                logger.info(f"Provisioning {service_name}")
                logger.info(f"{'=' * 80}")
                result = provision_func()
                env_vars.update(result)
                logger.info(f"✓ {service_name} provisioned successfully\n")
            except Exception as e:
                logger.error(f"✗ Failed to provision {service_name}: {e}")
                logger.warning(f"Continuing with other services...\n")

        # Add additional configuration
        env_vars.update({
            "AZURE_SUBSCRIPTION_ID": self.config.subscription_id,
            "AZURE_RESOURCE_GROUP": self.config.resource_group_name,
            "AZURE_LOCATION": self.config.location,
        })

        logger.info("\n" + "=" * 80)
        logger.info("Provisioning Complete!")
        logger.info("=" * 80)

        return env_vars

    def save_env_file(self, env_vars: Dict[str, str], output_file: str = ".env.generated"):
        """Save environment variables to a file."""
        logger.info(f"\nSaving environment variables to {output_file}...")

        with open(output_file, 'w') as f:
            f.write("# Auto-generated by azure_provision.py\n")
            f.write(f"# Generated for resource group: {self.config.resource_group_name}\n")
            f.write(f"# Location: {self.config.location}\n\n")

            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")

        logger.info(f"✓ Environment variables saved to {output_file}")
        logger.info(f"\nTo use these variables:")
        logger.info(f"  1. Review and update {output_file}")
        logger.info(f"  2. Copy to your .env file or source directly")
        logger.info(f"  3. Never commit API keys or secrets to version control!")


def load_config_from_file(config_file: str) -> AzureResourceConfig:
    """Load configuration from JSON file."""
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    return AzureResourceConfig(**config_data)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Provision Azure infrastructure for BankX Multi-Agent Banking System"
    )
    parser.add_argument(
        "--config",
        help="Path to JSON configuration file"
    )
    parser.add_argument(
        "--subscription-id",
        help="Azure subscription ID"
    )
    parser.add_argument(
        "--resource-group",
        help="Resource group name"
    )
    parser.add_argument(
        "--location",
        default="eastus",
        help="Azure region (default: eastus)"
    )
    parser.add_argument(
        "--environment",
        default="dev",
        choices=["dev", "staging", "prod"],
        help="Environment name (default: dev)"
    )
    parser.add_argument(
        "--output",
        default=".env.generated",
        help="Output file for environment variables (default: .env.generated)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating resources"
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        config = load_config_from_file(args.config)
    else:
        if not args.subscription_id or not args.resource_group:
            parser.error("Either --config or both --subscription-id and --resource-group are required")

        config = AzureResourceConfig(
            subscription_id=args.subscription_id,
            resource_group_name=args.resource_group,
            location=args.location,
            environment=args.environment
        )

    if args.dry_run:
        logger.info("DRY RUN MODE - No resources will be created")
        logger.info(f"\nConfiguration:")
        logger.info(json.dumps(asdict(config), indent=2))
        return

    # Provision infrastructure
    provisioner = AzureInfrastructureProvisioner(config)
    env_vars = provisioner.provision_all()

    # Save environment variables
    provisioner.save_env_file(env_vars, args.output)

    logger.info("\n✓ All done! Your BankX infrastructure is ready.")


if __name__ == "__main__":
    main()
