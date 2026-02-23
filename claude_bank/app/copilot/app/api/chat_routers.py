from fastapi import APIRouter, HTTPException, Depends
from typing import List, Any
import logging
import asyncio
import uuid
import time

# Foundry Agent based dependencies
from app.agents.foundry.supervisor_agent_foundry import SupervisorAgent
from app.config.container_foundry import Container
from app.conversation_state_manager import get_conversation_state_manager, is_continuation_message

# Azure Chat based agents dependencies
# from app.agents.azure_chat.supervisor_agent import SupervisorAgent
# from app.config.container_azure_chat import Container

from app.models.chat import ChatAppRequest, ChatResponse, ChatResponseMessage, ChatChoice, ChatContext, ChatDelta
from app.models.chat import ChatMessage as AppChatMessage
from app.models.user_context import UserContext
from app.api.dependencies import get_current_user
# from agent_framework import ChatMessage, Role
from dependency_injector.wiring import Provide, inject
from fastapi.responses import StreamingResponse
import json
from typing import AsyncGenerator


router = APIRouter()
logger = logging.getLogger(__name__)



# Helper function to convert messages

def _convert_string_to_chat_response(content: str, thread_id: str | None) -> ChatResponse:
    """Convert a string response to ChatResponse format."""
    chat_message = ChatResponseMessage(
        content=content,
        role="assistant",
        attachments=[]
    )
    
    context = ChatContext(
        thoughts="",
        data_points=[]
    )
    
    delta = ChatDelta(
        content=content,
        role="assistant",
        attachments=[]
    )
    
    choice = ChatChoice(
        index=0,
        message=chat_message,
        context=context,
        delta=delta
    )

    return ChatResponse(choices=[choice], threadId=thread_id if thread_id else "")

# Helper function to convert ChatAppRequest to ChatMessageList
# def _chat_app_request_to_chat_message_list(chat_request: ChatAppRequest) -> ChatMessageList:
#     """Convert a ChatAppRequest to a ChatMessageList for agent-framework threading, mapping roles appropriately."""
#     messages: list[ChatMessage] = []
#     for msg in chat_request.messages[:-1]:
#         # Map roles from ChatAppRequest to agent-framework ChatMessage roles
#         if msg.role == "user":
#             af_role = Role.USER
#         elif msg.role == "assistant":
#             af_role = Role.ASSISTANT
#         else:
#             # raise exception that role is not recognized
#             raise ValueError(f"Unrecognized role from ChatAppRequest: {msg.role}. The message content is: {msg.content} ")

#         # Create a new ChatMessage instance
#         af_message = ChatMessage(
#             role=af_role,
#             text=msg.content
#         )
#         messages.append(af_message)
#     return ChatMessageList(messages)

def _format_stream_chunk(content: str, is_final: bool = False, thread_id: str | None = None) -> str:
    """Format a chunk for streaming response in SSE (Server-Sent Events) format."""
    # logger.info(f"📤 [SSE FORMAT] content length: {len(content)}, is_final: {is_final}, thread_id: {thread_id}")
    # print(f"📤 [SSE FORMAT] Formatting chunk - content: '{content[:100]}...', is_final: {is_final}")
    
    if is_final:
        # Final chunk with full message (no context for A2A responses)
        response = {
            "choices": [{
                "index": 0,
                "delta": {
                    "content": content,
                    "role": "assistant",
                    "attachments": []
                },
                "message": {
                    "content": content,
                    "role": "assistant",
                    "attachments": []
                }
            }]
        }
        if thread_id:
            response["threadId"] = thread_id
    else:
        # Streaming chunk with delta only
        response = {
            "choices": [{
                "index": 0,
                "delta": {
                    "content": content,
                    "role": "assistant",
                    "attachments": []
                }
            }]
        }
    
    sse_data = f"data: {json.dumps(response)}\n\n"
    # print(f"📤 [SSE FORMAT] SSE data length: {len(sse_data)} bytes")
    # print(f"📤 [SSE FORMAT] First 200 chars of SSE: {sse_data[:200]}")
    
    # SSE format: "data: {json}\n\n"
    return sse_data


async def _stream_response(
    supervisor_agent: SupervisorAgent,
    user_message: str,
    thread_id: str | None,
    user_context: UserContext,
    full_message_history: List[AppChatMessage] | None = None
) -> AsyncGenerator[str, None]:
    """Stream the response from the supervisor agent."""
    full_content = ""
    final_thread_id = None
    
    logger.info(f"🧠 [THINKING SSE] Starting stream response for user: {user_context.entra_user_email}")
    
    # Get conversation state manager
    state_manager = get_conversation_state_manager()
    
    # Check if this is a continuation of an active conversation
    is_continuation = is_continuation_message(user_message)
    active_agent_info = None
    
    # Use customer_id to check for active agent (handles different thread_ids)
    if is_continuation and user_context.customer_id:
        active_agent_info = state_manager.get_active_agent(user_context.customer_id)
        if active_agent_info:
            agent_name, active_agent, old_thread_id = active_agent_info
            logger.info(f"⚡ [CONTINUATION] Continuing with {agent_name} for customer {user_context.customer_id}")
            logger.info(f"⚡ [CONTINUATION] Skipping cache + routing (saves ~12s)")
            logger.info(f"⚡ [CONTINUATION] Using thread {old_thread_id or 'will create new'}")
    
    try:
        # If continuation with active agent, use it directly
        if active_agent_info:
            agent_name, active_agent, old_thread_id = active_agent_info
            
            # Emit continuation indicator
            continuation_event = {
                "type": "thinking",
                "step": "continuation",
                "message": f"Continuing with {agent_name}",
                "status": "completed",
                "timestamp": time.time()
            }
            logger.info(f"🧠 [THINKING SSE] Sending continuation event")
            yield f"data: {json.dumps(continuation_event)}\n\n"
            
            logger.info(f"⏭️ [CONTINUATION] Thinking event yielded, now checking agent type...")
            print(f"⏭️ [CONTINUATION] Thinking event yielded, now checking agent type...")
            
            # Check if this is an A2A agent proxy
            if hasattr(active_agent, 'a2a_url') and active_agent.a2a_url:
                # A2A Agent - route via HTTP instead of build_af_agent
                logger.info(f"🔄 [CONTINUATION A2A] Routing to {agent_name} via A2A at {active_agent.a2a_url}")
                print(f"🔄 [CONTINUATION A2A] Routing to {agent_name} via A2A at {active_agent.a2a_url}")
                
                # Yield "processing" thinking event to keep SSE connection alive during A2A call
                processing_event = {
                    "type": "thinking",
                    "step": "processing",
                    "message": f"Processing with {agent_name}...",
                    "status": "in_progress",
                    "timestamp": time.time()
                }
                logger.info(f"🔄 [A2A] Sending processing event to keep connection alive")
                yield f"data: {json.dumps(processing_event)}\n\n"
                
                # Call the A2A endpoint directly
                import httpx
                try:
                    customer_id = user_context.customer_id if user_context else "Somchai"
                    
                    print("\n" + "="*80)
                    print(f"[COPILOT DEBUG] Converting message history for A2A agent")
                    print(f"[COPILOT DEBUG] full_message_history provided: {full_message_history is not None}")
                    if full_message_history:
                        print(f"[COPILOT DEBUG] Total messages in history: {len(full_message_history)}")
                        for i, msg in enumerate(full_message_history):
                            print(f"[COPILOT DEBUG]   Message {i}: role={msg.role}, content='{msg.content[:80]}...'")
                    print("="*80 + "\n")
                    
                    # Convert full message history to A2A format
                    a2a_messages = []
                    if full_message_history:
                        for msg in full_message_history:
                            a2a_messages.append({
                                "role": msg.role,
                                "content": msg.content
                            })
                    else:
                        # Fallback: just the current message
                        a2a_messages = [{"role": "user", "content": user_message}]
                    
                    # 💳 [PAYMENT FIX] Prepend username to ALL user messages for PaymentAgent
                    if agent_name in ("PaymentAgent", "Payment Agent"):
                        user_email = user_context.entra_user_email if user_context else None
                        if user_email:
                            print(f"💳 [PAYMENT FIX] Prepending username to ALL user messages in history for {agent_name}")
                            for msg in a2a_messages:
                                if msg.get("role") == "user":
                                    content = msg.get("content", "")
                                    # Only prepend if not already present
                                    if not content.startswith(f"my username is {user_email}"):
                                        msg["content"] = f"my username is {user_email}, {content}"
                            print(f"💳 [PAYMENT FIX] Fixed {len([m for m in a2a_messages if m.get('role') == 'user'])} user messages")
                        else:
                            print(f"⚠️ [PAYMENT FIX] No user_email available, skipping username prepending")
                    
                    print(f"[COPILOT DEBUG] Converted to {len(a2a_messages)} A2A messages:")
                    for i, msg in enumerate(a2a_messages):
                        print(f"[COPILOT DEBUG]   A2A Message {i}: role={msg['role']}, content='{msg['content'][:80]}...'")
                    
                    a2a_request = {
                        "messages": a2a_messages,  # Full conversation history
                        "thread_id": old_thread_id or thread_id or f"thread_{customer_id}",
                        "customer_id": customer_id,
                        "stream": False,
                    }
                    
                    print("\n" + "="*80)
                    print(f"[COPILOT DEBUG] A2A Request Payload:")
                    print(f"[COPILOT DEBUG]   URL: {active_agent.a2a_url}/a2a/invoke")
                    print(f"[COPILOT DEBUG]   thread_id: {a2a_request['thread_id']}")
                    print(f"[COPILOT DEBUG]   customer_id: {a2a_request['customer_id']}")
                    print(f"[COPILOT DEBUG]   messages count: {len(a2a_request['messages'])}")
                    print(f"[COPILOT DEBUG]   Full messages payload:")
                    for i, msg in enumerate(a2a_request['messages']):
                        print(f"[COPILOT DEBUG]     [{i}] role={msg['role']}, content='{msg['content']}'")
                    print("="*80 + "\n")
                    
                    logger.info(f"📡 [CONTINUATION A2A] Sending request to {active_agent.a2a_url}/a2a/invoke")
                    logger.info(f"📡 [CONTINUATION A2A] Thread: {a2a_request['thread_id']}, messages count: {len(a2a_messages)}")
                    print(f"📡 [CONTINUATION A2A] Sending request to {active_agent.a2a_url}/a2a/invoke")
                    print(f"📡 [CONTINUATION A2A] Thread: {a2a_request['thread_id']}, messages count: {len(a2a_messages)}")
                    
                    agent_response = None  # Initialize before async with block
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        response = await client.post(
                            f"{active_agent.a2a_url}/a2a/invoke",
                            json=a2a_request,
                            headers={"Content-Type": "application/json"},
                        )
                        
                        logger.info(f"📡 [CONTINUATION A2A] Received status: {response.status_code}")
                        print(f"📡 [CONTINUATION A2A] Received status: {response.status_code}")
                        
                        if response.status_code == 200:
                            result = response.json()
                            logger.info(f"📡 [CONTINUATION A2A] Result keys: {list(result.keys())}")
                            print(f"📡 [CONTINUATION A2A] Result keys: {list(result.keys())}")
                            print(f"📡 [CONTINUATION A2A] Full result: {result}")
                            
                            # Extract response content from A2A response format
                            if "messages" in result and len(result["messages"]) >= 2:
                                print(f"📡 [CONTINUATION A2A] Found {len(result['messages'])} messages")
                                assistant_message = result["messages"][-1]
                                print(f"📡 [CONTINUATION A2A] Last message: {assistant_message}")
                                agent_response = assistant_message.get("content", "")
                            else:
                                print(f"📡 [CONTINUATION A2A] No messages array, using direct content")
                                agent_response = result.get("content", "")
                            
                            logger.info(f"✅ [CONTINUATION A2A] Response length: {len(agent_response)} chars")
                            print(f"✅ [CONTINUATION A2A] Response: {agent_response[:200]}...")
                            print(f"✅ [CONTINUATION A2A] agent_response type: {type(agent_response)}, value: '{agent_response}'")
                        else:
                            error_msg = f"A2A request failed with status {response.status_code}"
                            logger.error(f"❌ [A2A] {error_msg}")
                            print(f"❌ [A2A] {error_msg}")
                    
                    # Yield response AFTER closing the httpx client connection
                    logger.info(f"🔍 [A2A YIELD] About to yield. agent_response exists: {agent_response is not None}, length: {len(agent_response) if agent_response else 0}")
                    print(f"🔍 [A2A YIELD] About to yield. agent_response exists: {agent_response is not None}, length: {len(agent_response) if agent_response else 0}")
                    
                    if agent_response:
                        # Send processing completed event
                        processing_done_event = {
                            "type": "thinking",
                            "step": "processing",
                            "message": f"{agent_name} response received",
                            "status": "completed",
                            "timestamp": time.time()
                        }
                        logger.info(f"✅ [A2A] Sending processing completed event")
                        yield f"data: {json.dumps(processing_done_event)}\n\n"
                        
                        final_thread_id = old_thread_id or thread_id
                        logger.info(f"🚀 [A2A YIELD] Creating SSE chunk for: thread={final_thread_id}, content_preview='{agent_response[:100]}...'")
                        print(f"🚀 [A2A YIELD] Creating SSE chunk for: thread={final_thread_id}, content_preview='{agent_response[:100]}...'")
                        
                        sse_chunk = _format_stream_chunk(agent_response, is_final=True, thread_id=final_thread_id)
                        
                        logger.info(f"📤 [A2A YIELD] SSE chunk created, size: {len(sse_chunk)} bytes, yielding now...")
                        print(f"📤 [A2A YIELD] SSE chunk created, size: {len(sse_chunk)} bytes, yielding now...")
                        print(f"📤 [A2A YIELD] SSE chunk content: {sse_chunk[:500]}")
                        
                        yield sse_chunk
                        
                        logger.info(f"✅ [A2A YIELD] Yield completed successfully, returning from generator")
                        print(f"✅ [A2A YIELD] Yield completed successfully, returning from generator")
                        return  # Exit generator after sending A2A response
                    else:
                        logger.error(f"❌ [A2A YIELD] agent_response is None or empty!")
                        print(f"❌ [A2A YIELD] agent_response is None or empty!")
                        yield _format_stream_chunk(f"I couldn't connect to the {agent_name.lower()} service. Please try again later.", is_final=True)
                        return  # Exit generator after sending error
                
                except Exception as e:
                    logger.error(f"❌ [A2A CONTINUATION] Error: {e}", exc_info=True)
                    print(f"❌ [A2A CONTINUATION] Error: {e}")
                    import traceback
                    traceback.print_exc()
                    yield _format_stream_chunk(f"An error occurred while processing your request: {str(e)}", is_final=True)
                    return  # Exit generator after sending error
            else:
                # In-process Agent - use build_af_agent method
                # Continue with specialist agent directly (no Supervisor)
                from app.agents.foundry.supervisor_agent_foundry import _stream_specialist_agent
                async for content, is_final, tid, thinking_event in _stream_specialist_agent(
                    active_agent, 
                    user_message, 
                    old_thread_id or thread_id,  # Use old thread if available
                    user_context
                ):
                    if thinking_event:
                        logger.info(f"🧠 [THINKING SSE] Sending thinking event: {thinking_event.get('step')} - {thinking_event.get('status')}")
                        yield f"data: {json.dumps(thinking_event)}\n\n"
                        continue
                    
                    if is_final:
                        final_thread_id = tid
                        full_content += content
                        logger.info(f"🧠 [THINKING SSE] Sending final chunk, thread_id: {final_thread_id}")
                        # Send final chunk with thread_id only if content was added in this iteration
                        if content:
                            yield _format_stream_chunk(full_content, is_final=True, thread_id=final_thread_id)
                        else:
                            # No new content - just send the final marker with thread_id
                            yield _format_stream_chunk("", is_final=True, thread_id=final_thread_id)
                    else:
                        full_content += content
                        yield _format_stream_chunk(content, is_final=False)
        else:
            # Normal flow: Go through Supervisor
            async for content, is_final, tid, thinking_event in supervisor_agent.processMessageStream(user_message, thread_id, user_context):
                # Handle thinking events
                if thinking_event:
                    logger.info(f"🧠 [THINKING SSE] Sending thinking event: {thinking_event.get('step')} - {thinking_event.get('status')}")
                    print(f"🧠 [THINKING SSE] Event: {thinking_event}")
                    # SSE format for thinking events
                    yield f"data: {json.dumps(thinking_event)}\n\n"
                    continue
                
                if is_final:
                    final_thread_id = tid
                    full_content += content
                    logger.info(f"🧠 [THINKING SSE] Sending final chunk, thread_id: {final_thread_id}")
                    # Send final chunk with thread_id only if content was added in this iteration
                    # Otherwise, full_content already contains everything that was streamed
                    if content:
                        # Content in final chunk - send it
                        yield _format_stream_chunk(full_content, is_final=True, thread_id=final_thread_id)
                    else:
                        # No new content - just send the final marker with thread_id
                        # The content has already been streamed in previous chunks
                        yield _format_stream_chunk("", is_final=True, thread_id=final_thread_id)
                else:
                    full_content += content
                    # Send streaming chunk
                    yield _format_stream_chunk(content, is_final=False)
    except Exception as e:
        logger.error(f"Error during streaming: {str(e)}", exc_info=True)
        # Send error as a final chunk
        error_message = f"An error occurred: {str(e)}"
        error_response = {
            "choices": [{
                "index": 0,
                "delta": {
                    "content": error_message,
                    "role": "assistant",
                    "attachments": []
                },
                "message": {
                    "content": error_message,
                    "role": "assistant",
                    "attachments": []
                },
                "context": {
                    "thoughts": "",
                    "data_points": []
                }
            }],
            "error": str(e)
        }
        if thread_id:
            error_response["threadId"] = thread_id
        # SSE format for errors
        yield f"data: {json.dumps(error_response)}\n\n"


@router.post("/chat")
@inject
async def chat(
    chat_request: ChatAppRequest,
    user_context: UserContext = Depends(get_current_user),
    supervisor_agent: SupervisorAgent = Depends(Provide[Container.supervisor_agent])
):
    """
    Chat endpoint with authentication.
    Requires a valid JWT token in the Authorization header.
    """
    if not chat_request.messages:
        raise HTTPException(status_code=400, detail="history cannot be null in Chat request")
    
    logger.info(f"Chat request from user: {user_context.entra_user_email} (customer_id: {user_context.customer_id})")
    
    # Check the request for attachments reference. If any they will be appended to user message
    last_message = chat_request.messages[-1]
    if last_message.attachments:
        # Append attachment references to the user message
        last_message.content += " " + ",".join(last_message.attachments)

    # Handle streaming vs non-streaming
    if chat_request.stream:
        try:
            # Return streaming response with SSE (Server-Sent Events)
            return StreamingResponse(
                _stream_response(
                    supervisor_agent, 
                    last_message.content, 
                    chat_request.threadId, 
                    user_context,
                    chat_request.messages  # Pass full message history
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        except Exception as e:
            logger.error(f"Error initiating stream: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    else:
        try:
            # Return regular JSON response
            response_content, thread_id = await supervisor_agent.processMessage(
                last_message.content,
                chat_request.threadId,
                user_context
            )
            
            # Convert string response to structured ChatResponse
            return _convert_string_to_chat_response(response_content, thread_id)
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@router.get("/agent-activity/{session_id}")
async def get_agent_activity(
    session_id: str,
    limit: int = 20,
    user_context: UserContext = Depends(get_current_user)
):
    """
    Get agent activity logs for a session.
    Used by frontend to display real-time agent thinking process.
    
    Args:
        session_id: Session/thread identifier
        limit: Maximum number of activities to return (most recent)
        user_context: Authenticated user context
    
    Returns:
        List of agent activities
    """
    from app.utils.agent_activity_tracker import get_activity_tracker
    
    try:
        tracker = get_activity_tracker()
        activities = tracker.get_session_activities(session_id, limit=limit)
        
        # Convert to dict for JSON response
        return {
            "session_id": session_id,
            "activities": [activity.dict() for activity in activities]
        }
    except Exception as e:
        logger.error(f"Error fetching agent activities: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching activities: {str(e)}")


@router.get("/agent-activity-stream/{session_id}")
async def stream_agent_activity(
    session_id: str,
    user_context: UserContext = Depends(get_current_user)
):
    """
    Stream agent activity logs for a session using Server-Sent Events (SSE).
    Polls for new activities every second and streams them to frontend.
    
    Args:
        session_id: Session/thread identifier
        user_context: Authenticated user context
    
    Returns:
        SSE stream of agent activities
    """
    from app.utils.agent_activity_tracker import get_activity_tracker
    import asyncio
    
    async def activity_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for agent activities"""
        tracker = get_activity_tracker()
        last_activity_count = 0
        
        try:
            # Keep streaming for up to 5 minutes
            for _ in range(300):  # 300 seconds = 5 minutes
                activities = tracker.get_session_activities(session_id)
                
                # Only send new activities
                if len(activities) > last_activity_count:
                    new_activities = activities[last_activity_count:]
                    for activity in new_activities:
                        # SSE format: data: {json}\n\n
                        yield f"data: {json.dumps(activity.dict())}\n\n"
                    last_activity_count = len(activities)
                
                # Poll every second
                await asyncio.sleep(1)
            
            # Send end of stream
            yield "data: {\"type\": \"end\"}\n\n"
        except Exception as e:
            logger.error(f"Error in activity stream: {str(e)}")
            yield f"data: {{\"type\": \"error\", \"message\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        activity_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/cache/initialize")
async def initialize_user_cache(
    user_context: UserContext = Depends(get_current_user)
):
    """
    Initialize user data cache on login for fast UC1 responses.
    Fetches REAL data from MCP servers and caches in JSON file.
    
    This endpoint should be called by frontend after successful login.
    
    Args:
        user_context: Authenticated user context
    
    Returns:
        Cache initialization status
    """
    from app.cache import get_cache_manager
    from app.cache.mcp_client import (
        get_account_mcp_client,
        get_transaction_mcp_client,
        get_payment_mcp_client,
        get_limits_mcp_client
    )
    
    try:
        cache_manager = get_cache_manager()
        customer_id = user_context.customer_id
        
        logger.info(f"🔄 Cache initialization requested for {customer_id}")
        
        # Get MCP clients (these call real MCP servers)
        mcp_clients = {
            "account_mcp": get_account_mcp_client(),
            "transaction_mcp": get_transaction_mcp_client(),
            "payment_mcp": get_payment_mcp_client(),
            "limits_mcp": get_limits_mcp_client()
        }
        
        # Initialize cache with REAL data from MCP servers
        cache_data = await cache_manager.initialize_user_cache(
            customer_id=customer_id,
            user_email=user_context.entra_user_email,
            mcp_clients=mcp_clients
        )
        
        logger.info(f"✅ Cache initialized for {customer_id} with real MCP data")
        
        return {
            "status": "success",
            "customer_id": customer_id,
            "cached_at": cache_data.get("cached_at"),
            "data_sections": list(cache_data.get("data", {}).keys()),
            "message": "User cache initialized successfully with real data"
        }
        
    except Exception as e:
        logger.error(f"❌ Error initializing cache for {user_context.customer_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize user cache: {str(e)}"
        )


@router.post("/init-session")
async def initialize_session(
    user_context: UserContext = Depends(get_current_user)
):
    """
    Initialize a new session and populate cache with MCP data.
    Called on user login or when starting a new chat session.
    
    Args:
        user_context: Authenticated user context
    
    Returns:
        Session information with session_id
    """
    from app.utils.session_memory import get_session_manager
    from app.utils.mcp_data_fetcher import get_mcp_fetcher
    import uuid
    
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create session file
        session_manager = get_session_manager()
        session_manager.create_session(
            user_id=user_context.customer_id,
            session_id=session_id
        )
        
        # Trigger MCP data fetch in background
        mcp_fetcher = get_mcp_fetcher()
        asyncio.create_task(
            mcp_fetcher.populate_session_cache(
                session_id=session_id,
                user_email=user_context.entra_user_email
            )
        )
        
        logger.info(f"✅ Session initialized: {session_id} for user {user_context.entra_user_email}")
        
        return {
            "session_id": session_id,
            "user_id": user_context.customer_id,
            "status": "initialized",
            "cache_status": "populating"
        }
    except Exception as e:
        logger.error(f"Error initializing session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error initializing session: {str(e)}")