import React, { useState, useMemo, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { dashboardApi, type UserMessage } from '@/api/dashboardApi';
import { Search, Table as TableIcon, LayoutGrid, Clock, BarChart3, MessageSquare, Loader2, RefreshCw } from 'lucide-react';
import { usePagination } from '@/hooks/usePagination';
import { Pagination } from '@/components/dashboard/Pagination';

type ViewMode = 'table' | 'card' | 'timeline' | 'chart';

const UserMessagesPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [data, setData] = useState<UserMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const result = await dashboardApi.getUserMessages(undefined, 500);
      setData(result);
      setError(null);
    } catch (err) {
      console.error('Error fetching user messages:', err);
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
    return data.filter((message) => {
      const matchesSearch = 
        searchQuery === '' ||
        message.user_query.toLowerCase().includes(searchQuery.toLowerCase()) ||
        message.response_preview.toLowerCase().includes(searchQuery.toLowerCase()) ||
        message.thread_id.toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesType = selectedType === 'all' || message.message_type === selectedType;
      
      return matchesSearch && matchesType;
    });
  }, [searchQuery, selectedType, data]);

  // Get unique message types
  const uniqueTypes = useMemo(() => {
    return Array.from(new Set(data.map(m => m.message_type)));
  }, [data]);

  // Calculate stats
  // Pagination
  const pagination = usePagination(filteredData, 10);

  const stats = useMemo(() => {
    const avgDuration = filteredData.reduce((sum, m) => sum + m.duration_seconds, 0) / filteredData.length;
    const avgResponseLength = filteredData.reduce((sum, m) => sum + m.response_length, 0) / filteredData.length;
    const uniqueThreads = new Set(filteredData.map(m => m.thread_id)).size;
    
    return {
      total: filteredData.length,
      avgDuration: avgDuration.toFixed(2),
      avgResponseLength: avgResponseLength.toFixed(0),
      uniqueThreads
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
          <h1 className="text-3xl font-bold mb-2">User Messages</h1>
          <p className="text-muted-foreground">
            Monitor user queries, response quality, and conversation patterns
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
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Messages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgDuration}s</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Length</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avgResponseLength}</div>
            <p className="text-xs text-muted-foreground mt-1">characters</p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Threads</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.uniqueThreads}</div>
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
                placeholder="Search queries, responses, or threads..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            {/* Type Filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-4 py-2 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Types</option>
              {uniqueTypes.map(type => (
                <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
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
const TableView: React.FC<{ data: UserMessage[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Timestamp</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">User Query</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Response Preview</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Type</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Length</th>
              <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">Duration</th>
            </tr>
          </thead>
          <tbody>
            {data.map((message, idx) => (
              <tr key={`${message.timestamp}-${idx}`} className="border-b border-border hover:bg-muted/50">
                <td className="py-3 px-4 text-sm">
                  {new Date(message.timestamp).toLocaleString()}
                </td>
                <td className="py-3 px-4 text-sm max-w-xs truncate">{message.user_query}</td>
                <td className="py-3 px-4 text-sm max-w-md truncate text-muted-foreground">
                  {message.response_preview}
                </td>
                <td className="py-3 px-4 text-sm">
                  <MessageTypeBadge type={message.message_type} />
                </td>
                <td className="py-3 px-4 text-sm">{message.response_length}</td>
                <td className="py-3 px-4 text-sm">{message.duration_seconds}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </CardContent>
  </Card>
);

// Card View Component
const CardView: React.FC<{ data: UserMessage[] }> = ({ data }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    {data.map((message, idx) => (
      <Card key={`${message.timestamp}-${idx}`} className="hover:shadow-lg transition-shadow">
        <CardHeader>
          <div className="flex justify-between items-start mb-2">
            <MessageTypeBadge type={message.message_type} />
            <span className="text-xs text-muted-foreground">{message.duration_seconds}s</span>
          </div>
          <CardDescription className="text-xs">
            {new Date(message.timestamp).toLocaleString()}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">Query</p>
              <p className="text-sm text-muted-foreground line-clamp-2">{message.user_query}</p>
            </div>
            <div>
              <p className="text-sm font-medium mb-1">Response</p>
              <p className="text-sm text-muted-foreground line-clamp-3">{message.response_preview}</p>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Length: {message.response_length} chars</span>
              <span>Thread: {message.thread_id.slice(-8)}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    ))}
  </div>
);

// Timeline View Component
const TimelineView: React.FC<{ data: UserMessage[] }> = ({ data }) => (
  <Card>
    <CardContent className="pt-6">
      <div className="space-y-4">
        {data.map((message, index) => (
          <div key={`${message.timestamp}-${index}`} className="flex gap-4">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full ${
                message.duration_seconds < 3 ? 'bg-green-500' : 
                message.duration_seconds < 6 ? 'bg-yellow-500' : 
                'bg-red-500'
              }`} />
              {index < data.length - 1 && <div className="w-0.5 h-full bg-border mt-2" />}
            </div>
            <div className="flex-1 pb-8">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <p className="text-sm text-muted-foreground">
                    {new Date(message.timestamp).toLocaleString()}
                  </p>
                </div>
                <MessageTypeBadge type={message.message_type} />
              </div>
              <div className="mb-2">
                <p className="text-sm font-medium mb-1">User Query:</p>
                <p className="text-sm">{message.user_query}</p>
              </div>
              <div className="mb-2">
                <p className="text-sm font-medium mb-1">Response:</p>
                <p className="text-sm text-muted-foreground line-clamp-2">{message.response_preview}</p>
              </div>
              <div className="flex gap-4 text-xs text-muted-foreground">
                <span>Duration: {message.duration_seconds}s</span>
                <span>Length: {message.response_length} chars</span>
                <span>Thread: {message.thread_id.slice(-8)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

// Chart View Component
const ChartView: React.FC<{ data: UserMessage[] }> = ({ data }) => {
  // Group by message type
  const typeData = useMemo(() => {
    const grouped = data.reduce((acc, message) => {
      if (!acc[message.message_type]) {
        acc[message.message_type] = { count: 0, totalDuration: 0, totalLength: 0 };
      }
      acc[message.message_type].count++;
      acc[message.message_type].totalDuration += message.duration_seconds;
      acc[message.message_type].totalLength += message.response_length;
      return acc;
    }, {} as Record<string, { count: number; totalDuration: number; totalLength: number }>);

    return Object.entries(grouped).map(([type, stats]) => ({
      type,
      count: stats.count,
      avgDuration: stats.totalDuration / stats.count,
      avgLength: stats.totalLength / stats.count
    })).sort((a, b) => b.count - a.count);
  }, [data]);

  // Response time distribution
  const durationBuckets = useMemo(() => {
    const fast = data.filter(m => m.duration_seconds < 3).length;
    const medium = data.filter(m => m.duration_seconds >= 3 && m.duration_seconds < 6).length;
    const slow = data.filter(m => m.duration_seconds >= 6).length;
    
    return [
      { label: 'Fast (<3s)', count: fast, color: 'bg-green-500' },
      { label: 'Medium (3-6s)', count: medium, color: 'bg-yellow-500' },
      { label: 'Slow (≥6s)', count: slow, color: 'bg-red-500' }
    ];
  }, [data]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* Message Type Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Messages by Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {typeData.map((item) => (
              <div key={item.type}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{item.type.replace(/_/g, ' ')}</span>
                  <span className="text-muted-foreground">{item.count} messages</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary rounded-full h-2"
                    style={{ width: `${(item.count / data.length) * 100}%` }}
                  />
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground mt-1">
                  <span>Avg Duration: {item.avgDuration.toFixed(2)}s</span>
                  <span>Avg Length: {item.avgLength.toFixed(0)} chars</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Response Time Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Response Time Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {durationBuckets.map((bucket) => (
              <div key={bucket.label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium">{bucket.label}</span>
                  <span className="text-muted-foreground">
                    {bucket.count} ({((bucket.count / data.length) * 100).toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className={`rounded-full h-2 ${bucket.color}`}
                    style={{ width: `${(bucket.count / data.length) * 100}%` }}
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

// Message Type Badge Component
const MessageTypeBadge: React.FC<{ type: string }> = ({ type }) => {
  const colors: Record<string, string> = {
    'account_inquiry': 'bg-blue-500/10 text-blue-500 border-blue-500/20',
    'transaction_inquiry': 'bg-purple-500/10 text-purple-500 border-purple-500/20',
    'payment_request': 'bg-green-500/10 text-green-500 border-green-500/20',
    'general_inquiry': 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    'coaching_request': 'bg-pink-500/10 text-pink-500 border-pink-500/20'
  };

  const color = colors[type] || 'bg-gray-500/10 text-gray-500 border-gray-500/20';

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border ${color}`}>
      <MessageSquare className="h-3 w-3" />
      {type.replace(/_/g, ' ')}
    </span>
  );
};

export default UserMessagesPage;
