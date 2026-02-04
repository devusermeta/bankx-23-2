"""
Test using AIProjectClient.get_openai_client() with new agent format
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print("="*80)
print("Testing AIProjectClient.get_openai_client() with new agent format")
print("="*80)
print()

credential = AzureCliCredential()

# Get project client
project_client = AIProjectClient(
    credential=credential,
    endpoint=FOUNDRY_PROJECT_ENDPOINT
)

# Get the agent
agent = project_client.agents.get_version('AIMoneyCoachAgent', '2')
print(f"✅ Agent ID from AIProjectClient: {agent.id}")
print()

# Get OpenAI client
print("Getting OpenAI client from AIProjectClient...")
openai_client = project_client.get_openai_client()
print(f"✅ OpenAI client type: {type(openai_client)}")
print(f"   Has beta.assistants: {hasattr(openai_client.beta, 'assistants')}")
print(f"   Has beta.threads: {hasattr(openai_client.beta, 'threads')}")
print()

# Try to retrieve the agent using OpenAI client
print("Testing beta.assistants.retrieve() with versioned agent ID...")
print("-" * 80)

try:
    retrieved_agent = openai_client.beta.assistants.retrieve(agent.id)
    print(f"✅ SUCCESS! Retrieved agent: {retrieved_agent.id}")
    print(f"   Name: {retrieved_agent.name}")
    print(f"   Model: {retrieved_agent.model}")
    
    # Try to create a thread
    print()
    print("Testing thread creation...")
    thread = openai_client.beta.threads.create()
    print(f"✅ Thread created: {thread.id}")
    
    # Try to create a message
    print()
    print("Testing message creation...")
    message = openai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="What is financial planning?"
    )
    print(f"✅ Message created: {message.id}")
    
    # Try to create a run with streaming
    print()
    print("Testing run creation with streaming...")
    with openai_client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=agent.id  # Using the versioned ID AIMoneyCoachAgent:2
    ) as stream:
        print("✅ Stream started!")
        for event in stream:
            if event.event == 'thread.message.delta':
                if hasattr(event.data, 'delta') and hasattr(event.data.delta, 'content'):
                    for content in event.data.delta.content:
                        if hasattr(content, 'text') and hasattr(content.text, 'value'):
                            print(content.text.value, end='', flush=True)
            elif event.event == 'thread.run.completed':
                print("\n✅ Run completed!")
                break
    
    print()
    print("="*80)
    print("🎉 SUCCESS! AIProjectClient.get_openai_client() works with new format!")
    print("="*80)
    print()
    print("SOLUTION: Use AIProjectClient.get_openai_client() instead of agent-framework!")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
