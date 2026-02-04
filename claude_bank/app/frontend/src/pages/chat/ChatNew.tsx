import { useRef, useState, useEffect } from "react";
import { useMsal } from "@azure/msal-react";
import { AlertCircle, Loader2, Send, Sparkles, ArrowDown, Copy, Check } from "lucide-react";
import { readSSEStream } from "../../api/streamSSE";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "../../components/ui/alert";

import {
    chatApi,
    RetrievalMode,
    ChatAppResponse,
    ChatAppResponseOrError,
    ChatAppRequest,
    Approaches,
    SKMode
} from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { AnswerCard } from "../../components/Answer/AnswerCard";
import { UserChatMessage } from "../../components/UserChatMessage";
import { UserChatMessageCard } from "../../components/UserChatMessage/UserChatMessageCard";
import { ExampleList } from "../../components/Example";
import { QuestionContextType } from "../../components/QuestionInput/QuestionContext";
import { useLogin, getToken, validateToken, shouldRefreshToken } from "../../authConfig";
import { ThinkingPanel, ThinkingStep } from "../../components/ThinkingPanel";
import { AgentSystemMapVertical } from "../../components/AgentSystemMap";
import type { AgentEvent } from "../../components/AgentSystemMap/AgentSystemMap";
import type { AgentSystemMapVerticalRef } from "../../components/AgentSystemMap";
import { HumanInLoopConfirmation } from "../../components/HumanInLoopConfirmation";

// Message type with timestamp
type MessageWithTimestamp = {
    message: string;
    attachments: string[];
    response: ChatAppResponse;
    timestamp: Date;
};

// Confirmation details type
type ConfirmationDetails = {
    title: string;
    message: string;
    type: 'payment' | 'ticket' | 'email' | 'beneficiary' | 'general';
    details: Array<{ label: string; value: string }>;
};

const ChatNew = () => {
    const [approach] = useState<Approaches>(Approaches.JAVA_OPENAI_SDK);
    const [skMode] = useState<SKMode>(SKMode.Chains);
    const [promptTemplate] = useState<string>("");
    const [retrieveCount] = useState<number>(3);
    const [retrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [useSemanticRanker] = useState<boolean>(true);
    const [shouldStream] = useState<boolean>(true);
    const [useSemanticCaptions] = useState<boolean>(false);
    const [excludeCategory] = useState<string>("");
    const [useSuggestFollowupQuestions] = useState<boolean>(false);
    const [useOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter] = useState<boolean>(false);
    const [threadId, setThreadId] = useState<string | undefined>(undefined);

    const [question, setQuestion] = useState<string>("");
    const lastQuestionRef = useRef<string>("");
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [isStreaming, setIsStreaming] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [tokenError, setTokenError] = useState<string | null>(null);
    const [showScrollButton, setShowScrollButton] = useState<boolean>(false);

    const [answers, setAnswers] = useState<MessageWithTimestamp[]>([]);
    const [streamedAnswers, setStreamedAnswers] = useState<MessageWithTimestamp[]>([]);
    
    // Confirmation state
    const [showConfirmation, setShowConfirmation] = useState(false);
    const [confirmationDetails, setConfirmationDetails] = useState<ConfirmationDetails | null>(null);
    
    // Thinking panel state
    const [showThinkingPanel, setShowThinkingPanel] = useState(false);
    const [isThinkingPanelVisible, setIsThinkingPanelVisible] = useState(true);
    const [currentThinkingSteps, setCurrentThinkingSteps] = useState<ThinkingStep[]>([]);
    const [thinkingLogs, setThinkingLogs] = useState<Map<number, ThinkingStep[]>>(new Map());
    const [selectedThinkingMessageIndex, setSelectedThinkingMessageIndex] = useState<number | null>(null);
    
    // Agent System Map state
    const [latestAgentEvent, setLatestAgentEvent] = useState<AgentEvent | null>(null);
    const [activeAgent, setActiveAgent] = useState<string | null>(null);
    const agentMapRef = useRef<AgentSystemMapVerticalRef>(null);
    
    const chatContainerRef = useRef<HTMLDivElement | null>(null);

    const client = useLogin ? useMsal().instance : undefined;

    // Check if user is logged in
    const isAuthenticated = useLogin ? client?.getActiveAccount() !== null : true;

    // Track if we've already triggered cache initialization (use ref to persist across renders)
    const cacheInitTriggeredRef = useRef<boolean>(false);

    // Log token information on component mount
    useEffect(() => {
        // console.log("=".repeat(80));
        // console.log("🔷 CHATNEW COMPONENT MOUNTED - Reading token from localStorage...");
        // console.log("=".repeat(80));
        
        // Read all localStorage to find MSAL tokens
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.includes('accesstoken')) {
                // console.log(`🔑 [LOCALSTORAGE] Found token key: ${key}`);
                const value = localStorage.getItem(key);
                if (value) {
                    try {
                        const parsed = JSON.parse(value);
                        // console.log("📜 [LOCALSTORAGE] Token object:", parsed);
                        if (parsed.secret) {
                            // console.log("🎫 [LOCALSTORAGE] ACCESS TOKEN (secret):", parsed.secret);
                            
                            // Decode the token
                            const base64Url = parsed.secret.split('.')[1];
                            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                            }).join(''));
                            const decoded = JSON.parse(jsonPayload);
                            // console.log("🎭 [LOCALSTORAGE] DECODED TOKEN:", decoded);
                            console.log("👤 [LOCALSTORAGE] User:", decoded.preferred_username || decoded.upn || decoded.email);
                            console.log("🎯 [LOCALSTORAGE] ROLES:", decoded.roles || "⚠️ No roles in token");
                        }
                    } catch (e) {
                        console.error("❌ Failed to parse token from localStorage:", e);
                    }
                }
            }
        }
        // console.log("=".repeat(80));
    }, []); // Only run once on mount

    // Trigger cache initialization immediately after authentication (runs only once)
    useEffect(() => {
        // Only trigger if we haven't already done so
        if (cacheInitTriggeredRef.current) {
            console.log("ℹ️ [CACHE INIT] Already triggered, skipping...");
            return;
        }

        console.log("🔍 [CACHE INIT] Checking authentication state...");
        console.log("  - useLogin:", useLogin);
        console.log("  - client exists:", !!client);
        console.log("  - isAuthenticated:", isAuthenticated);
        
        if (useLogin && client && isAuthenticated) {
            console.log("🚀 [CACHE INIT] Authentication confirmed! Triggering cache pre-population...");
            cacheInitTriggeredRef.current = true; // Mark as triggered
            
            getToken(client)
                .then(tokenResponse => {
                    if (tokenResponse?.accessToken) {
                        console.log("🔑 [CACHE INIT] Got access token, calling /api/whoami...");
                        return fetch("/api/whoami", {
                            method: "GET",
                            headers: {
                                "Authorization": `Bearer ${tokenResponse.accessToken}`
                            }
                        });
                    } else {
                        throw new Error("No access token available");
                    }
                })
                .then(response => {
                    console.log("📡 [CACHE INIT] Response status:", response.status);
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log("✅ [CACHE INIT] Cache pre-population triggered successfully!");
                    console.log("📦 [CACHE INIT] Response data:", data);
                })
                .catch(error => {
                    console.warn("⚠️ [CACHE INIT] Pre-population failed (non-critical):", error);
                    console.warn("   Cache will be initialized on first message instead.");
                });
        } else {
            console.log("⏳ [CACHE INIT] Waiting for authentication...");
        }
    }, [useLogin, client, isAuthenticated]); // Re-run when authentication state changes

    // Validate token on mount and set up periodic refresh
    useEffect(() => {
        if (useLogin && client && isAuthenticated) {
            const checkToken = async () => {
                const isValid = await validateToken(client);
                if (!isValid) {
                    setTokenError("Your session has expired. You have been logged out. Please log in again.");
                }
            };
            
            // Check token immediately
            checkToken();
            
            // Set up periodic token check every 2 minutes
            // This ensures token stays fresh during active sessions (will last 40+ minutes)
            const refreshInterval = setInterval(async () => {
                console.log("[AUTH] Checking token status...");
                try {
                    const token = await getToken(client);
                    if (token && shouldRefreshToken(token)) {
                        console.log("[AUTH] Token expiring soon, forcing refresh...");
                        await client.acquireTokenSilent({
                            scopes: token.scopes,
                            account: client.getActiveAccount() || undefined,
                            forceRefresh: true
                        });
                        console.log("[AUTH] ✅ Token proactively refreshed");
                    } else if (token) {
                        console.log("[AUTH] ✅ Token still valid");
                    }
                } catch (error) {
                    console.warn("[AUTH] Token check failed:", error);
                }
            }, 2 * 60 * 1000); // Check every 2 minutes
            
            return () => clearInterval(refreshInterval);
        }
    }, [client, isAuthenticated]);

    const handleAsyncRequest = async (
        question: string,
        attachments: string[],
        answers: MessageWithTimestamp[],
        setAnswers: Function,
        responseBody: ReadableStream<any>
    ) => {
        let answer: string = "";
        let askResponse: ChatAppResponse = {} as ChatAppResponse;
        let capturedThreadId: string | undefined = undefined;
        
        // Reset thinking steps for new message
        console.log('🧠 [THINKING PANEL] Resetting thinking steps for new message');
        setCurrentThinkingSteps([]);
        setShowThinkingPanel(true);
        setIsThinkingPanelVisible(true); // Auto-show when new question is asked
        console.log('🧠 [THINKING PANEL] Auto-opening thinking panel');

        const updateState = (newContent: string) => {
            // Table deduplication: A response will never legitimately have 2 tables
            // If answer already has a table and newContent also has a table, skip it
            const answerHasTable = answer.includes('<table>');
            const newContentHasTable = newContent.includes('<table>');
            
            if (answerHasTable && newContentHasTable) {
                console.log('⚠️ [DEDUPLICATION] Skipping duplicate table - answer already contains a table');
                return; // Skip adding duplicate table
            }
            
            // Immediate update - no debounce for faster response
            answer += newContent;

            const latestResponse: ChatAppResponse = askResponse.choices
                ? {
                      ...askResponse,
                      threadId: capturedThreadId,
                      choices: [
                          {
                              ...askResponse.choices[0],
                              message: {
                                  content: answer,
                                  role: askResponse.choices[0].message?.role || "assistant"
                              }
                          }
                      ]
                  }
                : {
                      threadId: capturedThreadId,
                      choices: [
                          {
                              index: 0,
                              message: {
                                  content: answer,
                                  role: "assistant"
                              },
                              context: {
                                  thoughts: null,
                                  data_points: []
                              },
                              session_state: null
                          }
                      ]
                  };
            setStreamedAnswers([...answers, { 
                message: question, 
                attachments: attachments, 
                response: latestResponse,
                timestamp: new Date()
            }]);
        };

        // Store thinking steps in a variable outside React state to prevent timing issues
        let collectedThinkingSteps: ThinkingStep[] = [];
        
        try {
            setIsStreaming(true);
            
            // Use SSE streaming instead of NDJSON
            await readSSEStream(
                { body: responseBody } as Response,
                (sseEvent) => {
                    console.log('📨 [SSE RAW] Received event:', sseEvent);
                    const event = sseEvent.data;
                    console.log('📨 [SSE PARSED] Event data:', event);
                    console.log('📨 [SSE TYPE] Event type:', event["type"]);
                    
                    // Handle thinking events
                    if (event["type"] === "thinking") {
                        console.log('🧠 [THINKING EVENT] Received:', event);
                        const thinkingEvent = event as {
                            type: string;
                            step: string;
                            message: string;
                            agent?: string;  // NEW: Added agent field
                            agent_name?: string;  // Fallback
                            status: 'in_progress' | 'completed' | 'failed';
                            timestamp: number;
                            duration?: number;
                        };
                        
                        console.log(`🧠 [THINKING] Step: ${thinkingEvent.step}, Status: ${thinkingEvent.status}, Message: ${thinkingEvent.message}`);
                        
                        // Log selected agent when routing step is received
                        if (thinkingEvent.step === 'routing' && thinkingEvent.message) {
                            console.log(`🎯 [AGENT SELECTED] ${thinkingEvent.message}`);
                        }
                        
                        // Extract agent name from agent_selected OR routing step
                        if ((thinkingEvent.step === 'agent_selected' || thinkingEvent.step === 'routing') && thinkingEvent.message) {
                            console.log(`🔍 [AGENT EXTRACTION] Step: ${thinkingEvent.step}, Message: "${thinkingEvent.message}"`);
                            
                            let detectedAgent = null;
                            
                            // PRIORITY 1: Read from 'agent' field directly (NEW!)
                            if (thinkingEvent.agent) {
                                detectedAgent = thinkingEvent.agent;
                                console.log(`✅ [AGENT FROM FIELD] Direct agent field: ${detectedAgent}`);
                            }
                            // PRIORITY 2: Fallback to agent_name field
                            else if (thinkingEvent.agent_name) {
                                detectedAgent = thinkingEvent.agent_name;
                                console.log(`✅ [AGENT FROM FIELD] agent_name field: ${detectedAgent}`);
                            }
                            // PRIORITY 3: Fallback to regex parsing (for old messages)
                            else {
                                const patterns = [
                                    /🎯\s*(\w+)/,           // 🎯 TransactionAgent
                                    /(\w+Agent)\s*\(/,       // TransactionAgent (cached)
                                    /Agent:\s*(\w+)/i,       // Agent: TransactionAgent
                                    /(Payment|Account|Transaction|ProdInfo|Coach|AIMoneyCoach)Agent/i  // Direct agent names
                                ];
                                
                                for (const pattern of patterns) {
                                    const match = thinkingEvent.message.match(pattern);
                                    if (match) {
                                        detectedAgent = match[1];
                                        console.log(`✅ [AGENT MATCHED] Pattern: ${pattern}, Agent: ${detectedAgent}`);
                                        break;
                                    }
                                }
                            }
                            
                            if (detectedAgent) {
                                // Check if it's a cache hit
                                const isCached = thinkingEvent.message.includes('cached') || thinkingEvent.message.includes('cache');
                                
                                // Emit agent event for visualization ONLY when agent is detected
                                const agentEvent: AgentEvent = {
                                    type: 'thinking',
                                    timestamp: new Date(thinkingEvent.timestamp).toISOString(),
                                    step: thinkingEvent.step,
                                    message: thinkingEvent.message,
                                    agent: detectedAgent,
                                    cached: isCached
                                };
                                
                                setLatestAgentEvent(agentEvent);
                                setActiveAgent(detectedAgent);
                                console.log(`✅ [AGENT DETECTED] Agent: ${detectedAgent}, Cached: ${isCached}, Event sent to map:`, agentEvent);
                            } else {
                                console.warn(`❌ [AGENT NOT DETECTED] Could not extract agent from: "${thinkingEvent.message}"`);
                            }
                        }
                        
                        // Create the new step
                        const newStep: ThinkingStep = {
                            id: `${thinkingEvent.step}-${thinkingEvent.timestamp}`,
                            step: thinkingEvent.step,
                            message: thinkingEvent.message,
                            status: thinkingEvent.status,
                            timestamp: thinkingEvent.timestamp,
                            duration: thinkingEvent.duration
                        };
                        
                        // Update the collected steps array
                        const existingIndex = collectedThinkingSteps.findIndex(s => s.step === thinkingEvent.step);
                        if (existingIndex >= 0) {
                            // Update existing step
                            collectedThinkingSteps[existingIndex] = newStep;
                        } else {
                            // Add new step
                            collectedThinkingSteps.push(newStep);
                        }
                        
                        // Update React state for display
                        setCurrentThinkingSteps([...collectedThinkingSteps]);
                        return;
                    }
                    
                    if (event["choices"] && event["choices"][0]["context"] && event["choices"][0]["context"]["data_points"]) {
                        console.log('📨 [SSE] Processing context + data_points path');
                        event["choices"][0]["message"] = event["choices"][0]["delta"];
                        askResponse = event as ChatAppResponse;
                    } else if (event["choices"] && event["choices"][0]["delta"]["content"]) {
                        console.log('📨 [SSE] Processing delta content path');
                        console.log('📨 [SSE] Delta content:', event["choices"][0]["delta"]["content"]);
                        setIsLoading(false);
                        updateState(event["choices"][0]["delta"]["content"]);
                        // Set askResponse to preserve the response structure
                        if (!askResponse.choices || event["choices"][0]["message"]) {
                            // Update askResponse for final chunk or first chunk
                            event["choices"][0]["message"] = event["choices"][0]["message"] || event["choices"][0]["delta"];
                            askResponse = event as ChatAppResponse;
                        }
                    } else if (event["choices"] && event["choices"][0]["context"]) {
                        console.log('📨 [SSE] Processing context-only path');
                        event["choices"][0]["message"] = event["choices"][0]["delta"];
                        askResponse = event;
                    } else if (event["choices"] && event["choices"][0]["session_state"]) {
                        console.log('📨 [SSE] Processing session_state path');
                        if (askResponse.choices && askResponse.choices[0]) {
                            askResponse.choices[0].session_state = event["choices"][0]["session_state"];
                        }
                    } else {
                        console.log('⚠️ [SSE] No matching path for event structure:', event);
                    }

                    if (event["threadId"]) {
                        console.log('📨 [SSE] ThreadId captured:', event["threadId"]);
                        capturedThreadId = event["threadId"];
                    }
                },
                (error) => {
                    console.error('SSE Stream Error:', error);
                }
            );
        } finally {
            setIsStreaming(false);
            
            // Save thinking logs for this message using the collected steps
            const messageIndex = answers.length;
            console.log(`🧠 [THINKING PANEL] Saving thinking logs for message index ${messageIndex}`);
            console.log('🧠 [THINKING PANEL] Collected thinking steps:', collectedThinkingSteps);
            console.log('🧠 [THINKING PANEL] Current answers array length:', answers.length);
            console.log('🧠 [THINKING PANEL] Will save at index:', messageIndex);
            setThinkingLogs(prev => {
                const newLogs = new Map(prev);
                if (collectedThinkingSteps.length > 0) {
                    newLogs.set(messageIndex, [...collectedThinkingSteps]);
                    console.log(`🧠 [THINKING PANEL] Successfully saved ${collectedThinkingSteps.length} steps at index ${messageIndex}`);
                } else {
                    console.warn(`🧠 [THINKING PANEL] No thinking steps to save!`);
                }
                console.log(`🧠 [THINKING PANEL] Total stored logs: ${newLogs.size}`);
                console.log(`🧠 [THINKING PANEL] All stored indices:`, Array.from(newLogs.keys()));
                return newLogs;
            });
            
            // Keep panel open (no auto-collapse)
            console.log('🧠 [THINKING PANEL] Keeping panel open for user review');
        }
        const fullResponse: ChatAppResponse = {
            ...askResponse,
            threadId: capturedThreadId,
            choices: [{ ...askResponse.choices[0], message: { content: answer, role: askResponse.choices[0].message?.role || "assistant" } }]
        };
        return fullResponse;
    };

    // Detect if response contains confirmation request
    const detectConfirmationRequest = (responseText: string) => {
        console.log('🔍 CHATNEW Detection called with:', responseText);
        
        // Payment confirmation pattern (structured format)
        const paymentPattern = /PAYMENT\s+CONFIRMATION\s+REQUIRED/i;
        if (paymentPattern.test(responseText)) {
            // Enhanced regex - handles various formats (bullet points, bold markers, etc.)
            const amountMatch = responseText.match(/\*{0,2}Amount\*{0,2}[:\s]+\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*[•\n]|Reply|$)/i);
            const recipientMatch = responseText.match(/\*{0,2}Recipient\*{0,2}[:\s]+\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*[•\n]|Reply|$)/i);
            const accountMatch = responseText.match(/\*{0,2}Account\*{0,2}[:\s]+\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*[•\n]|Reply|$)/i);
            
            console.log('✅ PAYMENT DETECTED IN CHATNEW!');
            
            setConfirmationDetails({
                title: 'Payment Confirmation Required',
                message: 'Please confirm this payment to proceed.',
                type: 'payment',
                details: [
                    { label: 'Amount', value: amountMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Recipient', value: recipientMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Account', value: accountMatch?.[1]?.trim() || 'N/A' }
                ]
            });
            setShowConfirmation(true);
            return true;
        }
        
        // Fallback: Simple payment confirmation pattern
        // Matches: "Please confirm if you want to proceed with the payment of X THB to Y..."
        // or "confirm...payment" with Reply/Confirm instruction
        const simplePaymentPattern = /(?:please\s+)?confirm.*?(?:proceed.*?)?payment.*?(?:Reply\s+['"']Yes['"]|Confirm)/i;
        if (simplePaymentPattern.test(responseText)) {
            // Extract payment details from natural language
            const amountMatch = responseText.match(/payment\s+of\s+([0-9,]+(?:\.\d{2})?)\s*THB/i) || 
                              responseText.match(/([0-9,]+(?:\.\d{2})?)\s*THB/i);
            const recipientMatch = responseText.match(/to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
            const accountMatch = responseText.match(/account\s+([0-9-]+)/i);
            const balanceMatch = responseText.match(/(?:current\s+)?balance\s+of\s+([0-9,]+(?:\.\d{2})?)\s*THB/i);
            
            console.log('✅ SIMPLE PAYMENT FORMAT DETECTED IN CHATNEW!');
            console.log('  Amount:', amountMatch?.[1]);
            console.log('  Recipient:', recipientMatch?.[1]);
            console.log('  Account:', accountMatch?.[1]);
            console.log('  Balance:', balanceMatch?.[1]);
            
            const details = [];
            if (amountMatch?.[1]) details.push({ label: 'Amount', value: `${amountMatch[1]} THB` });
            if (recipientMatch?.[1]) details.push({ label: 'Recipient', value: recipientMatch[1].trim() });
            if (accountMatch?.[1]) details.push({ label: 'Account', value: accountMatch[1].trim() });
            if (balanceMatch?.[1]) details.push({ label: 'Current Balance', value: `${balanceMatch[1]} THB` });
            
            setConfirmationDetails({
                title: 'Payment Confirmation Required',
                message: 'Please confirm this payment to proceed.',
                type: 'payment',
                details: details.length > 0 ? details : [{ label: 'Payment', value: 'Confirmation needed' }]
            });
            setShowConfirmation(true);
            return true;
        }
        
        // Ticket creation confirmation pattern
        const ticketPattern = /TICKET\s+(?:CREATION\s+)?CONFIRMATION\s+REQUIRED/i;
        if (ticketPattern.test(responseText)) {
            // Enhanced regex - handles various formats (bullet points, bold markers, etc.)
            const issueMatch = responseText.match(/\*{0,2}Issue\*{0,2}[:\s]+\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*[•\n]|Reply|$)/i);
            const typeMatch = responseText.match(/\*{0,2}Type\*{0,2}[:\s]+\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*[•\n]|Reply|$)/i);
            const priorityMatch = responseText.match(/\*{0,2}Priority\*{0,2}[:\s]+\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*[•\n]|Reply|$)/i);
            
            console.log('✅ TICKET CREATION DETECTED IN CHATNEW!');
            
            setConfirmationDetails({
                title: 'Ticket Creation Confirmation Required',
                message: 'Please confirm to create this support ticket.',
                type: 'ticket',
                details: [
                    { label: 'Issue', value: issueMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Type', value: typeMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Priority', value: priorityMatch?.[1]?.trim() || 'N/A' }
                ]
            });
            setShowConfirmation(true);
            return true;
        }
        
        // Email confirmation pattern
        const emailPattern = /EMAIL\s+CONFIRMATION\s+REQUIRED/i;
        if (emailPattern.test(responseText)) {
            // More flexible regex - handles inline format and multiline format
            const toMatch = responseText.match(/To:\s*\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*•|\n|Reply|$)/i);
            const subjectMatch = responseText.match(/Subject:\s*\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*•|\n|Reply|$)/i);
            const previewMatch = responseText.match(/Preview:\s*\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*•|\n|Reply|$)/i);
            
            console.log('✅ EMAIL CONFIRMATION DETECTED IN CHATNEW!');
            
            setConfirmationDetails({
                title: 'Email Confirmation Required',
                message: 'Please confirm to send this email.',
                type: 'email',
                details: [
                    { label: 'To', value: toMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Subject', value: subjectMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Preview', value: previewMatch?.[1]?.trim() || 'N/A' }
                ]
            });
            setShowConfirmation(true);
            return true;
        }
        
        // Beneficiary addition confirmation pattern
        const beneficiaryPattern = /BENEFICIARY\s+(?:ADDITION\s+)?CONFIRMATION\s+REQUIRED/i;
        if (beneficiaryPattern.test(responseText)) {
            // More flexible regex
            const nameMatch = responseText.match(/Name:\s*\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*•|\n|Reply|$)/i);
            const accountMatch = responseText.match(/Account\s+Number:\s*\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*•|\n|Reply|$)/i);
            const bankMatch = responseText.match(/Bank:\s*\*{0,2}([^•\n*]+?)(?:\*{0,2})?(?:\s*•|\n|Reply|$)/i);
            
            console.log('✅ BENEFICIARY ADDITION DETECTED IN CHATNEW!');
            
            setConfirmationDetails({
                title: 'Beneficiary Addition Confirmation Required',
                message: 'Please confirm to add this beneficiary.',
                type: 'beneficiary',
                details: [
                    { label: 'Name', value: nameMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Account Number', value: accountMatch?.[1]?.trim() || 'N/A' },
                    { label: 'Bank', value: bankMatch?.[1]?.trim() || 'N/A' }
                ]
            });
            setShowConfirmation(true);
            return true;
        }
        
        // Legacy ticket pattern (fallback)
        const legacyTicketPattern = /Would you like me to create a support ticket/i;
        if (legacyTicketPattern.test(responseText)) {
            setConfirmationDetails({
                title: 'Create Support Ticket',
                message: 'Would you like to create a support ticket for this issue?',
                type: 'ticket',
                details: []
            });
            setShowConfirmation(true);
            return true;
        }
        
        return false;
    };
    
    // Handle confirmation
    const handleConfirm = () => {
        console.log('✅ User clicked CONFIRM button');
        const type = confirmationDetails?.type || 'payment';
        setShowConfirmation(false);
        
        // Send type-specific confirmation message
        const confirmationMessages: Record<string, string> = {
            payment: "Yes, confirm the payment",
            ticket: "Yes, create the ticket",
            email: "Yes, send the email",
            beneficiary: "Yes, add the beneficiary"
        };
        
        makeApiRequest({ question: confirmationMessages[type] || "Yes, confirm", attachments: [] });
    };
    
    // Handle cancellation
    const handleCancel = () => {
        console.log('❌ User clicked CANCEL button');
        const type = confirmationDetails?.type || 'payment';
        setShowConfirmation(false);
        setConfirmationDetails(null);
        
        // Send type-specific cancellation message
        const cancellationMessages: Record<string, string> = {
            payment: "No, cancel the payment",
            ticket: "No, cancel the ticket creation",
            email: "No, cancel the email",
            beneficiary: "No, cancel adding the beneficiary"
        };
        
        makeApiRequest({ question: cancellationMessages[type] || "No, cancel", attachments: [] });
    };

    const makeApiRequest = async (questionContext: QuestionContextType) => {
        lastQuestionRef.current = questionContext.question;

        error && setError(undefined);
        tokenError && setTokenError(null);
        setIsLoading(true);
        setStreamedAnswers(answers);
        
        // Clear agent map and show supervisor thinking immediately
        if (agentMapRef.current) {
            agentMapRef.current.clearAndShowSupervisor();
            console.log('✅ [CHAT] Called clearAndShowSupervisor on agent map');
        }

        const token = client ? await getToken(client) : undefined;
        
        // If token acquisition failed and login is required, show error
        if (useLogin && !token) {
            setTokenError("Your session has expired. You have been logged out. Please log in again to continue.");
            setIsLoading(false);
            return;
        }
        
        const stream = shouldStream && approach !== Approaches.JAVA_SEMANTIC_KERNEL_PLANNER;

        try {
            // Build full conversation history from previous answers
            const conversationMessages: Array<{role: string, content: string}> = [];
            
            // Add all previous Q&A pairs
            for (const answer of answers) {
                // Add user message
                conversationMessages.push({
                    role: "user",
                    content: answer.message
                });
                // Add assistant response
                if (answer.response && answer.response.choices && answer.response.choices.length > 0) {
                    const assistantContent = answer.response.choices[0].message?.content || "";
                    if (assistantContent) {
                        conversationMessages.push({
                            role: "assistant",
                            content: assistantContent
                        });
                    }
                }
            }
            
            // Add current question
            conversationMessages.push({
                role: "user",
                content: questionContext.question
            });
            
            console.log(`[FRONTEND DEBUG] Sending ${conversationMessages.length} messages to backend:`, 
                conversationMessages.map((m, i) => `[${i}] ${m.role}: ${m.content.substring(0, 50)}...`));
            
            const request: ChatAppRequest = {
                messages: conversationMessages,
                stream: stream,
                context: {
                    overrides: {
                        prompt_template: promptTemplate.length === 0 ? undefined : promptTemplate,
                        exclude_category: excludeCategory.length === 0 ? undefined : excludeCategory,
                        top: retrieveCount,
                        retrieval_mode: retrievalMode,
                        semantic_ranker: useSemanticRanker,
                        semantic_captions: useSemanticCaptions,
                        suggest_followup_questions: useSuggestFollowupQuestions,
                        use_oid_security_filter: useOidSecurityFilter,
                        use_groups_security_filter: useGroupsSecurityFilter,
                        semantic_kernel_mode: skMode
                    }
                },
                approach: approach,
                session_state: answers.length ? answers[answers.length - 1].response.choices[0].session_state : null,
                threadId: threadId
            };

            const response = await chatApi(request, token?.accessToken);
            if (!response.body) {
                throw Error("No response body");
            }
            const timestamp = new Date();
            
            if (stream) {
                const parsedResponse: ChatAppResponse = await handleAsyncRequest(
                    questionContext.question,
                    questionContext.attachments || [],
                    answers,
                    setAnswers,
                    response.body
                );
                setAnswers([...answers, { 
                    message: questionContext.question, 
                    attachments: questionContext.attachments || [], 
                    response: parsedResponse,
                    timestamp 
                }]);
                setThreadId(parsedResponse.threadId || undefined);
            } else {
                const parsedResponse: ChatAppResponseOrError = await response.json();
                if (response.status > 299 || !response.ok) {
                    throw Error(parsedResponse.error || "Unknown error");
                }
                setAnswers([...answers, { 
                    message: questionContext.question, 
                    attachments: questionContext.attachments || [], 
                    response: parsedResponse as ChatAppResponse,
                    timestamp 
                }]);
                setThreadId((parsedResponse as ChatAppResponse).threadId || undefined);
            }
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const clearChat = () => {
        console.log('🧠 [THINKING PANEL] Clearing chat and resetting all thinking data');
        lastQuestionRef.current = "";
        error && setError(undefined);
        setAnswers([]);
        setStreamedAnswers([]);
        setIsLoading(false);
        setIsStreaming(false);
        setThreadId(undefined);
        setQuestion("");
        setThinkingLogs(new Map());
        setCurrentThinkingSteps([]);
        setShowThinkingPanel(false);
        setSelectedThinkingMessageIndex(null);
        console.log('🧠 [THINKING PANEL] All thinking data cleared');
    };
    
    const handleThinkingClick = (messageIndex: number) => {
        console.log(`🧠 [THINKING PANEL] User clicked thinking icon for message ${messageIndex}`);
        console.log(`🧠 [THINKING PANEL] All stored thinking logs:`, Array.from(thinkingLogs.keys()));
        
        const logs = thinkingLogs.get(messageIndex);
        if (logs && logs.length > 0) {
            console.log(`🧠 [THINKING PANEL] Found ${logs.length} thinking steps for message ${messageIndex}`);
            console.log('🧠 [THINKING PANEL] Steps:', logs);
            setCurrentThinkingSteps([...logs]); // Create new array to force re-render
            setSelectedThinkingMessageIndex(messageIndex);
            setShowThinkingPanel(true);
            setIsThinkingPanelVisible(true); // Show panel when AI Thinking button is clicked
            console.log('🧠 [THINKING PANEL] Panel opened for historical view');
        } else {
            console.warn(`🧠 [THINKING PANEL] No thinking logs found for message ${messageIndex}`);
            console.log('🧠 [THINKING PANEL] Available log indices:', Array.from(thinkingLogs.keys()));
            // Show empty panel
            setCurrentThinkingSteps([]);
            setSelectedThinkingMessageIndex(messageIndex);
            setShowThinkingPanel(true);
            setIsThinkingPanelVisible(true); // Show panel even if empty
        }
    };

    const sendQuestion = () => {
        if (!question.trim() || isLoading || !isAuthenticated) {
            return;
        }
        makeApiRequest({ question: question.trim(), attachments: [] });
        setQuestion("");
    };

    const onEnterPress = (ev: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (ev.key === "Enter" && !ev.shiftKey && !ev.ctrlKey) {
            ev.preventDefault();
            sendQuestion();
        }
    };

    const onExampleClicked = (example: string) => {
        if (!isAuthenticated) return;
        makeApiRequest({ question: example, attachments: [] });
    };

    const scrollToBottom = () => {
        chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" });
    };

    // Handle scroll detection for "scroll to bottom" button
    const handleScroll = () => {
        if (chatContainerRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
            const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
            setShowScrollButton(!isNearBottom && answers.length > 0);
        }
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);
    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" }), [streamedAnswers]);
    
    // Detect confirmation requests in the latest answer
    useEffect(() => {
        if (answers.length > 0) {
            const latestAnswer = answers[answers.length - 1];
            const responseText = latestAnswer?.response?.choices?.[0]?.message?.content || '';
            console.log('🔄 CHATNEW useEffect - Latest answer content:', responseText);
            detectConfirmationRequest(responseText);
        }
    }, [answers]);
    
    useEffect(() => {
        const container = chatContainerRef.current;
        if (container) {
            container.addEventListener('scroll', handleScroll);
            return () => container.removeEventListener('scroll', handleScroll);
        }
    }, [answers.length]);

    return (
        <div className="h-[calc(100vh-64px)] bg-background flex relative">
            {/* Left Column - Chat Area */}
            <div className="flex-1 flex flex-col">
                {/* Main Chat Area - Fixed height with internal scrolling */}
                <div ref={chatContainerRef} className="flex-1 overflow-y-auto px-6 py-8 w-full">
                {!lastQuestionRef.current ? (
                    <div className="flex flex-col items-center justify-center h-full space-y-10 animate-in fade-in duration-700">
                        <div className="relative">
                            <div className="absolute inset-0 blur-3xl opacity-30 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"></div>
                            <Sparkles className="h-28 w-28 text-primary relative animate-pulse" />
                        </div>
                        <div className="text-center space-y-5">
                            <h1 className="text-5xl font-bold bg-gradient-to-r from-primary via-blue-600 to-purple-600 bg-clip-text text-transparent animate-in slide-in-from-bottom-4 duration-700">
                                Chat with BankX Assistant
                            </h1>
                            <p className="text-muted-foreground text-xl max-w-2xl leading-relaxed animate-in slide-in-from-bottom-5 duration-700 delay-150">
                                {/* Ask anything about your banking account details and payments or try an example */}
                                Ask about BankX product information, account details, transactions, payments, or personal finance debt.
                            </p>
                        </div>
                        {tokenError && (
                            <Alert variant="destructive" className="max-w-xl shadow-lg animate-in slide-in-from-bottom-6 duration-700 delay-300">
                                <AlertCircle className="h-5 w-5" />
                                <AlertDescription className="text-base">{tokenError}</AlertDescription>
                            </Alert>
                        )}
                        {!isAuthenticated ? (
                            <Alert className="max-w-xl shadow-lg animate-in slide-in-from-bottom-6 duration-700 delay-300">
                                <AlertCircle className="h-5 w-5" />
                                <AlertDescription className="text-base">Please sign in to start chatting</AlertDescription>
                            </Alert>
                        ) : (
                            <div className="w-full max-w-4xl animate-in slide-in-from-bottom-7 duration-700 delay-300">
                                <ExampleList onExampleClicked={onExampleClicked} />
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="space-y-6 max-w-5xl mx-auto w-full pb-4">
                        {/* Always render completed answers */}
                        {answers.map((answer, index) => {
                            const isLastAnswer = index === answers.length - 1;
                            const shouldShowConfirmation = isLastAnswer && showConfirmation && confirmationDetails;
                            
                            return (
                                <div key={`completed-${index}`} className="space-y-4">
                                    <UserChatMessageCard 
                                        message={answer.message} 
                                        timestamp={answer.timestamp}
                                    />
                                    <AnswerCard 
                                        content={answer.response.choices[0].message.content}
                                        isStreaming={false}
                                        timestamp={answer.timestamp}
                                        onFeedback={(feedback) => {
                                            console.log(`Feedback for message ${index}:`, feedback);
                                            // TODO: Send feedback to backend
                                        }}
                                        onThinkingClicked={() => handleThinkingClick(index)}
                                        hasThinkingLog={thinkingLogs.has(index)}
                                        showConfirmation={!!shouldShowConfirmation}
                                        onConfirm={shouldShowConfirmation ? handleConfirm : undefined}
                                        onCancel={shouldShowConfirmation ? handleCancel : undefined}
                                        isConfirming={isLoading}
                                    />
                                </div>
                            );
                        })}
                        
                        {/* Render streaming answer on top of completed ones */}
                        {isStreaming &&
                            streamedAnswers.slice(answers.length).map((streamedAnswer, index) => (
                                <div key={`streaming-${answers.length + index}`} className="space-y-4">
                                    <UserChatMessageCard 
                                        message={streamedAnswer.message} 
                                        timestamp={streamedAnswer.timestamp}
                                    />
                                    <AnswerCard 
                                        content={streamedAnswer.response.choices[0].message.content}
                                        isStreaming={true}
                                        timestamp={streamedAnswer.timestamp}
                                        onThinkingClicked={() => handleThinkingClick(answers.length + index)}
                                        hasThinkingLog={currentThinkingSteps.length > 0}
                                    />
                                </div>
                            ))}
                        
                        {isLoading && (
                            <>
                                <UserChatMessage message={lastQuestionRef.current} attachments={[]} />
                                <AnswerLoading currentThinkingSteps={currentThinkingSteps} />
                            </>
                        )}
                        {error ? (
                            <>
                                <UserChatMessage message={lastQuestionRef.current} attachments={[]} />
                                <AnswerError error={error.toString()} onRetry={() => makeApiRequest({ question: lastQuestionRef.current })} />
                            </>
                        ) : null}
                        <div ref={chatMessageStreamEnd} />
                    </div>
                )}
            </div>

            {/* Scroll to Bottom Button */}
            {showScrollButton && (
                <button
                    onClick={scrollToBottom}
                    className="fixed bottom-32 right-8 bg-primary hover:bg-primary/90 text-primary-foreground rounded-full p-3 shadow-lg hover:shadow-xl transition-all duration-200 hover:scale-110 z-50 animate-in fade-in slide-in-from-bottom-4"
                    aria-label="Scroll to bottom"
                >
                    <ArrowDown className="h-5 w-5" />
                </button>
            )}

            {/* Input Area - Fixed at bottom */}
            <div className="border-t border-border bg-card/80 backdrop-blur-sm px-6 py-5 flex-shrink-0 shadow-lg">
                <div className="max-w-5xl mx-auto w-full">
                    {tokenError ? (
                        <Alert variant="destructive" className="shadow-md">
                            <AlertCircle className="h-5 w-5" />
                            <AlertDescription className="text-base">{tokenError}</AlertDescription>
                        </Alert>
                    ) : !isAuthenticated ? (
                        <Alert className="shadow-md">
                            <AlertCircle className="h-5 w-5" />
                            <AlertDescription className="text-base">Please sign in to start chatting with the assistant</AlertDescription>
                        </Alert>
                    ) : (
                        <div className="space-y-2">
                            <div className="flex gap-3 items-end">
                                <div className="flex-1 relative">
                                    <Textarea
                                        placeholder="Type your question here..."
                                        value={question}
                                        onChange={e => setQuestion(e.target.value)}
                                        onKeyDown={onEnterPress}
                                        disabled={isLoading}
                                        maxLength={2000}
                                        className="min-h-[90px] resize-none text-base shadow-sm transition-all duration-200 focus:shadow-md pr-16"
                                    />
                                    <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                                        {question.length}/2000
                                    </div>
                                </div>
                            <div className="flex gap-2 flex-shrink-0">
                                {lastQuestionRef.current && (
                                    <Button 
                                        variant="outline" 
                                        onClick={clearChat} 
                                        disabled={isLoading} 
                                        size="lg"
                                        className="transition-all duration-200 hover:scale-105"
                                    >
                                        Clear
                                    </Button>
                                )}
                                <Button 
                                    onClick={sendQuestion} 
                                    disabled={!question.trim() || isLoading} 
                                    size="lg"
                                    className="transition-all duration-200 hover:scale-105 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-md hover:shadow-lg"
                                >
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                            Sending
                                        </>
                                    ) : (
                                        <>
                                            <Send className="mr-2 h-4 w-4" />
                                            Send
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground mt-2 px-1">
                            <span>💡 Press <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 rounded bg-muted border border-border">Shift + Enter</kbd> for new line</span>
                        </div>
                    </div>
                    )}
                </div>
            </div>
            </div>

            {/* Thinking Process Bubble - Positioned between chat and map on the right */}
            {currentThinkingSteps.length > 0 && isThinkingPanelVisible && (
                <div className="fixed top-32 right-[720px] z-50 animate-in slide-in-from-right-4 duration-300">
                    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border-2 border-blue-500/30 p-6 w-[520px] max-h-[600px] overflow-y-auto backdrop-blur-xl bg-opacity-95">
                        <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-blue-500/20">
                            <div className="flex items-center gap-3">
                                <div className="h-3 w-3 bg-blue-500 rounded-full animate-pulse shadow-lg shadow-blue-500/50"></div>
                                <h3 className="text-base font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">AI Thinking</h3>
                            </div>
                            <button 
                                onClick={() => setIsThinkingPanelVisible(false)}
                                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                                aria-label="Close thinking panel"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                                </svg>
                            </button>
                        </div>
                        <div className="space-y-3">
                            {currentThinkingSteps.map((step) => (
                                <div key={step.id} className="flex items-start gap-3 text-sm bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-3 rounded-lg">
                                    <div className={`mt-0.5 text-lg ${
                                        step.status === 'completed' ? 'text-green-500' : 
                                        step.status === 'in_progress' ? 'text-blue-500 animate-spin' : 
                                        'text-red-500'
                                    }`}>
                                        {step.status === 'completed' ? '✓' : step.status === 'in_progress' ? '⟳' : '✗'}
                                    </div>
                                    <div className="flex-1">
                                        <div className="font-semibold text-gray-800 dark:text-gray-200 text-sm">{step.step.replace(/_/g, ' ')}</div>
                                        <div className="text-gray-600 dark:text-gray-400 text-xs mt-1">{step.message}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Right Column - Visualization Panel (Full Height) */}
            <div className="w-[700px] border-l border-border bg-card/50 flex flex-col overflow-hidden">
                {/* Agent System Map - Full Height */}
                <div className="flex-1 overflow-hidden p-6">
                    <AgentSystemMapVertical
                        ref={agentMapRef}
                        latestEvent={latestAgentEvent}
                        activeAgent={activeAgent}
                        isStreaming={isStreaming}
                        isThinkingPanelVisible={isThinkingPanelVisible}
                    />
                </div>
            </div>
        </div>
    );
};

export default ChatNew;
