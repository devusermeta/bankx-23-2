"""
Test script to verify Cosmos DB sync functionality status.
This script will check if cosmos_sync is working or disabled.
"""

import os
import sys
from pathlib import Path

def test_environment_variables():
    """Test if Cosmos DB environment variables are accessible"""
    print("🔍 Testing Environment Variables")
    print("=" * 40)
    
    required_vars = ["COSMOS_ENDPOINT", "COSMOS_KEY", "COSMOS_DATABASE", "COSMOS_CONTAINER"]
    
    # Load from .env file
    try:
        from dotenv import load_dotenv
        load_dotenv(".env")
        print("✅ Environment loaded from .env")
    except ImportError:
        print("⚠️ python-dotenv not available")
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "KEY" in var:
                masked = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"   ✅ {var}: {masked}")
            else:
                print(f"   ✅ {var}: {value}")
        else:
            print(f"   ❌ {var}: Not set")
            return False
    
    return True

def test_cosmos_sync_import():
    """Test if cosmos_sync can be imported"""
    print("\n🔍 Testing cosmos_sync Import")
    print("=" * 35)
    
    try:
        # Add conversations directory to path
        conversations_path = str(Path(__file__).parent.parent.parent / "conversations")
        if conversations_path not in sys.path:
            sys.path.insert(0, conversations_path)
        print(f"✅ Added conversations path: {conversations_path}")
        
        # Try to import cosmos_sync
        from cosmos_sync import create_cosmos_sync_from_env
        print("✅ cosmos_sync module imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ cosmos_sync import failed: {e}")
        return False

def test_azure_cosmos_availability():
    """Test if azure-cosmos package is available"""
    print("\n🔍 Testing azure-cosmos Package")
    print("=" * 35)
    
    try:
        import azure.cosmos
        print("✅ azure-cosmos package available")
        return True
    except ImportError as e:
        print(f"❌ azure-cosmos not available: {e}")
        return False

def test_cosmos_sync_creation():
    """Test if CosmosSync can be created"""
    print("\n🔍 Testing CosmosSync Creation")
    print("=" * 35)
    
    try:
        # Import required modules
        conversations_path = str(Path(__file__).parent.parent.parent / "conversations")
        if conversations_path not in sys.path:
            sys.path.insert(0, conversations_path)
        
        from cosmos_sync import create_cosmos_sync_from_env
        
        # Try to create CosmosSync instance
        cosmos_sync = create_cosmos_sync_from_env()
        
        if cosmos_sync:
            print("✅ CosmosSync instance created successfully")
            
            # Test sync status
            status = cosmos_sync.get_sync_status()
            print(f"✅ Sync status: {status}")
            return True
        else:
            print("❌ CosmosSync instance creation returned None")
            return False
            
    except Exception as e:
        print(f"❌ CosmosSync creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversation_manager_cosmos_integration():
    """Test if ConversationManager has Cosmos DB integration"""
    print("\n🔍 Testing ConversationManager Cosmos Integration")
    print("=" * 50)
    
    try:
        # Add conversations directory to path
        conversations_path = str(Path(__file__).parent.parent.parent / "conversations")
        if conversations_path not in sys.path:
            sys.path.insert(0, conversations_path)
        
        from conversation_manager import get_conversation_manager
        
        conv_manager = get_conversation_manager()
        
        if conv_manager.cosmos_sync:
            print("✅ ConversationManager has Cosmos DB sync ENABLED")
            
            # Get sync status
            status = conv_manager.get_active_threads_status()
            print(f"✅ Thread status: {status}")
            return True
        else:
            print("❌ ConversationManager has Cosmos DB sync DISABLED")
            print("   This means conversations will only be stored in JSON files")
            return False
            
    except Exception as e:
        print(f"❌ ConversationManager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_cosmos_db_connectivity():
    """Test actual connectivity to Cosmos DB"""
    print("\n🔍 Testing Cosmos DB Connectivity")
    print("=" * 40)
    
    try:
        from azure.cosmos import CosmosClient
        
        endpoint = os.getenv("COSMOS_ENDPOINT")
        key = os.getenv("COSMOS_KEY")
        database_name = os.getenv("COSMOS_DATABASE", "BankX")
        container_name = os.getenv("COSMOS_CONTAINER", "Conversations")
        
        if not endpoint or not key:
            print("❌ Missing Cosmos DB credentials")
            return False
        
        # Test connection
        client = CosmosClient(endpoint, credential=key)
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        
        # Test read operation
        container_info = container.read()
        print(f"✅ Successfully connected to Cosmos DB")
        print(f"   Database: {database_name}")
        print(f"   Container: {container_name}")
        print(f"   Partition Key: {container_info.get('partitionKey', {}).get('paths', ['Unknown'])}")
        
        # Check if any documents exist
        try:
            items = list(container.query_items("SELECT VALUE COUNT(1) FROM c", enable_cross_partition_query=True))
            doc_count = items[0] if items else 0
            print(f"   Documents: {doc_count}")
        except Exception as e:
            print(f"   Documents: Unable to count ({e})")
        
        return True
        
    except Exception as e:
        print(f"❌ Cosmos DB connectivity failed: {e}")
        return False

def main():
    """Run comprehensive cosmos_sync status check"""
    print("🚀 Cosmos DB Sync Status Check")
    print("=" * 50)
    
    results = {}
    results['env_vars'] = test_environment_variables()
    results['cosmos_sync_import'] = test_cosmos_sync_import()
    results['azure_cosmos'] = test_azure_cosmos_availability()
    results['cosmos_sync_creation'] = test_cosmos_sync_creation()
    results['conversation_manager'] = test_conversation_manager_cosmos_integration()
    results['connectivity'] = check_cosmos_db_connectivity()
    
    print("\n" + "=" * 50)
    print("📊 Cosmos DB Sync Status Summary:")
    print("=" * 50)
    
    if results['env_vars']:
        print("✅ Environment variables configured")
    else:
        print("❌ Environment variables missing")
    
    if results['cosmos_sync_import']:
        print("✅ cosmos_sync module can be imported")
    else:
        print("❌ cosmos_sync module cannot be imported")
    
    if results['azure_cosmos']:
        print("✅ azure-cosmos package available")
    else:
        print("❌ azure-cosmos package missing")
    
    if results['cosmos_sync_creation']:
        print("✅ CosmosSync can be created")
    else:
        print("❌ CosmosSync creation fails")
    
    if results['conversation_manager']:
        print("✅ ConversationManager has Cosmos sync ENABLED")
    else:
        print("❌ ConversationManager has Cosmos sync DISABLED")
    
    if results['connectivity']:
        print("✅ Cosmos DB is accessible")
    else:
        print("❌ Cosmos DB is not accessible")
    
    # Overall assessment
    print("\n🎯 Overall Assessment:")
    if all(results.values()):
        print("🎉 Cosmos DB sync is FULLY OPERATIONAL!")
        print("   Conversations will be synced to Cosmos DB after 5 minutes of inactivity")
    elif results['env_vars'] and results['connectivity']:
        print("⚠️ Cosmos DB sync is PARTIALLY WORKING")
        print("   Resources exist but sync functionality may be disabled")
    else:
        print("❌ Cosmos DB sync is NOT WORKING")
        print("   Conversations will only be stored in JSON files")
    
    print("\n💡 Recommendations:")
    if not results['azure_cosmos']:
        print("   🔧 Install azure-cosmos: pip install azure-cosmos==4.7.0")
    if not results['cosmos_sync_creation']:
        print("   🔧 Check cosmos_sync.py for errors")
    if not results['conversation_manager']:
        print("   🔧 Check conversation_manager.py cosmos_sync integration")

if __name__ == "__main__":
    main()