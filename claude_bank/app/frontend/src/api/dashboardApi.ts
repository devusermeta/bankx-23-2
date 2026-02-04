/**
 * Dashboard API Service
 * Handles all API calls to the dashboard endpoints
 */

// Always use empty base URL to let Vite proxy handle dashboard routes
// The proxy is configured in vite.config.ts for /api/dashboard
const API_BASE_URL = '';

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

export interface DashboardStats {
  total_conversations: number;
  total_agent_decisions: number;
  total_rag_queries: number;
  total_mcp_calls: number;
  active_agents: number;
}

class DashboardApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async fetchWithErrorHandling<T>(endpoint: string): Promise<T> {
    const fullUrl = `${this.baseUrl}${endpoint}`;
    console.log(`[Dashboard API] Fetching: ${fullUrl}`);
    console.log(`[Dashboard API] Base URL: "${this.baseUrl}"`);
    
    try {
      const response = await fetch(fullUrl);
      console.log(`[Dashboard API] Response status: ${response.status} ${response.statusText}`);
      console.log(`[Dashboard API] Response content-type: ${response.headers.get('content-type')}`);
      
      if (!response.ok) {
        const text = await response.text();
        console.error(`[Dashboard API] Error response body:`, text.substring(0, 200));
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log(`[Dashboard API] Success! Data type: ${Array.isArray(data) ? `Array[${data.length}]` : typeof data}`);
      return data;
    } catch (error) {
      console.error(`[Dashboard API] Error (${endpoint}):`, error);
      throw error;
    }
  }

  /**
   * Get overall dashboard statistics
   */
  async getDashboardStats(): Promise<DashboardStats> {
    return this.fetchWithErrorHandling<DashboardStats>('/api/dashboard/stats');
  }

  /**
   * Get agent decision logs
   * @param date - Optional date in YYYY-MM-DD format
   * @param limit - Maximum number of records to return
   */
  async getAgentDecisions(date?: string, limit: number = 100): Promise<AgentDecision[]> {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    params.append('limit', limit.toString());
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.fetchWithErrorHandling<AgentDecision[]>(`/api/dashboard/agent-decisions${query}`);
  }

  /**
   * Get RAG evaluation logs
   * @param date - Optional date in YYYY-MM-DD format
   * @param limit - Maximum number of records to return
   */
  async getRagEvaluations(date?: string, limit: number = 100): Promise<RagEvaluation[]> {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    params.append('limit', limit.toString());
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.fetchWithErrorHandling<RagEvaluation[]>(`/api/dashboard/rag-evaluations${query}`);
  }

  /**
   * Get triage rule logs
   * @param date - Optional date in YYYY-MM-DD format
   * @param limit - Maximum number of records to return
   */
  async getTriageRules(date?: string, limit: number = 100): Promise<TriageRule[]> {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    params.append('limit', limit.toString());
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.fetchWithErrorHandling<TriageRule[]>(`/api/dashboard/triage-rules${query}`);
  }

  /**
   * Get MCP audit logs
   * @param date - Optional date in YYYY-MM-DD format
   * @param limit - Maximum number of records to return
   */
  async getMcpAudit(date?: string, limit: number = 100): Promise<McpAudit[]> {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    params.append('limit', limit.toString());
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.fetchWithErrorHandling<McpAudit[]>(`/api/dashboard/mcp-audit${query}`);
  }

  /**
   * Get user message logs
   * @param date - Optional date in YYYY-MM-DD format
   * @param limit - Maximum number of records to return
   */
  async getUserMessages(date?: string, limit: number = 100): Promise<UserMessage[]> {
    const params = new URLSearchParams();
    if (date) params.append('date', date);
    params.append('limit', limit.toString());
    
    const query = params.toString() ? `?${params.toString()}` : '';
    return this.fetchWithErrorHandling<UserMessage[]>(`/api/dashboard/user-messages${query}`);
  }
}

// Export singleton instance
export const dashboardApi = new DashboardApiService();
