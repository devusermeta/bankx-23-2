import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { dashboardApi, type RagEvaluation } from '@/api/dashboardApi';
import { Search, Table as TableIcon, LayoutGrid, Clock, BarChart3, CheckCircle, XCircle, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import { usePagination } from '@/hooks/usePagination';
import { Pagination } from '@/components/dashboard/Pagination';

type ViewMode = 'table' | 'card' | 'timeline' | 'chart';

const RagEvaluationsPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('all');
  const [selectedGrounding, setSelectedGrounding] = useState('all');
  const [data, setData] = useState<RagEvaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getRagEvaluations(undefined, 500);
      setData(result);
      setError(null);
    } catch (err) {
      console.error('Error fetching RAG evaluations:', err);
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
    return data.filter((evaluation) => {
      const matchesSearch = 
        searchQuery === '' ||
        evaluation.query.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evaluation.service.toLowerCase().includes(searchQuery.toLowerCase()) ||
        evaluation.citations.some(c => c.toLowerCase().includes(searchQuery.toLowerCase()));
      
      const matchesAgent = selectedAgent === 'all' || evaluation.service === selectedAgent;
      
      const matchesGrounding = 
        selectedGrounding === 'all' || 
        (selectedGrounding === 'high' && evaluation.groundedness_score >= 0.8) ||
        (selectedGrounding === 'medium' && evaluation.groundedness_score >= 0.5 && evaluation.groundedness_score < 0.8) ||
        (selectedGrounding === 'low' && evaluation.groundedness_score < 0.5);
      
      return matchesSearch && matchesAgent && matchesGrounding;
    });
  }, [searchQuery, selectedAgent, selectedGrounding, data]);

  // Get unique agents
  const uniqueAgents = useMemo(() => {
    return Array.from(new Set(data.map(e => e.service)));
  }, [data]);

  // Pagination
  const pagination = usePagination(filteredData, 10);

  // Calculate stats
  const stats = useMemo(() => {
    const avgGroundedness = filteredData.reduce((sum, e) => sum + e.groundedness_score, 0) / filteredData.length;
    const avgConfidence = filteredData.reduce((sum, e) => sum + e.confidence_normalized, 0) / filteredData.length;
    const avgCitations = filteredData.reduce((sum, e) => sum + e.citations_count, 0) / filteredData.length;
    const highGrounding = filteredData.filter(e => e.groundedness_score >= 0.8).length;
    
    return {
      total: filteredData.length,
      avgGroundedness: (avgGroundedness * 100).toFixed(1),
      avgConfidence: (avgConfidence * 100).toFixed(1),
      avgCitations: avgCitations.toFixed(1),
      highGroundingPercent: ((highGrounding / filteredData.length) * 100).toFixed(1)
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
          <h1 className="text-3xl font-bold mb-2">RAG Evaluations</h1>
          <p className="text-muted-foreground">
            Monitor retrieval quality, grounding scores, and citation accuracy
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
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Evaluations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Groundedness</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgGroundedness}%</div>
            <p className="text-xs text-muted-foreground mt-1">High quality: {stats.highGroundingPercent}%</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Confidence</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgConfidence}%</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Citations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgCitations}</div>
            <p className="text-xs text-muted-foreground mt-1">per query</p>
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
                placeholder="Search queries, agents, or citations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

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

            {/* Grounding Filter */}
            <select
              value={selectedGrounding}
              onChange={(e) => setSelectedGrounding(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Grounding</option>
              <option value="high">High (≥80%)</option>
              <option value="medium">Medium (50-79%)</option>
              <option value="low">Low (&lt;50%)</option>
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

      {/* Pagination Controls */}
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
const TableView: React.FC<{ data: RagEvaluation[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Timestamp</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Agent</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Query</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Groundedness</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Confidence</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Citations</th>
            </tr>
          </thead>
          <tbody>
            {data.map((evaluation, idx) => (
              <tr key={`${evaluation.timestamp}-${idx}`} className="border-b border-border hover:bg-muted/50">
                <td className="py-3 px-4 text-sm">
                  {new Date(evaluation.timestamp).toLocaleString()}
                </td>
                <td className="py-3 px-4 text-sm font-medium">{evaluation.service}</td>
                <td className="py-3 px-4 text-sm max-w-md truncate">{evaluation.query}</td>
                <td className="py-3 px-4 text-sm">
                  <GroundingBadge score={evaluation.groundedness_score} />
                </td>
                <td className="py-3 px-4 text-sm">{(evaluation.confidence_normalized * 100).toFixed(0)}%</td>
                <td className="py-3 px-4 text-sm">{evaluation.citations_count}</td>

              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </CardContent>
  </Card>
);

// Card View Component
const CardView: React.FC<{ data: RagEvaluation[] }> = ({ data }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {data.map((evaluation, idx) => (
      <Card key={`${evaluation.timestamp}-${idx}`} className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex justify-between items-start mb-2">
            <CardTitle className="text-base">{evaluation.service}</CardTitle>
            <GroundingBadge score={evaluation.groundedness_score} />
          </div>
          <CardDescription className="text-xs">
            {new Date(evaluation.timestamp).toLocaleString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">Query</p>
              <p className="text-sm text-muted-foreground line-clamp-2">{evaluation.query}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <p className="text-xs text-muted-foreground">Confidence</p>
                <p className="text-sm font-medium">{(evaluation.confidence_normalized * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Grounded</p>
                <p className="text-sm font-medium">{evaluation.is_grounded ? 'Yes' : 'No'}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Citations ({evaluation.citations_count})</p>
              <div className="flex flex-wrap gap-1">
                {evaluation.citations.slice(0, 3).map((citation, idx) => (
                  <span key={idx} className="text-xs px-2 py-1 bg-muted rounded truncate max-w-full">
                    {citation}
                  </span>
                ))}
                {evaluation.citations.length > 3 && (
                  <span className="text-xs px-2 py-1 bg-muted rounded">
                    +{evaluation.citations.length - 3} more
                  </span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

// Timeline View Component
const TimelineView: React.FC<{ data: RagEvaluation[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="space-y-4">
        {data.map((evaluation, index) => (
          <div key={`${evaluation.timestamp}-${index}`} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full ${
                evaluation.groundedness_score >= 0.8 ? 'bg-green-500' : 
                evaluation.groundedness_score >= 0.5 ? 'bg-yellow-500' : 
                'bg-red-500'
              }`} />
              {index < data.length - 1 && <div className="w-0.5 h-full bg-border mt-2" />}
            </div>
            <div className="flex-1 pb-8">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="font-medium">{evaluation.service}</p>
                  <p className="text-sm text-muted-foreground">
                    {new Date(evaluation.timestamp).toLocaleString()}
                  </p>
                </div>
                <GroundingBadge score={evaluation.groundedness_score} />
              </div>
              <p className="text-sm mb-2">{evaluation.query}</p>
              <div className="flex gap-4 text-sm text-muted-foreground">
                <span>Confidence: {(evaluation.confidence_normalized * 100).toFixed(0)}%</span>
                <span>Citations: {evaluation.citations_count}</span>
                <span>Grounded: {evaluation.is_grounded ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

// Chart View Component
const ChartView: React.FC<{ data: RagEvaluation[] }> = ({ data }) => {
  // Group by agent
  const agentData = useMemo(() => {
    const grouped = data.reduce((acc, evaluation) => {
      if (!acc[evaluation.service]) {
        acc[evaluation.service] = { count: 0, avgGrounding: 0, avgConfidence: 0 };
      }
      acc[evaluation.service].count++;
      acc[evaluation.service].avgGrounding += evaluation.groundedness_score;
      acc[evaluation.service].avgConfidence += evaluation.confidence_normalized;
      return acc;
    }, {} as Record<string, { count: number; avgGrounding: number; avgConfidence: number }>);

    return Object.entries(grouped).map(([agent, stats]) => ({
      agent,
      count: stats.count,
      avgGrounding: (stats.avgGrounding / stats.count) * 100,
      avgConfidence: (stats.avgConfidence / stats.count) * 100
    }));
  }, [data]);

  // Grounding distribution
  const groundingDistribution = useMemo(() => {
    const high = data.filter(e => e.groundedness_score >= 0.8).length;
    const medium = data.filter(e => e.groundedness_score >= 0.5 && e.groundedness_score < 0.8).length;
    const low = data.filter(e => e.groundedness_score < 0.5).length;
    return [
      { category: 'High (≥80%)', count: high },
      { category: 'Medium (50-79%)', count: medium },
      { category: 'Low (<50%)', count: low }
    ];
  }, [data]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Agent Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Evaluations by Agent</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {agentData.map((item) => (
              <div key={item.agent}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{item.agent}</span>
                  <span className="text-muted-foreground">{item.count} queries</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary rounded-full h-2"
                    style={{ width: `${(item.count / data.length) * 100}%` }}
                  />
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                  <span>Avg Grounding: {item.avgGrounding.toFixed(1)}%</span>
                  <span>Avg Confidence: {item.avgConfidence.toFixed(1)}%</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Grounding Quality Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Grounding Quality Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {groundingDistribution.map((item) => (
              <div key={item.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{item.category}</span>
                  <span className="text-muted-foreground">
                    {item.count} ({((item.count / data.length) * 100).toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className={`rounded-full h-2 ${
                      item.category.startsWith('High') ? 'bg-green-500' :
                      item.category.startsWith('Medium') ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${(item.count / data.length) * 100}%` }}
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

// Grounding Badge Component
const GroundingBadge: React.FC<{ score: number }> = ({ score }) => {
  const percentage = (score * 100).toFixed(0);
  const variant = score >= 0.8 ? 'high' : score >= 0.5 ? 'medium' : 'low';
  
  const styles = {
    high: 'bg-green-500/10 text-green-500 border-green-500/20',
    medium: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    low: 'bg-red-500/10 text-red-500 border-red-500/20'
  };

  const icons = {
    high: CheckCircle,
    medium: AlertCircle,
    low: XCircle
  };

  const Icon = icons[variant];

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${styles[variant]}`}>
      <Icon className="h-3 w-3" />
      {percentage}%
    </span>
  );
};

export default RagEvaluationsPage;
