import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { dashboardApi, type McpAudit } from '@/api/dashboardApi';
import { Search, Table as TableIcon, LayoutGrid, Clock, BarChart3, Shield, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';
import { usePagination } from '@/hooks/usePagination';
import { Pagination } from '@/components/dashboard/Pagination';

type ViewMode = 'table' | 'card' | 'timeline' | 'chart';

const McpAuditPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedServer, setSelectedServer] = useState('all');
  const [selectedOperation, setSelectedOperation] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [data, setData] = useState<McpAudit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getMcpAudit(undefined, 500);
      setData(result);
      setError(null);
    } catch (err) {
      console.error('Error fetching MCP audit logs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Filter data based on search and filters
  const filteredData = useMemo(() => {
    return data.filter((audit) => {
      const matchesSearch = 
        searchQuery === '' ||
        audit.tool_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        audit.mcp_server.toLowerCase().includes(searchQuery.toLowerCase()) ||
        audit.user_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        audit.data_scope.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesServer = selectedServer === 'all' || audit.mcp_server === selectedServer;
      const matchesOperation = selectedOperation === 'all' || audit.operation_type === selectedOperation;
      const matchesStatus = selectedStatus === 'all' || audit.result_status === selectedStatus;
      
      return matchesSearch && matchesServer && matchesOperation && matchesStatus;
    });
  }, [searchQuery, selectedServer, selectedOperation, selectedStatus, data]);

  // Get unique values
  const uniqueServers = useMemo(() => {
    return Array.from(new Set(data.map(a => a.mcp_server)));
  }, [data]);

  const uniqueOperations = useMemo(() => {
    return Array.from(new Set(data.map(a => a.operation_type)));
  }, [data]);

  const uniqueStatuses = useMemo(() => {
    return Array.from(new Set(data.map(a => a.result_status)));
  }, [data]);

  // Pagination
  const pagination = usePagination(filteredData, 10);

  // Calculate stats
  const stats = useMemo(() => {
    const avgDuration = filteredData.reduce((sum, a) => sum + a.duration_ms, 0) / filteredData.length;
    const successRate = (filteredData.filter(a => a.result_status === 'success').length / filteredData.length) * 100;
    const totalCompliance = filteredData.reduce((sum, a) => sum + a.compliance_flags.length, 0);
    const uniqueUsers = new Set(filteredData.map(a => a.user_id)).size;
    
    return {
      total: filteredData.length,
      avgDuration: avgDuration.toFixed(0),
      successRate: successRate.toFixed(1),
      totalCompliance,
      uniqueUsers
    };
  }, [filteredData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <p className="text-red-500">{error}</p>
        <Button onClick={fetchData}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold mb-2">MCP Audit Trail</h1>
          <p className="text-muted-foreground">
            Monitor MCP server calls, data access, and compliance tracking
          </p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Operations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.successRate}%</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Duration</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgDuration}ms</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Compliance Flags</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalCompliance}</div>
            <p className="text-xs text-muted-foreground mt-1">{stats.uniqueUsers} users</p>
          </CardContent>
        </Card>
      </div>

      {/* Filters and View Toggles */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search tools, servers, users, or data scope..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Server Filter */}
            <select
              value={selectedServer}
              onChange={(e) => setSelectedServer(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Servers</option>
              {uniqueServers.map(server => (
                <option key={server} value={server}>{server}</option>
              ))}
            </select>

            {/* Operation Filter */}
            <select
              value={selectedOperation}
              onChange={(e) => setSelectedOperation(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Operations</option>
              {uniqueOperations.map(op => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Statuses</option>
              {uniqueStatuses.map(status => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>

            {/* View Mode Toggles */}
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'table' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('table')}
              >
                <TableIcon className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'card' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('card')}
              >
                <LayoutGrid className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'timeline' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('timeline')}
              >
                <Clock className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'chart' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('chart')}
              >
                <BarChart3 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Data Display */}
      {viewMode === 'table' && <TableView data={pagination.paginatedData} />}
      {viewMode === 'card' && <CardView data={pagination.paginatedData} />}
      {viewMode === 'timeline' && <TimelineView data={pagination.paginatedData} />}
      {viewMode === 'chart' && <ChartView data={filteredData} />}

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
const TableView: React.FC<{ data: McpAudit[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Timestamp</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">MCP Server</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Tool</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">User</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Data Scope</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Status</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Duration</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Compliance</th>
            </tr>
          </thead>
          <tbody>
            {data.map((audit, idx) => (
              <tr key={`${audit.timestamp}-${idx}`} className="border-b border-border hover:bg-muted/50">
                <td className="py-3 px-4 text-sm">
                  {new Date(audit.timestamp).toLocaleString()}
                </td>
                <td className="py-3 px-4 text-sm font-medium">{audit.mcp_server}</td>
                <td className="py-3 px-4 text-sm">{audit.tool_name}</td>
                <td className="py-3 px-4 text-sm">{audit.user_id}</td>
                <td className="py-3 px-4 text-sm">{audit.data_scope}</td>
                <td className="py-3 px-4 text-sm">
                  <StatusBadge status={audit.result_status} />
                </td>
                <td className="py-3 px-4 text-sm">{audit.duration_ms}ms</td>
                <td className="py-3 px-4 text-sm">
                  <div className="flex flex-wrap gap-1">
                    {audit.compliance_flags.slice(0, 2).map((flag, i) => (
                      <ComplianceBadge key={i} flag={flag} />
                    ))}
                    {audit.compliance_flags.length > 2 && (
                      <span className="text-xs text-muted-foreground">+{audit.compliance_flags.length - 2}</span>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </CardContent>
  </Card>
);

// Card View Component
const CardView: React.FC<{ data: McpAudit[] }> = ({ data }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {data.map((audit, idx) => (
      <Card key={`${audit.timestamp}-${idx}`} className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex justify-between items-start mb-2">
            <CardTitle className="text-base">{audit.mcp_server}</CardTitle>
            <StatusBadge status={audit.result_status} />
          </div>
          <CardDescription className="text-xs">
            {new Date(audit.timestamp).toLocaleString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">Tool Call</p>
              <p className="text-sm text-muted-foreground">{audit.tool_name}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-xs text-muted-foreground">User</p>
                <p className="text-sm font-medium truncate">{audit.user_id}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Duration</p>
                <p className="text-sm font-medium">{audit.duration_ms}ms</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Data Scope</p>
              <p className="text-sm">{audit.data_scope}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Compliance</p>
              <div className="flex flex-wrap gap-1">
                {audit.compliance_flags.map((flag, i) => (
                  <ComplianceBadge key={i} flag={flag} />
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

// Timeline View Component
const TimelineView: React.FC<{ data: McpAudit[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="space-y-4">
        {data.map((audit, index) => (
          <div key={`${audit.timestamp}-${index}`} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full ${
                audit.result_status === 'success' ? 'bg-green-500' : 
                audit.result_status === 'error' ? 'bg-red-500' : 
                'bg-yellow-500'
              }`} />
              {index < data.length - 1 && <div className="w-0.5 h-full bg-border mt-2" />}
            </div>
            <div className="flex-1 pb-8">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-medium">{audit.mcp_server} → {audit.tool_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(audit.timestamp).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={audit.result_status} />
              </div>
              <p className="text-sm mb-2">{audit.result_summary}</p>
              <div className="flex gap-4 text-sm text-muted-foreground mb-2">
                <span>User: {audit.user_id}</span>
                <span>Duration: {audit.duration_ms}ms</span>
                <span>Scope: {audit.data_scope}</span>
              </div>
              <div className="flex flex-wrap gap-1">
                {audit.compliance_flags.map((flag, i) => (
                  <ComplianceBadge key={i} flag={flag} />
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

// Chart View Component
const ChartView: React.FC<{ data: McpAudit[] }> = ({ data }) => {
  // Group by server
  const serverData = useMemo(() => {
    const grouped = data.reduce((acc, audit) => {
      if (!acc[audit.mcp_server]) {
        acc[audit.mcp_server] = { count: 0, avgDuration: 0, successCount: 0 };
      }
      acc[audit.mcp_server].count++;
      acc[audit.mcp_server].avgDuration += audit.duration_ms;
      if (audit.result_status === 'success') acc[audit.mcp_server].successCount++;
      return acc;
    }, {} as Record<string, { count: number; avgDuration: number; successCount: number }>);

    return Object.entries(grouped).map(([server, stats]) => ({
      server,
      count: stats.count,
      avgDuration: stats.avgDuration / stats.count,
      successRate: (stats.successCount / stats.count) * 100
    }));
  }, [data]);

  // Compliance distribution
  const complianceData = useMemo(() => {
    const flags = data.flatMap(a => a.compliance_flags);
    const grouped = flags.reduce((acc, flag) => {
      acc[flag] = (acc[flag] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(grouped).map(([flag, count]) => ({
      flag,
      count,
      percentage: (count / flags.length) * 100
    })).sort((a, b) => b.count - a.count);
  }, [data]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Server Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Operations by MCP Server</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {serverData.map((item) => (
              <div key={item.server}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{item.server}</span>
                  <span className="text-muted-foreground">{item.count} calls</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary rounded-full h-2"
                    style={{ width: `${(item.count / data.length) * 100}%` }}
                  />
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                  <span>Avg Duration: {item.avgDuration.toFixed(0)}ms</span>
                  <span>Success Rate: {item.successRate.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Compliance Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Compliance Flags Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {complianceData.map((item) => (
              <div key={item.flag}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{item.flag}</span>
                  <span className="text-muted-foreground">
                    {item.count} ({item.percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-green-500 rounded-full h-2"
                    style={{ width: `${item.percentage}%` }}
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
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles = {
    success: 'bg-green-500/10 text-green-500 border-green-500/20',
    error: 'bg-red-500/10 text-red-500 border-red-500/20',
    pending: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
  };

  const style = styles[status as keyof typeof styles] || styles.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${style}`}>
      {status}
    </span>
  );
};

// Compliance Badge Component
const ComplianceBadge: React.FC<{ flag: string }> = ({ flag }) => {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border bg-blue-500/10 text-blue-500 border-blue-500/20">
      <Shield className="h-3 w-3" />
      {flag}
    </span>
  );
};

export default McpAuditPage;
