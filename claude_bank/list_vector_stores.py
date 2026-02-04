"""
Check vector stores in the Azure AI Foundry project
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment
env_file = Path(__file__).parent / "app" / "copilot" / ".env"
load_dotenv(env_file, override=True)

print("\n" + "="*100)
print("List All Vector Stores in Azure AI Foundry Project")
print("="*100 + "\n")

# Get configuration
endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print(f"Endpoint: {endpoint[:80]}...\n")

# Create client
credential = DefaultAzureCredential()
client = AIProjectClient(endpoint, credential=credential, logging_enable=True)

print("Fetching all vector stores...\n")

try:
    # List all vector stores
    vector_stores = client.agents.vector_stores.list()
    
    vs_list = list(vector_stores)
    print(f"Found {len(vs_list)} vector stores:\n")
    print("="*100)
    
    for i, vs in enumerate(vs_list, 1):
        print(f"\nVector Store {i}:")
        print(f"  ID: {vs.id}")
        print(f"  Name: {vs.name}")
        print(f"  Status: {vs.status}")
        print(f"  File counts: {vs.file_counts}")
        print(f"  Created: {vs.created_at}")
        print(f"  {'-'*96}")
        
        # Try to list files in this vector store
        try:
            files = client.agents.vector_stores.list_files(vs.id)
            files_list = list(files)
            print(f"  Files in this vector store: {len(files_list)}")
            for j, file in enumerate(files_list[:5], 1):  # Show first 5 files
                print(f"    File {j}: {file.id}")
        except Exception as e:
            print(f"  ❌ Error listing files: {e}")
    
    print(f"\n" + "="*100)
    print("Vector Store IDs for .env:")
    print("="*100)
    
    for vs in vs_list:
        if "ProdInfo" in vs.name or "Product" in vs.name or "FAQ" in vs.name or "Savings" in vs.name:
            print(f"PRODINFO_FAQ_VECTOR_STORE_IDS={vs.id}  # {vs.name} - {vs.file_counts}")
        elif "Money" in vs.name or "Coach" in vs.name or "Finance" in vs.name:
            print(f"AI_MONEY_COACH_VECTOR_STORE_IDS={vs.id}  # {vs.name} - {vs.file_counts}")
    
    print("="*100 + "\n")
    
except Exception as e:
    print(f"❌ Error listing vector stores: {e}")
    import traceback
    traceback.print_exc()
