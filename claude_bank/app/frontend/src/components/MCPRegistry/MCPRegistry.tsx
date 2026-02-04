import React, { useState, useEffect } from 'react';
import { RefreshCw, Search, Server, AlertCircle } from 'lucide-react';
import styles from '../AgentSystemMap/AgentSystemMapVertical.module.css';
import { MCPToolDetailsModal, MCPService } from './MCPToolDetailsModal';

interface MCPRegistryResponse {
    services: MCPService[];
    total_services: number;
    healthy_services: number;
    total_tools: number;
}

export const MCPRegistry: React.FC = () => {
    const [registryData, setRegistryData] = useState<MCPRegistryResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedService, setSelectedService] = useState<MCPService | null>(null);
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [filterStatus, setFilterStatus] = useState<'all' | 'healthy' | 'degraded' | 'offline'>('all');

    // Fetch MCP registry data
    const fetchMCPRegistry = async () => {
        setLoading(true);
        setError(null);
        
        try {
            const response = await fetch('http://localhost:8080/api/mcp-registry');
            
            if (!response.ok) {
                throw new Error(`Failed to fetch MCP registry: ${response.statusText}`);
            }
            
            const data: MCPRegistryResponse = await response.json();
            setRegistryData(data);
        } catch (err: any) {
            console.error('Error fetching MCP registry:', err);
            setError(err.message || 'Failed to load MCP registry');
        } finally {
            setLoading(false);
        }
    };

    // Initial load
    useEffect(() => {
        fetchMCPRegistry();
    }, []);

    // Handle service card click
    const handleServiceClick = (service: MCPService) => {
        setSelectedService(service);
    };

    // Handle modal close
    const handleCloseModal = () => {
        setSelectedService(null);
    };

    // Filter services based on search and status
    const filteredServices = registryData?.services.filter(service => {
        // Search filter
        const matchesSearch = searchQuery === '' || 
            service.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            service.tools.some(tool => 
                tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                tool.description.toLowerCase().includes(searchQuery.toLowerCase())
            );
        
        // Status filter
        const matchesStatus = filterStatus === 'all' || service.status === filterStatus;
        
        return matchesSearch && matchesStatus;
    }) || [];

    // Status emoji helper
    const getStatusEmoji = (status: string) => {
        switch (status) {
            case 'healthy':
                return '🟢';
            case 'degraded':
                return '🟡';
            case 'offline':
                return '🔴';
            default:
                return '⚪';
        }
    };

    // Status color helper
    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy':
                return '#10b981'; // green
            case 'degraded':
                return '#f59e0b'; // yellow
            case 'offline':
                return '#ef4444'; // red
            default:
                return '#6b7280'; // gray
        }
    };

    return (
        <div className={styles.agentMapContainer}>
            {/* Header Section */}
            <div className={styles.mapHeader}>
                <div className={styles.headerLeft}>
                    <Server size={24} />
                    <div className={styles.headerTitle}>
                        <h2>MCP Service Registry</h2>
                        {registryData && (
                            <span className={styles.headerSubtitle}>
                                {registryData.healthy_services}/{registryData.total_services} services healthy • {registryData.total_tools} tools
                            </span>
                        )}
                    </div>
                </div>
                <button 
                    className={styles.refreshButton}
                    onClick={fetchMCPRegistry}
                    disabled={loading}
                    title="Refresh registry"
                >
                    <RefreshCw size={16} className={loading ? styles.spinning : ''} />
                </button>
            </div>

            {/* Search and Filter Bar */}
            <div className={styles.filterBar}>
                <div className={styles.searchContainer}>
                    <Search size={16} className={styles.searchIcon} />
                    <input
                        type="text"
                        className={styles.searchInput}
                        placeholder="Search services or tools..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                
                <div className={styles.statusFilter}>
                    <button
                        className={`${styles.filterButton} ${filterStatus === 'all' ? styles.active : ''}`}
                        onClick={() => setFilterStatus('all')}
                    >
                        All
                    </button>
                    <button
                        className={`${styles.filterButton} ${filterStatus === 'healthy' ? styles.active : ''}`}
                        onClick={() => setFilterStatus('healthy')}
                    >
                        🟢 Healthy
                    </button>
                    <button
                        className={`${styles.filterButton} ${filterStatus === 'degraded' ? styles.active : ''}`}
                        onClick={() => setFilterStatus('degraded')}
                    >
                        🟡 Degraded
                    </button>
                    <button
                        className={`${styles.filterButton} ${filterStatus === 'offline' ? styles.active : ''}`}
                        onClick={() => setFilterStatus('offline')}
                    >
                        🔴 Offline
                    </button>
                </div>
            </div>

            {/* Main Content */}
            <div className={styles.contentArea}>
                {loading ? (
                    <div className={styles.loadingState}>
                        <RefreshCw size={32} className={styles.spinning} />
                        <p>Loading MCP registry...</p>
                    </div>
                ) : error ? (
                    <div className={styles.errorState}>
                        <AlertCircle size={32} />
                        <p>{error}</p>
                        <button className={styles.retryButton} onClick={fetchMCPRegistry}>
                            Retry
                        </button>
                    </div>
                ) : filteredServices.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Server size={32} />
                        <p>No services found matching your criteria</p>
                    </div>
                ) : (
                    <div className={styles.servicesGrid}>
                        {filteredServices.map((service) => (
                            <div
                                key={service.name}
                                className={styles.serviceCard}
                                onClick={() => handleServiceClick(service)}
                                style={{
                                    borderLeftColor: getStatusColor(service.status),
                                    borderLeftWidth: '4px',
                                    borderLeftStyle: 'solid'
                                }}
                            >
                                {/* Service Header */}
                                <div className={styles.serviceHeader}>
                                    <div className={styles.serviceName}>
                                        <Server size={18} />
                                        <span>{service.name}</span>
                                    </div>
                                    <span 
                                        className={styles.serviceStatus}
                                        title={service.status}
                                    >
                                        {getStatusEmoji(service.status)}
                                    </span>
                                </div>

                                {/* Service Info */}
                                <div className={styles.serviceInfo}>
                                    <div className={styles.servicePort}>
                                        Port: <code>{service.port}</code>
                                    </div>
                                    <div className={styles.serviceToolCount}>
                                        {service.tools.length} tool{service.tools.length !== 1 ? 's' : ''}
                                    </div>
                                </div>

                                {/* Tool Preview */}
                                {service.tools.length > 0 && (
                                    <div className={styles.toolsPreview}>
                                        {service.tools.slice(0, 3).map((tool, idx) => (
                                            <div key={idx} className={styles.toolPreviewItem}>
                                                <code>{tool.name}</code>
                                            </div>
                                        ))}
                                        {service.tools.length > 3 && (
                                            <div className={styles.toolPreviewMore}>
                                                +{service.tools.length - 3} more
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* Used By Agents */}
                                {service.used_by_agents.length > 0 && (
                                    <div className={styles.usedByAgents}>
                                        <span className={styles.usedByLabel}>Used by:</span>
                                        {service.used_by_agents.slice(0, 2).map((agent, idx) => (
                                            <span key={idx} className={styles.agentTag}>
                                                {agent}
                                            </span>
                                        ))}
                                        {service.used_by_agents.length > 2 && (
                                            <span className={styles.agentTagMore}>
                                                +{service.used_by_agents.length - 2}
                                            </span>
                                        )}
                                    </div>
                                )}

                                {/* Error Indicator */}
                                {service.error_message && (
                                    <div className={styles.errorIndicator}>
                                        <AlertCircle size={14} />
                                        <span>{service.error_message}</span>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Service Details Modal */}
            {selectedService && (
                <MCPToolDetailsModal
                    service={selectedService}
                    onClose={handleCloseModal}
                />
            )}
        </div>
    );
};
