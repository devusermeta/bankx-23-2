"""
Validate that the updated agent handlers compile and have all required methods
"""
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.getcwd(), 'app', 'agents', 'prodinfo-faq-agent-a2a'))
sys.path.insert(0, os.path.join(os.getcwd(), 'app', 'agents', 'ai-money-coach-agent-a2a'))

print("Validating Agent Handlers...")
print("=" * 60)

# Validate Product Info Agent
print("\n1. Product Info Agent Handler")
print("-" * 60)
try:
    sys.path.insert(0, 'app/agents/prodinfo-faq-agent-a2a')
    import agent_handler as prodinfo_module
    print("OK Module imports successfully")
    
    # Check class exists
    handler_class = prodinfo_module.ProdInfoFAQAgentHandler
    print(f"OK ProdInfoFAQAgentHandler class exists")
    
    # Check tool function exists
    tool_func = prodinfo_module.create_support_ticket_tool
    print(f"OK create_support_ticket_tool function exists")
    
    # Check key methods
    methods = ['__init__', 'get_agent', 'process_message', 'call_escalation_agent', 'clear_cache']
    for method in methods:
        if hasattr(handler_class, method):
            print(f"OK Method '{method}' exists")
        else:
            print(f"ERROR Method '{method}' missing!")
    
    print("SUCCESS Product Info Agent validation passed!")
    
except Exception as e:
    print(f"ERROR Product Info Agent validation failed: {e}")
    import traceback
    traceback.print_exc()

# Validate AI Money Coach Agent
print("\n2. AI Money Coach Agent Handler")
print("-" * 60)
try:
    sys.path.insert(0, 'app/agents/ai-money-coach-agent-a2a')
    import agent_handler as coach_module
    print("OK Module imports successfully")
    
    # Check class exists
    handler_class = coach_module.AIMoneyCoachAgentHandler
    print(f"OK AIMoneyCoachAgentHandler class exists")
    
    # Check tool function exists
    tool_func = coach_module.create_support_ticket_tool
    print(f"OK create_support_ticket_tool function exists")
    
    # Check key methods
    methods = ['__init__', 'get_agent', 'process_message', 'call_escalation_agent', 'clear_cache']
    for method in methods:
        if hasattr(handler_class, method):
            print(f"OK Method '{method}' exists")
        else:
            print(f"ERROR Method '{method}' missing!")
    
    print("SUCCESS AI Money Coach Agent validation passed!")
    
except Exception as e:
    print(f"ERROR AI Money Coach Agent validation failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("All validations complete!")
print("=" * 60)
