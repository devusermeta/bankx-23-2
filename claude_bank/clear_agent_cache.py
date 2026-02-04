"""
Clear cached agents and threads to ensure fresh start

Run this after code changes to both agent handlers to ensure
they reload with the updated tool implementation.
"""
import httpx
import asyncio

SERVICES = [
    ("Product Info Agent", "http://localhost:9004/health"),
    ("AI Money Coach Agent", "http://localhost:9005/health"),
    ("Escalation Agent", "http://localhost:9006/health"),
]

async def check_service(name: str, url: str):
    """Check if a service is running"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                print(f"✅ {name} is running")
                return True
            else:
                print(f"⚠️  {name} returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ {name} is not reachable: {e}")
        return False

async def main():
    print("🔍 Checking A2A Agent Services...\n")
    
    all_healthy = True
    for name, url in SERVICES:
        healthy = await check_service(name, url)
        if not healthy:
            all_healthy = False
    
    print("\n" + "="*60)
    if all_healthy:
        print("✅ All services are running!")
        print("\n📝 Next steps:")
        print("1. Stop all agent services (Ctrl+C in their terminals)")
        print("2. Restart them to clear cached agents:")
        print("   - Product Info: cd claude_bank\\app/agents/prodinfo-faq-agent-a2a; uv run --prerelease=allow python main.py")
        print("   - AI Money Coach: cd claude_bank\\app/agents/ai-money-coach-agent-a2a; uv run --prerelease=allow python main.py")
        print("   - Escalation: cd claude_bank\\app/agents/escalation-agent-a2a; uv run --prerelease=allow python main.py")
        print("3. Test the escalation flow with a fresh conversation")
    else:
        print("⚠️  Some services are not running. Start them before testing.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
