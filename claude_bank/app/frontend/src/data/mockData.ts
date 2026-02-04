// Mock data types
export interface AgentDecision {
  timestamp: string;
  agent_name: string;
  thread_id: string;
  user_query: string;
  triage_rule: string;
  reasoning: string;
  tools_considered: string[];
  tools_invoked: string[];
  result_status: string;
  result_summary: string;
  context: Record<string, any>;
  duration_seconds: number;
  message_type: string;
}

export interface RagEvaluation {
  timestamp: string;
  service: string;
  query: string;
  response_preview: string;
  groundedness_score: number;
  is_grounded: boolean;
  confidence_normalized: number;
  reasoning: string;
  citations_count: number;
  citations: string[];
}

export interface TriageRule {
  timestamp: string;
  rule_name: string;
  target_agent: string;
  user_query: string;
  confidence: number;
}

export interface McpAudit {
  timestamp: string;
  operation_type: string;
  mcp_server: string;
  tool_name: string;
  user_id: string;
  thread_id: string | null;
  parameters: Record<string, any>;
  data_accessed: any[];
  data_scope: string;
  result_status: string;
  result_summary: string;
  error_message: string | null;
  duration_ms: number;
  compliance_flags: string[];
}

export interface UserMessage {
  timestamp: string;
  thread_id: string;
  user_query: string;
  response_preview: string;
  response_length: number;
  duration_seconds: number;
  message_type: string;
}

// Mock Agent Decisions Data
export const mockAgentDecisions: AgentDecision[] = [
  {
    timestamp: "2025-11-13T12:08:53.247251",
    agent_name: "AccountAgent",
    thread_id: "thread_YTY8LYt3YEIFsISbhruNsckq",
    user_query: "what is my account balance",
    triage_rule: "UC1_ACCOUNT_BALANCE",
    reasoning: "User query classified as account-related: balance_inquiry",
    tools_considered: [],
    tools_invoked: ["getAccountsByUserName", "getAccountDetails"],
    result_status: "success",
    result_summary: "Response length: 29 chars",
    context: { use_case: "UC1" },
    duration_seconds: 0.001,
    message_type: "account_inquiry"
  },
  {
    timestamp: "2025-11-13T12:20:09.519840",
    agent_name: "AccountAgent",
    thread_id: "thread_zkbwajB36uqFZ6rpXPxkyN0m",
    user_query: "what is my account balance?",
    triage_rule: "UC1_ACCOUNT_BALANCE",
    reasoning: "User query classified as account-related: balance_inquiry",
    tools_considered: [],
    tools_invoked: ["getAccountsByUserName"],
    result_status: "success",
    result_summary: "Response length: 30 chars",
    context: { use_case: "UC1" },
    duration_seconds: 0.0,
    message_type: "account_inquiry"
  },
  {
    timestamp: "2025-11-12T10:05:13.679374",
    agent_name: "ProdInfoFAQAgent",
    thread_id: "thread_zygTKVOr6pBUzsGmly9dqbFY",
    user_query: "What is BankX's policy on cryptocurrency trading?",
    triage_rule: "UC2_PRODUCT_GENERAL",
    reasoning: "User asked about BankX products, features, or FAQ",
    tools_considered: ["search_documents", "get_content_understanding"],
    tools_invoked: ["search_documents", "get_content_understanding", "write_to_cosmosdb"],
    result_status: "ticket_created",
    result_summary: "Low confidence (0.2) - Ticket created",
    context: { use_case: "UC2", confidence: 0.2 },
    duration_seconds: 0.029,
    message_type: "general_inquiry"
  },
  {
    timestamp: "2025-11-12T12:39:14.640487",
    agent_name: "ProdInfoFAQAgent",
    thread_id: "thread_QHWCm74YYDpGZqGCmcsDJMaX",
    user_query: "What are the fees for international wire transfers?",
    triage_rule: "UC2_PRODUCT_GENERAL",
    reasoning: "User asked about BankX products, features, or FAQ",
    tools_considered: ["search_documents"],
    tools_invoked: ["search_documents", "get_content_understanding"],
    result_status: "success",
    result_summary: "Product info retrieved",
    context: { use_case: "UC2" },
    duration_seconds: 0.012,
    message_type: "payment_request"
  },
  {
    timestamp: "2025-11-11T17:45:34.187681",
    agent_name: "AIMoneyCoachAgent",
    thread_id: "thread_LLb6X90iPpqwrJoKmYemE6hH",
    user_query: "I feel like a failure because I'm in debt.",
    triage_rule: "UC3_DEBT_MANAGEMENT",
    reasoning: "User seeking financial coaching and mindset support",
    tools_considered: ["ai_search_rag_results"],
    tools_invoked: ["ai_search_rag_results", "ai_foundry_content_understanding"],
    result_status: "success",
    result_summary: "Coaching advice provided from Chapter 12",
    context: { use_case: "UC3", financial_health: "ORDINARY" },
    duration_seconds: 0.156,
    message_type: "coaching_request"
  },
  {
    timestamp: "2025-11-13T10:15:22.482910",
    agent_name: "PaymentAgent",
    thread_id: "thread_ABC123DEF456GHI",
    user_query: "I want to transfer 25000 THB to account 123-456-002",
    triage_rule: "UC1_PAYMENT_TRANSFER",
    reasoning: "User initiated payment transfer request",
    tools_considered: ["validateTransfer", "checkLimits", "submitPayment"],
    tools_invoked: ["validateTransfer", "submitPayment"],
    result_status: "success",
    result_summary: "Transfer completed successfully",
    context: { use_case: "UC1", amount: 25000, currency: "THB" },
    duration_seconds: 0.245,
    message_type: "payment_request"
  },
  {
    timestamp: "2025-11-13T09:30:15.123456",
    agent_name: "TransactionAgent",
    thread_id: "thread_XYZ789UVW012",
    user_query: "Show me my transactions from last week",
    triage_rule: "UC1_TRANSACTION_HISTORY",
    reasoning: "User requesting transaction history with date filter",
    tools_considered: ["searchTransactions", "aggregateTransactions"],
    tools_invoked: ["searchTransactions"],
    result_status: "success",
    result_summary: "Retrieved 12 transactions",
    context: { use_case: "UC1", date_range: "last_7_days" },
    duration_seconds: 0.089,
    message_type: "transaction_inquiry"
  }
];

// Mock RAG Evaluations
export const mockRagEvaluations: RagEvaluation[] = [
  {
    timestamp: "2025-11-12T10:05:07.707578",
    service: "prodinfo_faq",
    query: "What is BankX's policy on cryptocurrency trading?",
    response_preview: "Based on the search results: BankX does not have a specific policy on cryptocurrency trading documented in the available product materials...",
    groundedness_score: 0.15,
    is_grounded: false,
    confidence_normalized: 0.2,
    reasoning: "No relevant documents found in knowledge base",
    citations_count: 0,
    citations: []
  },
  {
    timestamp: "2025-11-12T12:39:11.224145",
    service: "prodinfo_faq",
    query: "fees for international wire transfers",
    response_preview: "According to the Current Account documentation, international wire transfer fees vary based on the destination country and amount...",
    groundedness_score: 0.85,
    is_grounded: true,
    confidence_normalized: 0.8,
    reasoning: "Found relevant information in current account product docs",
    citations_count: 2,
    citations: [
      "current-account-en.docx (Section: chunk_3)",
      "normal-fixed-account-en.docx (Section: chunk_6)"
    ]
  },
  {
    timestamp: "2025-11-11T17:45:28.491203",
    service: "ai_money_coach",
    query: "I feel like a failure because I'm in debt",
    response_preview: "According to Chapter 12 of 'Debt-Free to Financial Freedom', feeling like a failure when in debt is common. Debt is a condition, not your identity...",
    groundedness_score: 0.95,
    is_grounded: true,
    confidence_normalized: 0.9,
    reasoning: "Found highly relevant content in Chapter 12 about debt psychology",
    citations_count: 3,
    citations: [
      "Chapter 12: Debt Does Not Define You",
      "Chapter 14: Healing Financial Shame",
      "Chapter 58: From Debt to Builder Mindset"
    ]
  }
];

// Mock MCP Audit Data
export const mockMcpAudit: McpAudit[] = [
  {
    timestamp: "2025-11-13T12:08:53.247251",
    operation_type: "tool_call",
    mcp_server: "account-mcp",
    tool_name: "getAccountsByUserName",
    user_id: "areeya@bankx.com",
    thread_id: "thread_YTY8LYt3YEIFsISbhruNsckq",
    parameters: { username: "areeya@bankx.com" },
    data_accessed: [{ account_id: "ACC-001", account_type: "savings" }],
    data_scope: "user_accounts",
    result_status: "success",
    result_summary: "Retrieved 2 accounts",
    error_message: null,
    duration_ms: 145,
    compliance_flags: ["PCI_DSS", "DATA_PROTECTION"]
  },
  {
    timestamp: "2025-11-13T12:20:09.519840",
    operation_type: "tool_call",
    mcp_server: "payment-mcp",
    tool_name: "initiateTransfer",
    user_id: "areeya@bankx.com",
    thread_id: "thread_zkbwajB36uqFZ6rpXPxkyN0m",
    parameters: { 
      from_account: "ACC-001",
      to_account: "ACC-002",
      amount: 25000,
      currency: "THB"
    },
    data_accessed: [
      { account_id: "ACC-001", balance_checked: true },
      { account_id: "ACC-002", verified: true }
    ],
    data_scope: "payment_transfer",
    result_status: "success",
    result_summary: "Transfer initiated successfully",
    error_message: null,
    duration_ms: 892,
    compliance_flags: ["PCI_DSS", "AML", "TRANSACTION_MONITORING"]
  },
  {
    timestamp: "2025-11-12T10:05:13.679374",
    operation_type: "search",
    mcp_server: "rag-mcp",
    tool_name: "search_documents",
    user_id: "john@bankx.com",
    thread_id: "thread_zygTKVOr6pBUzsGmly9dqbFY",
    parameters: { 
      query: "cryptocurrency trading policy",
      top_k: 5
    },
    data_accessed: [
      { document: "policies.pdf", sections: ["5.2", "8.1"] },
      { document: "faq.docx", sections: ["crypto"] }
    ],
    data_scope: "product_documents",
    result_status: "success",
    result_summary: "Found 5 relevant documents",
    error_message: null,
    duration_ms: 234,
    compliance_flags: ["DATA_ACCESS"]
  },
  {
    timestamp: "2025-11-12T12:39:14.640487",
    operation_type: "tool_call",
    mcp_server: "transaction-mcp",
    tool_name: "getTransactionHistory",
    user_id: "areeya@bankx.com",
    thread_id: "thread_QHWCm74YYDpGZqGCmcsDJMaX",
    parameters: { 
      account_id: "ACC-001",
      days: 30
    },
    data_accessed: [
      { transaction_count: 45, date_range: "2025-10-13 to 2025-11-12" }
    ],
    data_scope: "transaction_history",
    result_status: "success",
    result_summary: "Retrieved 45 transactions",
    error_message: null,
    duration_ms: 312,
    compliance_flags: ["PCI_DSS", "DATA_PROTECTION"]
  },
  {
    timestamp: "2025-11-11T17:45:34.187681",
    operation_type: "tool_call",
    mcp_server: "escalation-mcp",
    tool_name: "create_ticket",
    user_id: "john@bankx.com",
    thread_id: "thread_LLb6X90iPpqwrJoKmYemE6hH",
    parameters: { 
      category: "low_confidence",
      query: "cryptocurrency policy",
      confidence: 0.2
    },
    data_accessed: [{ ticket_id: "TICK-2025-11-11-001" }],
    data_scope: "support_tickets",
    result_status: "success",
    result_summary: "Ticket created successfully",
    error_message: null,
    duration_ms: 178,
    compliance_flags: ["CUSTOMER_SERVICE"]
  }
];

// Mock User Messages Data
export const mockUserMessages: UserMessage[] = [
  {
    timestamp: "2025-11-13T12:08:53.247251",
    thread_id: "thread_YTY8LYt3YEIFsISbhruNsckq",
    user_query: "what is my account balance",
    response_preview: "Your current account balance is 125,450.75 THB across 2 accounts...",
    response_length: 156,
    duration_seconds: 2.45,
    message_type: "account_inquiry"
  },
  {
    timestamp: "2025-11-13T12:20:09.519840",
    thread_id: "thread_zkbwajB36uqFZ6rpXPxkyN0m",
    user_query: "what is my account balance?",
    response_preview: "You have 2 accounts with BankX. Your Savings Account ending in 001 has a balance of...",
    response_length: 203,
    duration_seconds: 1.89,
    message_type: "account_inquiry"
  },
  {
    timestamp: "2025-11-12T10:05:13.679374",
    thread_id: "thread_zygTKVOr6pBUzsGmly9dqbFY",
    user_query: "What is BankX's policy on cryptocurrency trading?",
    response_preview: "I found some information about BankX policies, but I'm not entirely confident in the answer. I've created a support ticket...",
    response_length: 187,
    duration_seconds: 5.67,
    message_type: "general_inquiry"
  },
  {
    timestamp: "2025-11-12T12:39:14.640487",
    thread_id: "thread_QHWCm74YYDpGZqGCmcsDJMaX",
    user_query: "What are the fees for international wire transfers?",
    response_preview: "According to our fee schedule, international wire transfers have the following charges: For transfers up to 50,000 THB...",
    response_length: 342,
    duration_seconds: 3.21,
    message_type: "payment_request"
  },
  {
    timestamp: "2025-11-11T17:45:34.187681",
    thread_id: "thread_LLb6X90iPpqwrJoKmYemE6hH",
    user_query: "I feel like a failure because I'm in debt.",
    response_preview: "I understand how overwhelming debt can feel. According to financial coaching principles from Chapter 12...",
    response_length: 512,
    duration_seconds: 8.34,
    message_type: "coaching_request"
  },
  {
    timestamp: "2025-11-13T10:15:22.482910",
    thread_id: "thread_ABC123DEF456GHI",
    user_query: "I want to transfer 25000 THB to account 123-456-002",
    response_preview: "I'll help you transfer 25,000 THB. Let me verify your account balance and the recipient details...",
    response_length: 298,
    duration_seconds: 4.12,
    message_type: "payment_request"
  },
  {
    timestamp: "2025-11-13T09:30:18.123456",
    thread_id: "thread_XYZ789ABC012DEF",
    user_query: "Show me my last 5 transactions",
    response_preview: "Here are your last 5 transactions: 1) Nov 12: Payment to ABC Store -2,450 THB, 2) Nov 11: Salary deposit +45,000 THB...",
    response_length: 276,
    duration_seconds: 2.78,
    message_type: "transaction_inquiry"
  }
];

// Mock Triage Rules
export const mockTriageRules: TriageRule[] = [
  {
    timestamp: "2025-11-13T12:08:40.964647",
    rule_name: "UC1_ACCOUNT_BALANCE",
    target_agent: "AccountAgent",
    user_query: "what is my account balance",
    confidence: 1.0
  },
  {
    timestamp: "2025-11-13T12:20:09.519840",
    rule_name: "UC1_ACCOUNT_BALANCE",
    target_agent: "AccountAgent",
    user_query: "what is my account balance?",
    confidence: 1.0
  },
  {
    timestamp: "2025-11-12T10:05:13.679374",
    rule_name: "UC2_PRODUCT_GENERAL",
    target_agent: "ProdInfoFAQAgent",
    user_query: "What is BankX's policy on cryptocurrency trading?",
    confidence: 0.95
  },
  {
    timestamp: "2025-11-11T17:45:34.187681",
    rule_name: "UC3_DEBT_MANAGEMENT",
    target_agent: "AIMoneyCoachAgent",
    user_query: "I feel like a failure because I'm in debt",
    confidence: 0.98
  },
  {
    timestamp: "2025-11-13T10:15:22.482910",
    rule_name: "UC1_PAYMENT_TRANSFER",
    target_agent: "PaymentAgent",
    user_query: "I want to transfer 25000 THB",
    confidence: 1.0
  }
];
