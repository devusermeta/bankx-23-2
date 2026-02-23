import { useRef, useState, useEffect } from "react";
import { Checkbox, ChoiceGroup, Panel, DefaultButton, TextField, SpinButton, Dropdown, IDropdownOption, IChoiceGroupOption } from "@fluentui/react";
import { SparkleFilled } from "@fluentui/react-icons";
import readNDJSONStream from "ndjson-readablestream";


import styles from "./Chat.module.css";

import {
    chatApi,
    RetrievalMode,
    ChatAppResponse,
    ChatAppResponseOrError,
    ChatAppRequest,
    ResponseMessage,
    Approaches,
    SKMode
} from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { QuestionContextType } from "../../components/QuestionInput/QuestionContext";
import { ExampleList } from "../../components/Example";
import { UserChatMessage } from "../../components/UserChatMessage";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { SettingsButton } from "../../components/SettingsButton";
import { ClearChatButton } from "../../components/ClearChatButton";
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { TokenClaimsDisplay } from "../../components/TokenClaimsDisplay";
import { AttachmentType } from "../../components/AttachmentType";
import { AgentActivityPanel } from "../../components/AgentActivityPanel";
import { HumanInLoopConfirmation } from "../../components/HumanInLoopConfirmation";
import { ThinkingPanel, ThinkingStep } from "../../components/ThinkingPanel";


const Chat = () => {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [approach, setApproach] = useState<Approaches>(Approaches.JAVA_OPENAI_SDK);
    const [skMode, setSKMode] = useState<SKMode>(SKMode.Chains);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [shouldStream, setShouldStream] = useState<boolean>(true);
    const [streamAvailable, setStreamAvailable] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [useSuggestFollowupQuestions, setUseSuggestFollowupQuestions] = useState<boolean>(false);
    const [useOidSecurityFilter, setUseOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter, setUseGroupsSecurityFilter] = useState<boolean>(false);
    const [threadId, setThreadId] = useState<string | undefined>(undefined);

    const lastQuestionRef = useRef<string>("");
    const lastAttachementsRef = useRef<string[] | null>([]);
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [isStreaming, setIsStreaming] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<[user: string, attachments: string[], response: ChatAppResponse][]>([]);
    const [streamedAnswers, setStreamedAnswers] = useState<[user: string, attachments: string[], response: ChatAppResponse][]>([]);
    
    // Confirmation dialog state
    const [showConfirmation, setShowConfirmation] = useState(false);
    const [confirmationDetails, setConfirmationDetails] = useState<{
        title: string;
        message: string;
        details?: Array<{ label: string; value: string }>;
        type: 'payment' | 'ticket' | 'email' | 'general';
    } | null>(null);
    
    // Thinking panel state
    const [showThinkingPanel, setShowThinkingPanel] = useState(false);
    const [currentThinkingSteps, setCurrentThinkingSteps] = useState<ThinkingStep[]>([]);
    const [thinkingLogs, setThinkingLogs] = useState<Map<number, ThinkingStep[]>>(new Map());
    const [selectedThinkingMessageIndex, setSelectedThinkingMessageIndex] = useState<number | null>(null);

    // Log token information on component mount
    useEffect(() => {
        console.log("=".repeat(80));
        console.log("🔷 CHAT COMPONENT MOUNTED - Reading token from localStorage...");
        console.log("=".repeat(80));
        
        // Read all localStorage to find MSAL tokens
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.includes('accesstoken')) {
                console.log(`🔑 [LOCALSTORAGE] Found token key: ${key}`);
                const value = localStorage.getItem(key);
                if (value) {
                    try {
                        const parsed = JSON.parse(value);
                        console.log("📜 [LOCALSTORAGE] Token object:", parsed);
                        if (parsed.secret) {
                            console.log("🎫 [LOCALSTORAGE] ACCESS TOKEN (secret):", parsed.secret);
                            
                            // Decode the token
                            const base64Url = parsed.secret.split('.')[1];
                            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                            }).join(''));
                            const decoded = JSON.parse(jsonPayload);
                            console.log("🎭 [LOCALSTORAGE] DECODED TOKEN:", decoded);
                            console.log("👤 [LOCALSTORAGE] User:", decoded.preferred_username || decoded.upn || decoded.email);
                            console.log("🎯 [LOCALSTORAGE] ROLES:", decoded.roles || "⚠️ No roles in token");
                        }
                    } catch (e) {
                        console.error("❌ Failed to parse token from localStorage:", e);
                    }
                }
            }
        }
        console.log("=".repeat(80));
    }, []); // Empty dependency array = run once on mount

    const handleAsyncRequest = async (question: string, attachments: string[], answers: [string, string[],ChatAppResponse][], setAnswers: Function, responseBody: ReadableStream<any>) => {
        let answer: string = "";
        let askResponse: ChatAppResponse = {} as ChatAppResponse;
        let capturedThreadId: string | undefined = undefined;
        let hasError = false;
        
        // Reset thinking steps for new message
        setCurrentThinkingSteps([]);
        setShowThinkingPanel(true);  // Auto-open panel when user sends message

        const updateState = (newContent: string) => {
            return new Promise(resolve => {
                setTimeout(() => {
                    answer += newContent;
                    
                    // Check if askResponse.choices exists before accessing it
                    const latestResponse: ChatAppResponse = askResponse.choices 
                        ? {
                            ...askResponse,
                            threadId: capturedThreadId,
                            choices: [{ 
                                ...askResponse.choices[0], 
                                message: { 
                                    content: answer, 
                                    role: askResponse.choices[0].message?.role || "assistant" 
                            } 
                        }]
                        }
                        : {
                            threadId: capturedThreadId,
                            choices: [{
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
                            }]
                        };
                    
                    setStreamedAnswers([...answers, [question, attachments, latestResponse]]);
                    resolve(null);
                }, 33);
            });
        };
        
        try {
            setIsStreaming(true);
            for await (const event of readNDJSONStream(responseBody)) {
                // Handle thinking events
                if (event["type"] === "thinking") {
                    const thinkingEvent = event as {
                        type: string;
                        step: string;
                        message: string;
                        status: 'in_progress' | 'completed' | 'failed';
                        timestamp: number;
                        duration?: number;
                    };
                    
                    setCurrentThinkingSteps(prev => {
                        const existingIndex = prev.findIndex(s => s.step === thinkingEvent.step);
                        const newStep: ThinkingStep = {
                            id: `${thinkingEvent.step}-${thinkingEvent.timestamp}`,
                            step: thinkingEvent.step,
                            message: thinkingEvent.message,
                            status: thinkingEvent.status,
                            timestamp: thinkingEvent.timestamp,
                            duration: thinkingEvent.duration
                        };
                        
                        if (existingIndex >= 0) {
                            // Update existing step
                            const updated = [...prev];
                            updated[existingIndex] = newStep;
                            return updated;
                        } else {
                            // Add new step
                            return [...prev, newStep];
                        }
                    });
                    continue;
                }
                
                // Check for error in response
                if (event["error"]) {
                    hasError = true;
                    console.error("Stream error:", event["error"]);
                }
                
                // Capture threadId from any event that has it
                if (event["threadId"]) {
                    capturedThreadId = event["threadId"];
                }
                
                if (event["choices"] && event["choices"][0]["context"] && event["choices"][0]["context"]["data_points"]) {
                    // Final chunk with full context
                    event["choices"][0]["message"] = event["choices"][0]["delta"];
                    askResponse = event;
                    askResponse.threadId = capturedThreadId;
                    answer = askResponse["choices"][0]["message"]["content"];
                    // Update one last time with final response
                    await updateState("");
                } else if (event["choices"] && event["choices"][0]["delta"] && event["choices"][0]["delta"]["content"]) {
                    setIsLoading(false);
                    await updateState(event["choices"][0]["delta"]["content"]);
                }
            }
        } catch (error) {
            console.error("Error reading stream:", error);
            hasError = true;
            // Add error message to answer
            answer = answer || "An error occurred while streaming the response.";
            await updateState(" [Error: Stream interrupted]");
        } finally {
            setIsStreaming(false);
            
            // Save thinking logs for this message
            const messageIndex = answers.length;
            setThinkingLogs(prev => {
                const newLogs = new Map(prev);
                newLogs.set(messageIndex, [...currentThinkingSteps]);
                return newLogs;
            });
            
            // Auto-collapse panel after response is complete
            setTimeout(() => {
                setShowThinkingPanel(false);
            }, 1000);
        }
        
        const fullResponse: ChatAppResponse = {
            ...askResponse,
            threadId: capturedThreadId,
            choices: askResponse.choices 
                ? [{ ...askResponse.choices[0], message: { content: answer, role: askResponse.choices[0].message.role } }]
                : [{
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
                }]
        };
        return fullResponse;
    };

    const client = useLogin ? useMsal().instance : undefined;

    const makeApiRequest = async (questionContext: QuestionContextType) => {
        console.log("=".repeat(80));
        console.log("TEST TEST TEST - makeApiRequest function called!");
        console.log("=".repeat(80));
        alert("makeApiRequest called - check console!");
        console.log("🚀 [CHAT] makeApiRequest called - starting token acquisition...");
        
        // Read all localStorage to find MSAL tokens
        console.log("📦 [LOCALSTORAGE] Reading all localStorage keys...");
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.includes('accesstoken')) {
                console.log(`🔑 [LOCALSTORAGE] Found token key: ${key}`);
                const value = localStorage.getItem(key);
                if (value) {
                    try {
                        const parsed = JSON.parse(value);
                        console.log("📜 [LOCALSTORAGE] Token object:", parsed);
                        if (parsed.secret) {
                            console.log("🎫 [LOCALSTORAGE] ACCESS TOKEN (secret):", parsed.secret);
                            
                            // Decode the token
                            const base64Url = parsed.secret.split('.')[1];
                            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                            }).join(''));
                            const decoded = JSON.parse(jsonPayload);
                            console.log("🎭 [LOCALSTORAGE] DECODED TOKEN:", decoded);
                            console.log("🎯 [LOCALSTORAGE] ROLES:", decoded.roles || "No roles in token");
                        }
                    } catch (e) {
                        console.error("Failed to parse token from localStorage:", e);
                    }
                }
            }
        }
        
        lastQuestionRef.current = questionContext.question;
        lastAttachementsRef.current = questionContext.attachments || [];

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        console.log("🔍 About to call getToken with client:", client ? "EXISTS" : "NULL");
        const token = client ? await getToken(client) : undefined;
        console.log("✅ getToken completed");
        
        // Debug: Log token acquisition
        console.log("🔐 Token acquisition result:", token ? "SUCCESS" : "FAILED");
        if (token) {
            console.log("🔑 Access token length:", token.accessToken?.length || 0);
            console.log("🎫 Token scopes:", token.scopes);
            
            // Log the full access token
            console.log("📜 ACCESS TOKEN (full):", token.accessToken);
            
            // Decode and log JWT payload
            if (token.accessToken) {
                try {
                    const base64Url = token.accessToken.split('.')[1];
                    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
                    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
                    }).join(''));
                    const decoded = JSON.parse(jsonPayload);
                    console.log("🎭 DECODED TOKEN PAYLOAD:", decoded);
                    console.log("👤 User email:", decoded.preferred_username || decoded.upn || decoded.email);
                    console.log("🎯 Roles:", decoded.roles || "No roles assigned");
                } catch (e) {
                    console.error("Failed to decode token:", e);
                }
            }
        } else {
            console.warn("⚠️ No token acquired - will send request without authentication");
        }

        try {
            const messages: ResponseMessage[] = answers.flatMap(a => [
                { content: a[0], role: "user", attachments: a[1]},
                { content: a[2].choices[0].message.content, role: "assistant" }
            ]);

            const stream = streamAvailable && shouldStream;
            const request: ChatAppRequest = {
                messages: [...messages, { content: questionContext.question, role: "user", attachments: questionContext.attachments }],
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
                // ChatAppProtocol: Client must pass on any session state received from the server
                session_state: answers.length ? answers[answers.length - 1][2].choices[0].session_state : null,
                threadId: threadId
            };

            const response = await chatApi(request, token?.accessToken);
            if (!response.body) {
                throw Error("No response body");
            }
            if (stream) {
                const parsedResponse: ChatAppResponse = await handleAsyncRequest(questionContext.question,questionContext.attachments || [], answers, setAnswers, response.body);
                setAnswers([...answers, [questionContext.question,questionContext.attachments || [], parsedResponse]]);
                setThreadId(parsedResponse.threadId || undefined);
            } else {
                const parsedResponse: ChatAppResponseOrError = await response.json();
                if (response.status > 299 || !response.ok) {
                    throw Error(parsedResponse.error || "Unknown error");
                }
                setAnswers([...answers, [questionContext.question,questionContext.attachments || [], parsedResponse as ChatAppResponse]]);
                setThreadId((parsedResponse as ChatAppResponse).threadId || undefined);
            }
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const clearChat = () => {
        lastQuestionRef.current = "";
        lastAttachementsRef.current = [];
        error && setError(undefined);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);
        setAnswers([]);
        setStreamedAnswers([]);
        setIsLoading(false);
        setIsStreaming(false);
        setThreadId(undefined);
        setShowConfirmation(false);
        setConfirmationDetails(null);
        setThinkingLogs(new Map());
        setCurrentThinkingSteps([]);
        setShowThinkingPanel(false);
        setSelectedThinkingMessageIndex(null);
    };
    
    const handleThinkingClick = (messageIndex: number) => {
        const logs = thinkingLogs.get(messageIndex);
        if (logs) {
            setCurrentThinkingSteps(logs);
            setSelectedThinkingMessageIndex(messageIndex);
            setShowThinkingPanel(true);
        }
    };
    
    // Detect if response contains confirmation request
    const detectConfirmationRequest = (responseText: string) => {
        console.log('🔍 [DETECTION] Called with response length:', responseText.length);
        console.log('🔍 [DETECTION] Response preview:', responseText.substring(0, 200));
        
        // Payment confirmation pattern - matches with or without markdown bold (**), bullets, or newlines
        const paymentPattern = /⚠️\s*\*?\*?PAYMENT\s+CONFIRMATION\s+REQUIRED\*?\*?\s*⚠️/i;
        
        console.log('🔍 [DETECTION] Pattern test result:', paymentPattern.test(responseText));
        
        if (paymentPattern.test(responseText)) {
            console.log('✅ [DETECTION] PAYMENT MARKER FOUND! Parsing details...');
            
            // Helper function to extract value from HTML table row
            const extractTableValue = (label: string): string => {
                // Try HTML table format: <td><strong>Label</strong></td><td>Value</td>
                const htmlPattern = new RegExp(`<td>\\s*<strong>\\s*${label}\\s*</strong>\\s*</td>\\s*<td>\\s*([^<]+)\\s*</td>`, 'i');
                const htmlMatch = responseText.match(htmlPattern);
                if (htmlMatch) {
                    return htmlMatch[1].trim();
                }
                
                // Try plain text format: Label: Value or • Label: Value
                const textPattern = new RegExp(`[•\\-\\*]?\\s*${label}\\s*:\\s*([^•\\n<]+)`, 'i');
                const textMatch = responseText.match(textPattern);
                if (textMatch) {
                    return textMatch[1].trim();
                }
                
                return 'N/A';
            };
            
            const amount = extractTableValue('Amount');
            const recipient = extractTableValue('Recipient');
            const account = extractTableValue('Account');
            const paymentMethod = extractTableValue('Payment Method');
            const currentBalance = extractTableValue('Current Balance');
            const newBalance = extractTableValue('New Balance \\(Preview\\)') || extractTableValue('New Balance');
            
            console.log('📊 [DETECTION] Extracted values:', {
                amount,
                recipient,
                account,
                paymentMethod,
                currentBalance,
                newBalance
            });
            
            const details = [
                { label: 'Amount', value: amount },
                { label: 'Recipient', value: recipient },
                { label: 'Account', value: account },
                { label: 'Payment Method', value: paymentMethod },
                { label: 'Current Balance', value: currentBalance },
                { label: 'New Balance', value: newBalance }
            ];
            
            setConfirmationDetails({
                title: 'Payment Confirmation Required',
                message: 'Please review the payment details below and confirm to proceed.',
                type: 'payment',
                details: details
            });
            setShowConfirmation(true);
            console.log('✅ [DETECTION] Confirmation dialog triggered!');
            return true;
        } else {
            console.log('❌ [DETECTION] Payment marker not found');
        }
        
        // Ticket creation confirmation pattern
        const ticketPattern = /Would you like me to create a support ticket/i;
        if (ticketPattern.test(responseText)) {
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
        setShowConfirmation(false);
        // Send "yes" or "confirm" as the next message
        makeApiRequest({ question: "Yes, confirm" });
    };
    
    // Handle cancellation
    const handleCancel = () => {
        setShowConfirmation(false);
        setConfirmationDetails(null);
        // Optionally send "no" or "cancel"
        makeApiRequest({ question: "No, cancel" });
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);
    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" }), [streamedAnswers]);
    
    // Detect confirmation requests in the latest answer
    useEffect(() => {
        if (answers.length > 0) {
            const latestAnswer = answers[answers.length - 1][2];
            const responseText = latestAnswer?.choices?.[0]?.message?.content || '';
            detectConfirmationRequest(responseText);
        }
    }, [answers]);

    const onPromptTemplateChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplate(newValue || "");
    };

    const onRetrieveCountChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setRetrieveCount(parseInt(newValue || "3"));
    };

    const onRetrievalModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<RetrievalMode> | undefined, index?: number | undefined) => {
        setRetrievalMode(option?.data || RetrievalMode.Hybrid);
    };

    const onSKModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<SKMode> | undefined, index?: number | undefined) => {
        setSKMode(option?.data || SKMode.Chains);
    };

    const onApproachChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IChoiceGroupOption) => {
        const newApproach = (option?.key as Approaches);
        setApproach(newApproach || Approaches.JAVA_OPENAI_SDK);
        setStreamAvailable(newApproach === Approaches.JAVA_OPENAI_SDK);
    };

    const onUseSemanticRankerChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticRanker(!!checked);
    };

    const onUseSemanticCaptionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticCaptions(!!checked);
    };

    const onShouldStreamChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setShouldStream(!!checked);
    };

    const onExcludeCategoryChanged = (_ev?: React.FormEvent, newValue?: string) => {
        setExcludeCategory(newValue || "");
    };

    const onUseSuggestFollowupQuestionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSuggestFollowupQuestions(!!checked);
    };

    const onUseOidSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseOidSecurityFilter(!!checked);
    };

    const onUseGroupsSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseGroupsSecurityFilter(!!checked);
    };

    const onExampleClicked = (example: string) => {
        makeApiRequest({question:example});
    };

    const onShowCitation = (citation: string, index: number) => {
        if (activeCitation === citation && activeAnalysisPanelTab === AnalysisPanelTabs.CitationTab && selectedAnswer === index) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveCitation(citation);
            setActiveAnalysisPanelTab(AnalysisPanelTabs.CitationTab);
        }

        setSelectedAnswer(index);
    };

    const onToggleTab = (tab: AnalysisPanelTabs, index: number) => {
        if (activeAnalysisPanelTab === tab && selectedAnswer === index) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveAnalysisPanelTab(tab);
        }

        setSelectedAnswer(index);
    };

    const approaches: IChoiceGroupOption[] = [
        {
            key: Approaches.JAVA_OPENAI_SDK,
            text: "Python Azure Open AI SDK"
        },
        /* Pending Semantic Kernel Memory implementation in V1.0.0
        {
            key: Approaches.JAVA_SEMANTIC_KERNEL,
            text: "Java Semantic Kernel - Memory"
        },*/
        {
            key: Approaches.JAVA_SEMANTIC_KERNEL_PLANNER,
            text: "Python Agent Framework - Orchestration"
        }
    ];

    return (
        <div className={styles.container}>
            <div className={styles.commandsContainer}>
                <ClearChatButton className={styles.commandButton} onClick={clearChat} disabled={!lastQuestionRef.current || isLoading} />
                <SettingsButton className={styles.commandButton} onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
            </div>
            <div className={styles.chatRoot}>
                <div className={styles.chatContainer}>
                    {!lastQuestionRef.current ? (
                        <div className={styles.chatEmptyState}>
                            <SparkleFilled fontSize={"120px"} primaryFill={"rgba(115, 118, 225, 1)"} aria-hidden="true" aria-label="Chat logo" />
                            <h1 className={styles.chatEmptyStateTitle}>Chat with your personal assistant</h1>
                            <h2 className={styles.chatEmptyStateSubtitle}>Ask anything about your banking account details and payments or try an example</h2>
                            <ExampleList onExampleClicked={onExampleClicked} />
                        </div>
                    ) : (
                        <div className={styles.chatMessageStream}>
                            {/* Always render completed answers */}
                            {answers.map((answer, index) => (
                                <div key={`completed-${index}`}>
                                    <UserChatMessage message={answer[0]} attachments={answer[1]} />
                                    <div className={styles.chatMessageGpt}>
                                        <Answer
                                            isStreaming={false}
                                            key={index}
                                            answer={answer[2]}
                                            isSelected={selectedAnswer === index && activeAnalysisPanelTab !== undefined}
                                            onCitationClicked={c => onShowCitation(c, index)}
                                            onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                            onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)}
                                            onFollowupQuestionClicked={q => makeApiRequest({question:q})}
                                            showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
                                            onThinkingClicked={() => handleThinkingClick(index)}
                                            hasThinkingLog={thinkingLogs.has(index)}
                                        />
                                    </div>
                                </div>
                            ))}
                            
                            {/* Render streaming answer on top of completed ones */}
                            {isStreaming &&
                                streamedAnswers.slice(answers.length).map((streamedAnswer, index) => (
                                    <div key={`streaming-${answers.length + index}`}>
                                        <UserChatMessage message={streamedAnswer[0]} attachments={streamedAnswer[1]} />
                                        <div className={styles.chatMessageGpt}>
                                            <Answer
                                                isStreaming={true}
                                                key={answers.length + index}
                                                answer={streamedAnswer[2]}
                                                isSelected={false}
                                                onCitationClicked={c => onShowCitation(c, answers.length + index)}
                                                onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, answers.length + index)}
                                                onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab, answers.length + index)}
                                                onFollowupQuestionClicked={q => makeApiRequest({question:q})}
                                                showFollowupQuestions={false}
                                                onThinkingClicked={() => handleThinkingClick(answers.length + index)}
                                                hasThinkingLog={currentThinkingSteps.length > 0}
                                            />
                                        </div>
                                    </div>
                                ))}
                            
                            {/* Inline Confirmation - Appears in chat flow */}
                            {showConfirmation && confirmationDetails && (
                                <HumanInLoopConfirmation
                                    title={confirmationDetails.title}
                                    message={confirmationDetails.message}
                                    details={confirmationDetails.details}
                                    confirmationType={confirmationDetails.type}
                                    onConfirm={handleConfirm}
                                    onCancel={handleCancel}
                                    confirmText="Confirm"
                                    cancelText="Cancel"
                                    isSubmitting={isLoading}
                                />
                            )}
                            
                            {isLoading && (
                                <>
                                    <UserChatMessage message={lastQuestionRef.current} attachments={lastAttachementsRef.current || []}/>
                                    <div className={styles.chatMessageGptMinWidth}>
                                        <AnswerLoading />
                                    </div>
                                </>
                            )}
                            {error ? (
                                <>
                                    <UserChatMessage message={lastQuestionRef.current} attachments={lastAttachementsRef.current || []}/>
                                    <div className={styles.chatMessageGptMinWidth}>
                                        <AnswerError error={error.toString()} onRetry={() => makeApiRequest({question:lastQuestionRef.current})} />
                                    </div>
                                </>
                            ) : null}
                            <div ref={chatMessageStreamEnd} />
                        </div>
                    )}

                    <div className={styles.chatInput}>
                        <QuestionInput
                            clearOnSend
                            placeholder="Type a new question"
                            disabled={isLoading}
                            onSend={question => makeApiRequest(question)}
                        />
                    </div>
                </div>

                {/* Agent Activity Panel - Always visible on the right */}
                <div className={styles.rightSidebar}>
                    <AgentActivityPanel 
                        sessionId={threadId || 'default'} 
                        isProcessing={isLoading || isStreaming}
                    />
                </div>
                
                {/* Thinking Panel - Shows AI thinking process */}
                <ThinkingPanel
                    isOpen={showThinkingPanel}
                    onClose={() => setShowThinkingPanel(false)}
                    currentSteps={currentThinkingSteps}
                    messageId={selectedThinkingMessageIndex?.toString()}
                />

                {answers.length > 0 && activeAnalysisPanelTab && (
                    <AnalysisPanel
                        className={styles.chatAnalysisPanel}
                        activeCitation={activeCitation}
                        onActiveTabChanged={x => onToggleTab(x, selectedAnswer)}
                        citationHeight="810px"
                        answer={answers[selectedAnswer][2]}
                        activeTab={activeAnalysisPanelTab}
                    />
                )}

                <Panel
                    headerText="Configure answer generation"
                    isOpen={isConfigPanelOpen}
                    isBlocking={false}
                    onDismiss={() => setIsConfigPanelOpen(false)}
                    closeButtonAriaLabel="Close"
                    onRenderFooterContent={() => <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>Close</DefaultButton>}
                    isFooterAtBottom={true}
                >
                    <ChoiceGroup
                        className={styles.chatSettingsSeparator}
                        label="Approach"
                        options={approaches}
                        defaultSelectedKey={approach}
                        onChange={onApproachChange}
                    />

                    {(approach === Approaches.JAVA_OPENAI_SDK || approach === Approaches.JAVA_SEMANTIC_KERNEL) && (
                        <TextField
                            className={styles.chatSettingsSeparator}
                            defaultValue={promptTemplate}
                            label="Override prompt template"
                            multiline
                            autoAdjustHeight
                            onChange={onPromptTemplateChange}
                        />
                    )}
                    {(approach === Approaches.JAVA_SEMANTIC_KERNEL_PLANNER) && (
                        <Dropdown
                            className={styles.oneshotSettingsSeparator}
                            label="Semantic Kernel mode"
                            options={[
                                { key: "chains", text: "Function Chaining", selected: skMode == SKMode.Chains, data: SKMode.Chains },
                                { key: "planner", text: "Planner", selected: skMode == SKMode.Planner, data: SKMode.Planner, disabled: true }
                            ]}
                            required
                            onChange={onSKModeChange}
                        />
                    )}

                    <SpinButton
                        className={styles.chatSettingsSeparator}
                        label="Retrieve this many search results:"
                        min={1}
                        max={50}
                        defaultValue={retrieveCount.toString()}
                        onChange={onRetrieveCountChange}
                    />
                    <TextField className={styles.chatSettingsSeparator} label="Exclude category" onChange={onExcludeCategoryChanged} />
                    <Checkbox
                        className={styles.chatSettingsSeparator}
                        checked={useSemanticRanker}
                        label="Use semantic ranker for retrieval"
                        onChange={onUseSemanticRankerChange}
                    />
                    <Checkbox
                        className={styles.chatSettingsSeparator}
                        checked={useSemanticCaptions}
                        label="Use query-contextual summaries instead of whole documents"
                        onChange={onUseSemanticCaptionsChange}
                        disabled={!useSemanticRanker}
                    />
                    <Checkbox
                        className={styles.chatSettingsSeparator}
                        checked={useSuggestFollowupQuestions}
                        label="Suggest follow-up questions"
                        onChange={onUseSuggestFollowupQuestionsChange}
                    />
                    {useLogin && (
                        <Checkbox
                            className={styles.chatSettingsSeparator}
                            checked={useOidSecurityFilter}
                            label="Use oid security filter"
                            disabled={!client?.getActiveAccount()}
                            onChange={onUseOidSecurityFilterChange}
                        />
                    )}
                    {useLogin && (
                        <Checkbox
                            className={styles.chatSettingsSeparator}
                            checked={useGroupsSecurityFilter}
                            label="Use groups security filter"
                            disabled={!client?.getActiveAccount()}
                            onChange={onUseGroupsSecurityFilterChange}
                        />
                    )}
                    <Dropdown
                        className={styles.chatSettingsSeparator}
                        label="Retrieval mode"
                        options={[
                            { key: "hybrid", text: "Vectors + Text (Hybrid)", selected: retrievalMode == RetrievalMode.Hybrid, data: RetrievalMode.Hybrid },
                            { key: "vectors", text: "Vectors", selected: retrievalMode == RetrievalMode.Vectors, data: RetrievalMode.Vectors },
                            { key: "text", text: "Text", selected: retrievalMode == RetrievalMode.Text, data: RetrievalMode.Text }
                        ]}
                        required
                        onChange={onRetrievalModeChange}
                    />
                    {streamAvailable &&
                        <Checkbox
                            className={styles.chatSettingsSeparator}
                            checked={shouldStream}
                            label="Stream chat completion responses"
                            onChange={onShouldStreamChange}
                        />
                    }

                    {useLogin && <TokenClaimsDisplay />}
                </Panel>
            </div>
        </div>
    );
};

export default Chat;
