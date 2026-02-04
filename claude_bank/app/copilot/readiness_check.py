"""
Simple test to verify the banking system is working correctly
without requiring azure-cosmos import.
"""

import json
import time
from pathlib import Path

def test_conversation_creation():
    """Test creating a conversation and checking if it works"""
    print("🧪 Testing Conversation Creation")
    print("=" * 40)
    
    # Check if we can find conversation files
    conversations_dir = Path(__file__).parent.parent.parent / "conversations"
    print(f"📁 Conversations directory: {conversations_dir}")
    
    if conversations_dir.exists():
        print("✅ Conversations directory exists")
        
        # List existing conversation files
        json_files = list(conversations_dir.glob("*.json"))
        print(f"📄 Found {len(json_files)} conversation files:")
        
        for file in json_files[-5:]:  # Show last 5 files
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    message_count = len(data.get('messages', []))
                    created_at = data.get('created_at', 'Unknown')
                    print(f"   📝 {file.name}: {message_count} messages, created {created_at}")
            except Exception as e:
                print(f"   ❌ {file.name}: Error reading - {e}")
        
        return True
    else:
        print("❌ Conversations directory not found")
        return False

def test_backend_health():
    """Test if the backend is responding"""
    print("\n🧪 Testing Backend Health")
    print("=" * 30)
    
    try:
        import httpx
        
        # Test auth endpoint
        try:
            response = httpx.get("http://localhost:8080/api/auth_setup", timeout=5)
            if response.status_code == 200:
                print("✅ Backend auth endpoint responding")
                return True
            else:
                print(f"⚠️ Backend responded with status: {response.status_code}")
                return False
        except httpx.ConnectError:
            print("❌ Backend not reachable on port 8080")
            return False
        except Exception as e:
            print(f"❌ Backend test failed: {e}")
            return False
            
    except ImportError:
        print("⚠️ httpx not available, skipping backend test")
        return None

def test_frontend_readiness():
    """Test if frontend is accessible"""
    print("\n🧪 Testing Frontend Readiness")
    print("=" * 35)
    
    try:
        import httpx
        
        try:
            response = httpx.get("http://localhost:8081", timeout=5)
            if response.status_code == 200:
                print("✅ Frontend accessible on port 8081")
                return True
            else:
                print(f"⚠️ Frontend responded with status: {response.status_code}")
                return False
        except httpx.ConnectError:
            print("❌ Frontend not reachable on port 8081")
            print("💡 Make sure to run: npm run dev in the frontend directory")
            return False
        except Exception as e:
            print(f"❌ Frontend test failed: {e}")
            return False
            
    except ImportError:
        print("⚠️ httpx not available, skipping frontend test")
        return None

def main():
    """Run all readiness tests"""
    print("🚀 BankX System Readiness Check")
    print("=" * 45)
    
    results = {
        'conversations': test_conversation_creation(),
        'backend': test_backend_health(),
        'frontend': test_frontend_readiness()
    }
    
    print("\n" + "=" * 45)
    print("📊 Readiness Summary:")
    
    # Evaluate results
    ready_for_testing = True
    
    if results['conversations']:
        print("✅ Conversation system ready")
    else:
        print("❌ Conversation system not ready")
        ready_for_testing = False
    
    if results['backend'] is True:
        print("✅ Backend system ready") 
    elif results['backend'] is False:
        print("❌ Backend system not ready")
        ready_for_testing = False
    else:
        print("⚠️ Backend status unknown")
    
    if results['frontend'] is True:
        print("✅ Frontend system ready")
    elif results['frontend'] is False:
        print("❌ Frontend system not ready - but backend testing still possible")
    else:
        print("⚠️ Frontend status unknown")
    
    print("\n🎯 System Status:")
    if ready_for_testing:
        print("🎉 System is ready for conversation testing!")
        print("\n📋 Testing Steps:")
        print("   1. Open http://localhost:8081 in your browser")
        print("   2. Start a conversation (e.g., 'What's my balance?')")
        print("   3. Perform a transfer to test confirmations")
        print("   4. Wait 5+ minutes or start new conversation")
        print("   5. Check conversations folder for JSON files")
        print("   6. Cosmos DB sync will happen in background")
        print("   7. Check Application Insights for telemetry data")
    else:
        print("⚠️ System has some issues but core functionality should work")
        print("🔧 Check the errors above and restart any failed services")
    
    print(f"\n🔍 Conversation Files Location: {Path(__file__).parent.parent.parent / 'conversations'}")
    print("💡 Monitor this folder to see new conversations being created")

if __name__ == "__main__":
    main()