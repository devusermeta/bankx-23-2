import { useState, useEffect, useMemo } from "react";
import { Table, Grid, Clock, BarChart2, Search, Filter, Loader2, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { dashboardApi, type AgentDecision } from "@/api/dashboardApi";
import { usePagination } from "@/hooks/usePagination";
import { Pagination } from "@/components/dashboard/Pagination";

type ViewMode = "table" | "card" | "timeline" | "chart";

const AgentDecisionsPage = () => {
  const [viewMode, setViewMode] = useState<ViewMode>("table");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [data, setData] = useState<AgentDecision[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch data from API
  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getAgentDecisions(undefined, 500);
      setData(result);
      setError(null);
    } catch (err) {
      console.error('Error fetching agent decisions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filter data
  const filteredData = useMemo(() => {
    return data.filter((decision) => {
      const matchesSearch =
        decision.user_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
        decision.agent_name.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesAgent = selectedAgent === "all" || decision.agent_name === selectedAgent;
      const matchesStatus = selectedStatus === "all" || decision.result_status === selectedStatus;
      return matchesSearch && matchesAgent && matchesStatus;
    });
  }, [data, searchQuery, selectedAgent, selectedStatus]);

  // Get unique agents for filter
  const uniqueAgents = useMemo(() => {
    return Array.from(new Set(data.map((d) => d.agent_name)));
  }, [data]);
  
  const uniqueStatuses = useMemo(() => {
    return Array.from(new Set(data.map((d) => d.result_status)));
  }, [data]);

  // Pagination
  const pagination = usePagination(filteredData, 10);

  // Calculate stats
  const stats = useMemo(() => {
    if (data.length === 0) return { total: 0, successRate: 0, avgTime: 0, successCount: 0 };
    const successCount = data.filter(d => d.result_status === "success").length;
    const avgTime = data.reduce((sum, d) => sum + d.duration_seconds, 0) / data.length * 1000;
    return {
      total: data.length,
      successRate: (successCount / data.length) * 100,
      avgTime,
      successCount
    };
  }, [data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-red-500 mb-2">Error loading agent decisions</p>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={fetchData} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Agent Decisions</h2>
          <p className="text-muted-foreground">
            Monitor agent routing decisions, triage rules, and execution status
          </p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Decisions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.successRate.toFixed(1)}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.successCount} successful
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.avgTime.toFixed(0)}ms
            </div>
            <p className="text-xs text-muted-foreground">Across all agents</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{uniqueAgents.length}</div>
            <p className="text-xs text-muted-foreground">Handling requests</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and View Modes */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex-1 flex items-center gap-4">
              {/* Search */}
              <div className="relative w-96">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search queries or agents..."
                  className="w-full pl-10 pr-4 py-2 rounded-md border border-input bg-background text-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {/* Agent Filter */}
              <select
                className="px-3 py-2 rounded-md border border-input bg-background text-sm"
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
              >
                <option value="all">All Agents</option>
                {uniqueAgents.map((agent) => (
                  <option key={agent} value={agent}>
                    {agent}
                  </option>
                ))}
              </select>

              {/* Status Filter */}
              <select
                className="px-3 py-2 rounded-md border border-input bg-background text-sm"
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
              >
                <option value="all">All Statuses</option>
                {uniqueStatuses.map((status) => (
                  <option key={status} value={status}>
                    {status}
                  </option>
                ))}
              </select>
            </div>

            {/* View Mode Toggles */}
            <div className="flex items-center gap-1 border rounded-lg p-1">
              <Button
                variant={viewMode === "table" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("table")}
              >
                <Table className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "card" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("card")}
              >
                <Grid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "timeline" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("timeline")}
              >
                <Clock className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === "chart" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("chart")}
              >
                <BarChart2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {viewMode === "table" && <TableView data={pagination.paginatedData} />}
          {viewMode === "card" && <CardView data={pagination.paginatedData} />}
          {viewMode === "timeline" && <TimelineView data={pagination.paginatedData} />}
          {viewMode === "chart" && <ChartView data={data} />}
        </CardContent>
      </Card>

      {/* Pagination */}
      <Pagination
        currentPage={pagination.currentPage}
        totalPages={pagination.totalPages}
        totalItems={pagination.totalItems}
        itemsPerPage={pagination.itemsPerPage}
        onPageChange={pagination.setCurrentPage}
      />
    </div>
  );
};

// Table View Component
const TableView = ({ data }: { data: AgentDecision[] }) => {
  return (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead className="border-b bg-muted/50">
          <tr>
            <th className="px-4 py-3 text-left font-medium">Timestamp</th>
            <th className="px-4 py-3 text-left font-medium">Query</th>
            <th className="px-4 py-3 text-left font-medium">Rule</th>
            <th className="px-4 py-3 text-left font-medium">Agent</th>
            <th className="px-4 py-3 text-left font-medium">Status</th>
            {/* <th className="px-4 py-3 text-left font-medium">Duration</th> */}
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.map((decision, idx) => (
            <tr key={idx} className="hover:bg-muted/50 transition-colors">
              <td className="px-4 py-3 text-muted-foreground">
                {new Date(decision.timestamp).toLocaleString()}
              </td>
              <td className="px-4 py-3 max-w-xs truncate">{decision.user_query}</td>
                <td className="px-4 py-3">
                <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-500">
                  {decision.triage_rule}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className="font-medium">{decision.agent_name}</span>
              </td>
              
            
              <td className="px-4 py-3">
                <StatusBadge status={decision.result_status} />
              </td>
              {/* <td className="px-4 py-3 text-muted-foreground">
                {(decision.duration_seconds * 1000).toFixed(0)}ms
              </td> */}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Card View Component
const CardView = ({ data }: { data: AgentDecision[] }) => {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data.map((decision, idx) => (
        <Card key={idx} className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-lg">{decision.agent_name}</CardTitle>
                <CardDescription>{new Date(decision.timestamp).toLocaleString()}</CardDescription>
              </div>
              <StatusBadge status={decision.result_status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">User Query</p>
              <p className="text-sm">{decision.user_query}</p>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="inline-flex items-center rounded-full px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-500">
                {decision.triage_rule}
              </span>
              <span className="text-muted-foreground">{(decision.duration_seconds * 1000).toFixed(0)}ms</span>
            </div>
            {decision.tools_invoked.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1">Tools Invoked</p>
                <div className="flex flex-wrap gap-1">
                  {decision.tools_invoked.map((tool, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-muted rounded">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

// Timeline View Component
const TimelineView = ({ data }: { data: AgentDecision[] }) => {
  return (
    <div className="space-y-4">
      {data.map((decision, idx) => (
        <div key={idx} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="w-3 h-3 rounded-full bg-primary" />
            {idx < data.length - 1 && <div className="w-0.5 flex-1 bg-border mt-2" />}
          </div>
          <Card className="flex-1 mb-4">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-medium">{decision.agent_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(decision.timestamp).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={decision.result_status} />
              </div>
              <p className="text-sm mt-2">{decision.user_query}</p>
              <div className="flex items-center gap-2 mt-3">
                <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-500 rounded">
                  {decision.triage_rule}
                </span>
                <span className="text-xs text-muted-foreground">
                  {(decision.duration_seconds * 1000).toFixed(0)}ms
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      ))}
    </div>
  );
};

// Chart View Component (Placeholder - will add recharts later)
const ChartView = ({ data }: { data: AgentDecision[] }) => {
  const agentCounts = data.reduce((acc, d) => {
    acc[d.agent_name] = (acc[d.agent_name] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Agent Distribution</CardTitle>
          <CardDescription>Number of decisions per agent</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Object.entries(agentCounts).map(([agent, count]) => (
              <div key={agent}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{agent}</span>
                  <span className="text-sm text-muted-foreground">{count}</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${(count / data.length) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

// Status Badge Component
const StatusBadge = ({ status }: { status: string }) => {
  const colors = {
    success: "bg-green-500/10 text-green-500",
    failure: "bg-red-500/10 text-red-500",
    ticket_created: "bg-yellow-500/10 text-yellow-500",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
        colors[status as keyof typeof colors] || "bg-gray-500/10 text-gray-500"
      }`}
    >
      {status}
    </span>
  );
};

export default AgentDecisionsPage;
