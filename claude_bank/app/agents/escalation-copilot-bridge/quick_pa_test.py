"""
Quick diagnostic tool for Power Automate connection issues.
Run this to diagnose 502 errors before starting the A2A server.
"""

import asyncio
import httpx
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

async def quick_power_automate_test():
    """Quick test of Power Automate flow with detailed diagnostics"""
    
    flow_url = os.getenv("POWER_AUTOMATE_FLOW_URL")
    if not flow_url:
        print("❌ POWER_AUTOMATE_FLOW_URL not found in .env file")
        return False
    
    print("🔍 POWER AUTOMATE QUICK TEST")
    print("=" * 50)
    print(f"📍 Flow URL: {flow_url[:80]}...")
    print(f"🕐 Timestamp: {datetime.now().strftime('%H:%M:%S')}")
    
    # Test payload (matches Power Automate flow schema)
    test_payload = {
        "customer_id": "TEST-QUICK-001",
        "customer_email": "startup-test@example.com",
        "customer_name": "Startup Test", 
        "description": "Connection test from diagnostic tool",
        "priority": "Medium"
    }
    
    print(f"\n📤 Sending test payload...")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            start_time = asyncio.get_event_loop().time()
            
            response = await client.post(
                flow_url,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            
            print(f"📊 Response received in {elapsed:.1f}ms")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ SUCCESS: Power Automate flow is working!")
                print("🎯 The A2A server should start without connection errors")
                return True
                
            elif response.status_code == 502:
                print("❌ 502 BAD GATEWAY: Flow reachable but internal error")
                
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', 'Unknown')
                    print(f"📋 Error Details: {error_msg}")
                except:
                    print(f"📋 Raw Response: {response.text[:200]}")
                
                print("\n🔧 LIKELY CAUSES:")
                print("   1. 🤖 Copilot Studio bot not published")
                print("   2. 📧 Outlook connector authentication expired")
                print("   3. 📊 Excel connector permissions lost")
                print("   4. ⚡ Power Automate flow disabled")
                
                print("\n🎯 IMMEDIATE FIXES:")
                print("   1. Go to https://make.powerautomate.com")
                print("   2. Find your escalation flow and ensure it's 'On'")
                print("   3. Check run history for specific errors")
                print("   4. Re-publish your Copilot Studio bot")
                
                return False
                
            elif response.status_code == 500:
                print("❌ 500 INTERNAL SERVER ERROR: Flow configuration issue")
                
                try:
                    error_data = response.json()
                    print(f"📋 Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"📋 Raw Response: {response.text[:200]}")
                
                return False
                
            else:
                print(f"⚠️  UNEXPECTED STATUS: {response.status_code}")
                print(f"📋 Response: {response.text[:200]}")
                return False
    
    except httpx.TimeoutException:
        print("❌ TIMEOUT: Power Automate flow not responding")
        print("🔧 Try increasing timeout or check service status")
        return False
        
    except httpx.ConnectError as e:
        print("❌ CONNECTION ERROR: Cannot reach Power Automate")
        print(f"📋 Details: {e}")
        print("🔧 Check URL and network connectivity")
        return False
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

async def main():
    """Main diagnostic runner"""
    
    print("🚨 POWER AUTOMATE STARTUP DIAGNOSTICS")
    print("This tool tests the same connection that fails during A2A server startup")
    print()
    
    success = await quick_power_automate_test()
    
    print("\n" + "=" * 50)
    
    if success:
        print("🎉 RESULT: Power Automate is working!")
        print("✅ Your A2A server should start without connection errors")
        print("🚀 Run: python main.py")
    else:
        print("🚨 RESULT: Power Automate has issues") 
        print("❌ A2A server will show connection warnings during startup")
        print("🔧 Fix the Power Automate issues above first")
        print("📞 Service will still start - you can test connection later")
    
    print("\n🔄 After fixing issues, re-test with:")
    print("   python quick_pa_test.py")

if __name__ == "__main__":
    asyncio.run(main())