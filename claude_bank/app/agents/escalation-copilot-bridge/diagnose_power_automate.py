"""
Power Automate Flow Diagnostics
This script helps diagnose 502 Bad Gateway issues with Power Automate flows.
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Print a diagnostic step"""
    print(f"\n📋 Step {step}: {description}")
    print("-" * 40)

async def test_basic_connectivity():
    """Test basic connectivity to Power Automate"""
    print_step(1, "Testing Basic Connectivity")
    
    flow_url = os.getenv("POWER_AUTOMATE_FLOW_URL")
    if not flow_url:
        print("❌ POWER_AUTOMATE_FLOW_URL not found in .env")
        return False
    
    print(f"📍 Flow URL: {flow_url[:100]}...")
    
    try:
        # Test with minimal payload
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("🔄 Sending minimal test request...")
            
            minimal_payload = {
                "customer_id": "TEST-DIAG-001",
                "customer_email": "test@example.com",
                "customer_name": "Test User",
                "description": "Test ticket",
                "priority": "Medium"
            }
            
            response = await client.post(flow_url, json=minimal_payload)
            
            print(f"📊 Status Code: {response.status_code}")
            print(f"📊 Response Headers: {dict(response.headers)}")
            
            if response.status_code == 502:
                print("❌ 502 Bad Gateway - Flow or downstream service failing")
                try:
                    error_data = response.json()
                    print(f"📋 Error Details: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📋 Raw Response: {response.text}")
                return False
            elif response.status_code == 200:
                print("✅ Flow is responding correctly")
                return True
            else:
                print(f"⚠️ Unexpected status code: {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

async def test_flow_components():
    """Test individual flow components"""
    print_step(2, "Testing Flow Components")
    
    print("🔍 Potential Issues to Check in Power Automate:")
    print("1. 📧 Outlook Connector - Authentication expired?")
    print("2. 📊 Excel Connector - File permissions?") 
    print("3. 🤖 Copilot Studio Connector - Bot published?")
    print("4. ⚡ Flow Status - Enabled and running?")
    print("5. 🔐 Connections - All authenticated?")
    
    # Test without Copilot Studio (if possible)
    flow_url = os.getenv("POWER_AUTOMATE_FLOW_URL")
    
    try:
        print("\n🧪 Testing with bypass payload (skip Copilot Studio)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            bypass_payload = {
                "customer_id": "TEST-BYPASS-001",
                "customer_email": "diagnostics@example.com",
                "customer_name": "Diagnostic Test",
                "description": "Direct bypass test - skip Copilot Studio processing",
                "priority": "Medium",
                "bypass_copilot": True  # Custom flag
            }
            
            response = await client.post(flow_url, json=bypass_payload)
            
            if response.status_code == 502:
                print("❌ Still 502 - Issue is NOT Copilot Studio")
                print("🔍 Problem likely in Outlook/Excel connectors")
            elif response.status_code == 200:
                print("✅ Bypass works - Issue IS Copilot Studio")
                print("🔍 Check bot publication and Direct Line connection")
            else:
                print(f"ℹ️ Different result: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Bypass test failed: {e}")

async def test_power_platform_status():
    """Check Power Platform service status"""
    print_step(3, "Checking Power Platform Status")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check Microsoft service status
            print("🌐 Checking Microsoft service health...")
            
            # This is a public endpoint for service health
            status_response = await client.get("https://status.office.com/api/v1.0/status")
            
            if status_response.status_code == 200:
                print("✅ Microsoft services appear healthy")
            else:
                print(f"⚠️ Service status check inconclusive: {status_response.status_code}")
                
    except Exception as e:
        print(f"ℹ️ Could not check service status: {e}")
    
    print("\n🔍 Manual checks needed:")
    print("1. Go to https://make.powerautomate.com")
    print("2. Check if your flow is 'On' (enabled)")  
    print("3. View run history for error details")
    print("4. Test connections individually")

async def generate_diagnostics_report():
    """Generate a comprehensive diagnostics report"""
    print_section("Power Automate Flow Diagnostics Report")
    
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    
    # Environment check
    print_step("ENV", "Environment Configuration")
    flow_url = os.getenv("POWER_AUTOMATE_FLOW_URL")
    bot_id = os.getenv("COPILOT_BOT_ID")
    
    print(f"🔗 Flow URL: {'✅ Set' if flow_url else '❌ Missing'}")
    print(f"🤖 Bot ID: {'✅ Set' if bot_id else '❌ Missing'}")
    
    if flow_url:
        print(f"🌐 Domain: {flow_url.split('/')[2]}")
    
    # Test connectivity
    connectivity_ok = await test_basic_connectivity()
    
    # Test components
    await test_flow_components()
    
    # Test platform status
    await test_power_platform_status()
    
    # Summary
    print_section("DIAGNOSIS SUMMARY")
    
    if not connectivity_ok:
        print("❌ ISSUE IDENTIFIED: 502 Bad Gateway from Power Automate")
        print("\n🔧 RECOMMENDED FIXES:")
        print("1. Check Power Automate flow status (On/Off)")
        print("2. Verify Copilot Studio bot is published")
        print("3. Test Outlook connector authentication")
        print("4. Test Excel connector permissions")
        print("5. Check flow run history for specific errors")
        
        print(f"\n🌐 Quick Links:")
        print(f"   Power Automate: https://make.powerautomate.com")
        print(f"   Copilot Studio: https://copilotstudio.microsoft.com")
        print(f"   Service Health: https://status.office.com")
        
    return connectivity_ok

async def create_test_flow_request():
    """Create a simplified test request for manual testing"""
    print_section("Manual Test Request")
    
    flow_url = os.getenv("POWER_AUTOMATE_FLOW_URL")
    
    test_payload = {
        "customer_id": "TEST-MANUAL-001",
        "customer_email": "test@example.com",
        "customer_name": "Manual Test",
        "description": "Manual test from diagnostics",
        "priority": "Medium"
    }
    
    print("📋 Use this payload to test your flow manually:")
    print(f"URL: {flow_url}")
    print("Method: POST")
    print("Headers: Content-Type: application/json")
    print("Body:")
    print(json.dumps(test_payload, indent=2))
    
    print(f"\n🌐 Or test in browser/Postman:")
    print(f"curl -X POST '{flow_url}' \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{json.dumps(test_payload)}'")

async def main():
    """Main diagnostic runner"""
    print("🚨 POWER AUTOMATE FLOW DIAGNOSTICS")
    print("This tool helps diagnose 502 Bad Gateway errors")
    
    await generate_diagnostics_report()
    
    print("\n")
    await create_test_flow_request()
    
    print_section("NEXT STEPS")
    print("1. 🔧 Fix issues identified above")
    print("2. 🧪 Test flow manually in Power Automate")  
    print("3. 🔄 Re-run A2A escalation test")
    print("4. 📞 Contact support if issues persist")

if __name__ == "__main__":
    asyncio.run(main())