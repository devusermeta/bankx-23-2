import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { dashboardApi, type TriageRule } from '@/api/dashboardApi';
import { Search, Table as TableIcon, LayoutGrid, Clock, BarChart3, Target, Loader2, RefreshCw } from 'lucide-react';
import { usePagination } from '@/hooks/usePagination';
import { Pagination } from '@/components/dashboard/Pagination';

type ViewMode = 'table' | 'card' | 'timeline' | 'chart';

const TriageRulesPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [selectedRule, setSelectedRule] = useState('all');
  const [data, setData] = useState<TriageRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getTriageRules(undefined, 500);
      setData(result);
      setError(null);
    } catch (err) {
      console.error('Error fetching triage rules:', err);
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
    return data.filter((rule) => {
      const matchesSearch = 
        searchQuery === '' ||
        rule.user_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rule.rule_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        rule.target_agent.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesAgent = selectedAgent === 'all' || rule.target_agent === selectedAgent;
      const matchesRule = selectedRule === 'all' || rule.rule_name === selectedRule;
      
      return matchesSearch && matchesAgent && matchesRule;
    });
  }, [searchQuery, selectedAgent, selectedRule, data]);

  // Get unique values
  const uniqueAgents = useMemo(() => {
    return Array.from(new Set(data.map(r => r.target_agent)));
  }, [data]);

  const uniqueRules = useMemo(() => {
    return Array.from(new Set(data.map(r => r.rule_name)));
  }, [data]);

  // Pagination
  const pagination = usePagination(filteredData, 10);

  // Calculate stats
  const stats = useMemo(() => {
    const avgConfidence = filteredData.reduce((sum, r) => sum + r.confidence, 0) / filteredData.length;
    const highConfidence = filteredData.filter(r => r.confidence >= 0.8).length;
    const uniqueRulesCount = new Set(filteredData.map(r => r.rule_name)).size;
    const uniqueAgentsCount = new Set(filteredData.map(r => r.target_agent)).size;
    
    return {
      total: filteredData.length,
      avgConfidence: (avgConfidence * 100).toFixed(1),
      highConfidencePercent: ((highConfidence / filteredData.length) * 100).toFixed(1),
      uniqueRules: uniqueRulesCount,
      uniqueAgents: uniqueAgentsCount
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
          <h1 className="text-3xl font-bold mb-2">Triage Rules</h1>
          <p className="text-muted-foreground">
            Monitor routing decisions and agent assignment patterns
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
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Triages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgConfidence}%</div>
            <p className="text-xs text-muted-foreground mt-1">High: {stats.highConfidencePercent}%</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Rules</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.uniqueRules}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Target Agents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.uniqueAgents}</div>
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
                placeholder="Search queries, rules, or agents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Rule Filter */}
            <select
              value={selectedRule}
              onChange={(e) => setSelectedRule(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Rules</option>
              {uniqueRules.map(rule => (
                <option key={rule} value={rule}>{rule}</option>
              ))}
            </select>

            {/* Agent Filter */}
            <select
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Agents</option>
              {uniqueAgents.map(agent => (
                <option key={agent} value={agent}>{agent}</option>
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
const TableView: React.FC<{ data: TriageRule[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Timestamp</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">User Query</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Rule Name</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Target Agent</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {data.map((rule, idx) => (
              <tr key={`${rule.timestamp}-${idx}`} className="border-b border-border hover:bg-muted/50">
                <td className="py-3 px-4 text-sm">
                  {new Date(rule.timestamp).toLocaleString()}
                </td>
                <td className="py-3 px-4 text-sm max-w-md truncate">{rule.user_query}</td>
                <td className="py-3 px-4 text-sm font-medium">{rule.rule_name}</td>
                <td className="py-3 px-4 text-sm">
                  <AgentBadge agent={rule.target_agent} />
                </td>
           

                <td className="py-3 px-4 text-sm">
                  <ConfidenceBadge confidence={rule.confidence} />
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
const CardView: React.FC<{ data: TriageRule[] }> = ({ data }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {data.map((rule, idx) => (
      <Card key={`${rule.timestamp}-${idx}`} className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex justify-between items-start mb-2">
            <CardTitle className="text-base">{rule.rule_name}</CardTitle>
            <ConfidenceBadge confidence={rule.confidence} />
          </div>
          <CardDescription className="text-xs">
            {new Date(rule.timestamp).toLocaleString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">User Query</p>
              <p className="text-sm text-muted-foreground line-clamp-2">{rule.user_query}</p>
            </div>
            <div>
              <p className="text-sm font-medium mb-1">Target Agent</p>
              <AgentBadge agent={rule.target_agent} />
            </div>
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

// Timeline View Component
const TimelineView: React.FC<{ data: TriageRule[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="space-y-4">
        {data.map((rule, index) => (
          <div key={`${rule.timestamp}-${index}`} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full ${
                rule.confidence >= 0.8 ? 'bg-green-500' : 
                rule.confidence >= 0.5 ? 'bg-yellow-500' : 
                'bg-red-500'
              }`} />
              {index < data.length - 1 && <div className="w-0.5 h-full bg-border mt-2" />}
            </div>
            <div className="flex-1 pb-8">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-medium">{rule.rule_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(rule.timestamp).toLocaleString()}
                  </p>
                </div>
                <ConfidenceBadge confidence={rule.confidence} />
              </div>
              <p className="text-sm mb-2">{rule.user_query}</p>
              <div className="flex gap-2 items-center text-sm">
                <Target className="h-4 w-4 text-muted-foreground" />
                <AgentBadge agent={rule.target_agent} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

// Chart View Component
const ChartView: React.FC<{ data: TriageRule[] }> = ({ data }) => {
  // Group by rule
  const ruleData = useMemo(() => {
    const grouped = data.reduce((acc, rule) => {
      if (!acc[rule.rule_name]) {
        acc[rule.rule_name] = { count: 0, avgConfidence: 0, targetAgent: rule.target_agent };
      }
      acc[rule.rule_name].count++;
      acc[rule.rule_name].avgConfidence += rule.confidence;
      return acc;
    }, {} as Record<string, { count: number; avgConfidence: number; targetAgent: string }>);

    return Object.entries(grouped).map(([ruleName, stats]) => ({
      ruleName,
      count: stats.count,
      avgConfidence: (stats.avgConfidence / stats.count) * 100,
      targetAgent: stats.targetAgent
    }));
  }, [data]);

  // Group by agent
  const agentData = useMemo(() => {
    const grouped = data.reduce((acc, rule) => {
      if (!acc[rule.target_agent]) {
        acc[rule.target_agent] = 0;
      }
      acc[rule.target_agent]++;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(grouped).map(([agent, count]) => ({
      agent,
      count,
      percentage: (count / data.length) * 100
    })).sort((a, b) => b.count - a.count);
  }, [data]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Rule Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Rules by Frequency</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {ruleData.map((item) => (
              <div key={item.ruleName}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium truncate mr-2">{item.ruleName}</span>
                  <span className="text-muted-foreground whitespace-nowrap">{item.count} times</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary rounded-full h-2"
                    style={{ width: `${(item.count / data.length) * 100}%` }}
                  />
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                  <span>Avg Confidence: {item.avgConfidence.toFixed(1)}%</span>
                  <span>→ {item.targetAgent}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Agent Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Target Agent Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {agentData.map((item) => (
              <div key={item.agent}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{item.agent}</span>
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

// Agent Badge Component
const AgentBadge: React.FC<{ agent: string }> = ({ agent }) => {
  const colors: Record<string, string> = {
    'AccountAgent': 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    'TransactionAgent': 'bg-purple-500/10 text-purple-500 border-purple-500/20',
    'PaymentAgent': 'bg-green-500/10 text-green-500 border-green-500/20',
    'ProdInfoFAQAgent': 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    'AIMoneyCoachAgent': 'bg-pink-500/10 text-pink-500 border-pink-500/20',
    'EscalationCommsAgent': 'bg-red-500/10 text-red-500 border-red-500/20'
  };

  const color = colors[agent] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${color}`}>
      <Target className="h-3 w-3" />
      {agent}
    </span>
  );
};

// Confidence Badge Component
const ConfidenceBadge: React.FC<{ confidence: number }> = ({ confidence }) => {
  const percentage = (confidence * 100).toFixed(0);
  const variant = confidence >= 0.8 ? 'high' : confidence >= 0.5 ? 'medium' : 'low';
  
  const styles = {
    high: 'bg-green-500/10 text-green-500 border-green-500/20',
    medium: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    low: 'bg-red-500/10 text-red-500 border-red-500/20'
  };

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${styles[variant]}`}>
      {percentage}%
    </span>
  );
};

export default TriageRulesPage;
