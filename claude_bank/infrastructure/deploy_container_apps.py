"""Deploy BankX A2A agents to Azure Container Apps.

This script deploys the Agent Registry and all agent services to Azure Container Apps.
It does NOT use Kubernetes - it's specifically for Azure Container Apps deployment.
"""
import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ContainerAppsDeployer:
    """Deploy agents to Azure Container Apps."""

    def __init__(
        self,
        subscription_id: str,
        resource_group: str,
        location: str,
        environment_name: str,
        registry_name: str,
    ):
        """Initialize deployer.

        Args:
            subscription_id: Azure subscription ID
            resource_group: Resource group name
            location: Azure region (e.g., eastus)
            environment_name: Container Apps environment name
            registry_name: Azure Container Registry name
        """
        self.subscription_id = subscription_id
        self.resource_group = resource_group
        self.location = location
        self.environment_name = environment_name
        self.registry_name = registry_name
        self.acr_login_server = f"{registry_name}.azurecr.io"

    def run_command(self, command: List[str], check: bool = True) -> Optional[str]:
        """Run Azure CLI command.

        Args:
            command: Command to run
            check: Whether to check return code

        Returns:
            Command output or None if failed
        """
        try:
            logger.info(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                check=check,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            if check:
                raise
            return None

    def set_subscription(self):
        """Set active Azure subscription."""
        logger.info(f"Setting subscription: {self.subscription_id}")
        self.run_command([
            "az", "account", "set",
            "--subscription", self.subscription_id
        ])

    def create_resource_group(self):
        """Create resource group if it doesn't exist."""
        logger.info(f"Creating resource group: {self.resource_group}")
        self.run_command([
            "az", "group", "create",
            "--name", self.resource_group,
            "--location", self.location
        ])

    def create_container_registry(self):
        """Create Azure Container Registry if it doesn't exist."""
        logger.info(f"Creating Azure Container Registry: {self.registry_name}")

        # Check if ACR exists
        existing = self.run_command([
            "az", "acr", "show",
            "--name", self.registry_name,
            "--resource-group", self.resource_group
        ], check=False)

        if not existing:
            self.run_command([
                "az", "acr", "create",
                "--name", self.registry_name,
                "--resource-group", self.resource_group,
                "--location", self.location,
                "--sku", "Basic",
                "--admin-enabled", "true"
            ])
            logger.info("Container Registry created")
        else:
            logger.info("Container Registry already exists")

    def create_container_apps_environment(self):
        """Create Container Apps environment."""
        logger.info(f"Creating Container Apps environment: {self.environment_name}")

        # Check if environment exists
        existing = self.run_command([
            "az", "containerapp", "env", "show",
            "--name", self.environment_name,
            "--resource-group", self.resource_group
        ], check=False)

        if not existing:
            self.run_command([
                "az", "containerapp", "env", "create",
                "--name", self.environment_name,
                "--resource-group", self.resource_group,
                "--location", self.location
            ])
            logger.info("Container Apps environment created")
        else:
            logger.info("Container Apps environment already exists")

    def build_and_push_image(self, service_name: str, dockerfile_path: str) -> str:
        """Build and push Docker image to ACR.

        Args:
            service_name: Name of the service
            dockerfile_path: Path to Dockerfile

        Returns:
            Full image name with tag
        """
        image_name = f"{self.acr_login_server}/bankx/{service_name}:1.0.0"
        logger.info(f"Building image: {image_name}")

        # Build image using ACR build (no local Docker needed)
        dockerfile_dir = str(Path(dockerfile_path).parent)

        self.run_command([
            "az", "acr", "build",
            "--registry", self.registry_name,
            "--image", f"bankx/{service_name}:1.0.0",
            "--file", dockerfile_path,
            dockerfile_dir
        ])

        logger.info(f"Image built and pushed: {image_name}")
        return image_name

    def deploy_agent_registry(self, redis_connection_string: str, cosmos_endpoint: str, cosmos_key: str):
        """Deploy Agent Registry service.

        Args:
            redis_connection_string: Redis connection string
            cosmos_endpoint: Cosmos DB endpoint
            cosmos_key: Cosmos DB key
        """
        logger.info("Deploying Agent Registry...")

        # Build and push image
        image = self.build_and_push_image(
            "agent-registry",
            "app/agent-registry/Dockerfile"
        )

        # Deploy container app
        env_vars = [
            f"REDIS_URL={redis_connection_string}",
            f"AZURE_COSMOS_ENDPOINT={cosmos_endpoint}",
            f"AZURE_COSMOS_KEY={cosmos_key}",
            "A2A_HEALTH_CHECK_ENABLED=true",
            "LOG_LEVEL=INFO"
        ]

        self.run_command([
            "az", "containerapp", "create",
            "--name", "agent-registry",
            "--resource-group", self.resource_group,
            "--environment", self.environment_name,
            "--image", image,
            "--target-port", "9000",
            "--ingress", "internal",
            "--min-replicas", "2",
            "--max-replicas", "5",
            "--cpu", "0.5",
            "--memory", "1Gi",
            "--registry-server", self.acr_login_server,
            "--env-vars", *env_vars
        ])

        logger.info("Agent Registry deployed successfully")

    def deploy_domain_agent(
        self,
        agent_name: str,
        port: int,
        min_replicas: int,
        max_replicas: int,
        env_vars: Dict[str, str]
    ):
        """Deploy a domain agent.

        Args:
            agent_name: Agent name (e.g., 'account-agent')
            port: Container port
            min_replicas: Minimum replicas
            max_replicas: Maximum replicas
            env_vars: Environment variables
        """
        logger.info(f"Deploying {agent_name}...")

        # Build and push image
        image = self.build_and_push_image(
            agent_name,
            f"app/agents/{agent_name}/Dockerfile"
        )

        # Convert env vars to list
        env_list = [f"{k}={v}" for k, v in env_vars.items()]

        # Deploy container app
        self.run_command([
            "az", "containerapp", "create",
            "--name", agent_name,
            "--resource-group", self.resource_group,
            "--environment", self.environment_name,
            "--image", image,
            "--target-port", str(port),
            "--ingress", "internal",
            "--min-replicas", str(min_replicas),
            "--max-replicas", str(max_replicas),
            "--cpu", "0.5",
            "--memory", "1Gi",
            "--registry-server", self.acr_login_server,
            "--env-vars", *env_list
        ])

        logger.info(f"{agent_name} deployed successfully")

    def get_registry_url(self) -> str:
        """Get internal URL of Agent Registry.

        Returns:
            Internal FQDN of the registry service
        """
        output = self.run_command([
            "az", "containerapp", "show",
            "--name", "agent-registry",
            "--resource-group", self.resource_group,
            "--query", "properties.configuration.ingress.fqdn",
            "--output", "tsv"
        ])
        return f"https://{output}"


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy BankX A2A agents to Azure Container Apps")
    parser.add_argument("--subscription-id", required=True, help="Azure subscription ID")
    parser.add_argument("--resource-group", required=True, help="Resource group name")
    parser.add_argument("--location", default="eastus", help="Azure region")
    parser.add_argument("--environment", default="bankx-agents-env", help="Container Apps environment name")
    parser.add_argument("--registry", default="bankxagentsacr", help="Azure Container Registry name")
    parser.add_argument("--redis-connection", required=True, help="Redis connection string")
    parser.add_argument("--cosmos-endpoint", required=True, help="Cosmos DB endpoint")
    parser.add_argument("--cosmos-key", required=True, help="Cosmos DB key")
    parser.add_argument("--openai-endpoint", required=True, help="Azure OpenAI endpoint")
    parser.add_argument("--openai-key", required=True, help="Azure OpenAI key")

    args = parser.parse_args()

    # Initialize deployer
    deployer = ContainerAppsDeployer(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        location=args.location,
        environment_name=args.environment,
        registry_name=args.registry
    )

    try:
        # Step 1: Set subscription
        deployer.set_subscription()

        # Step 2: Create resource group
        deployer.create_resource_group()

        # Step 3: Create Container Registry
        deployer.create_container_registry()

        # Step 4: Create Container Apps environment
        deployer.create_container_apps_environment()

        # Step 5: Deploy Agent Registry
        deployer.deploy_agent_registry(
            redis_connection_string=args.redis_connection,
            cosmos_endpoint=args.cosmos_endpoint,
            cosmos_key=args.cosmos_key
        )

        # Get registry URL for agents
        registry_url = deployer.get_registry_url()
        logger.info(f"Agent Registry URL: {registry_url}")

        # Step 6: Deploy domain agents
        agent_configs = [
            {
                "name": "account-agent",
                "port": 8100,
                "min_replicas": 2,
                "max_replicas": 10,
                "env_vars": {
                    "AGENT_REGISTRY_URL": registry_url,
                    "ACCOUNT_MCP_URL": "http://account-mcp:8070",
                    "LIMITS_MCP_URL": "http://limits-mcp:8073",
                    "AZURE_OPENAI_ENDPOINT": args.openai_endpoint,
                    "AZURE_OPENAI_API_KEY": args.openai_key,
                }
            },
            {
                "name": "transaction-agent",
                "port": 8101,
                "min_replicas": 2,
                "max_replicas": 10,
                "env_vars": {
                    "AGENT_REGISTRY_URL": registry_url,
                    "TRANSACTION_MCP_URL": "http://transaction-mcp:8071",
                    "AZURE_OPENAI_ENDPOINT": args.openai_endpoint,
                    "AZURE_OPENAI_API_KEY": args.openai_key,
                }
            },
            {
                "name": "payment-agent",
                "port": 8102,
                "min_replicas": 2,
                "max_replicas": 10,
                "env_vars": {
                    "AGENT_REGISTRY_URL": registry_url,
                    "PAYMENT_MCP_URL": "http://payment-mcp:8072",
                    "LIMITS_MCP_URL": "http://limits-mcp:8073",
                    "AZURE_OPENAI_ENDPOINT": args.openai_endpoint,
                    "AZURE_OPENAI_API_KEY": args.openai_key,
                }
            },
        ]

        for agent_config in agent_configs:
            try:
                deployer.deploy_domain_agent(
                    agent_name=agent_config["name"],
                    port=agent_config["port"],
                    min_replicas=agent_config["min_replicas"],
                    max_replicas=agent_config["max_replicas"],
                    env_vars=agent_config["env_vars"]
                )
            except Exception as e:
                logger.error(f"Failed to deploy {agent_config['name']}: {e}")
                logger.info("Continuing with next agent...")

        logger.info("✅ Deployment completed successfully!")
        logger.info(f"Agent Registry: {registry_url}")

    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
