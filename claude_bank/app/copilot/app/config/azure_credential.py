import os
from azure.identity import ManagedIdentityCredential, AzureCliCredential
from azure.identity.aio import ManagedIdentityCredential as AioManagedIdentityCredential, AzureCliCredential as AioCliCredential
from app.config.settings import settings

async def get_azure_credential_async():
    """
    Returns an Azure credential asynchronously based on the application environment.

    Priority order:
    1. Service Principal (if AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET all set)
    2. Azure CLI (if PROFILE='dev' and no service principal)
    3. Managed Identity (production fallback)

    Returns:
        Credential object: Service Principal, CLI, or Managed Identity credential.
    """
    # Check if service principal credentials are available (Docker/CI/CD)
    if (os.getenv('AZURE_CLIENT_ID') and 
        os.getenv('AZURE_TENANT_ID') and 
        os.getenv('AZURE_CLIENT_SECRET')):
        from azure.identity.aio import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET')
        )
    elif settings.PROFILE == 'dev':
        return AioCliCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    else:
        return AioManagedIdentityCredential(client_id=settings.AZURE_CLIENT_ID)

def get_async_azure_credential():
    """
    Returns an Azure credential asynchronously based on the application environment.

    Priority order:
    1. Service Principal (if AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET all set)
    2. Azure CLI (if PROFILE='dev' and no service principal)
    3. Managed Identity (production fallback)

    Returns:
        Credential object: Service Principal, CLI, or Managed Identity credential.
    """
    # Check if service principal credentials are available (Docker/CI/CD)
    if (os.getenv('AZURE_CLIENT_ID') and 
        os.getenv('AZURE_TENANT_ID') and 
        os.getenv('AZURE_CLIENT_SECRET')):
        from azure.identity.aio import ClientSecretCredential
        return ClientSecretCredential(
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET')
        )
    elif settings.PROFILE == 'dev':
        return AioCliCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    else:
        return AioManagedIdentityCredential(client_id=settings.AZURE_CLIENT_ID)

def get_azure_credential():
    """
    Returns an Azure credential based on the application environment.

    If the environment is 'dev', it uses DefaultAzureCredential.
    Otherwise, it uses ManagedIdentityCredential.

    Args:
        client_id (str, optional): The client ID for the Managed Identity Credential.

    Returns:
        Credential object: Either DefaultAzureCredential or ManagedIdentityCredential.
    """
    if settings.PROFILE == 'dev':
        return AzureCliCredential()  # CodeQL [SM05139] Okay use of DefaultAzureCredential as it is only used in development
    else:
        return ManagedIdentityCredential(client_id=settings.AZURE_CLIENT_ID)
