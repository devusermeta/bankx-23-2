import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Activity, Check, AlertCircle, Loader2 } from 'lucide-react';
import styles from './AgentActivityPanel.module.css';

interface AgentActivity {
    timestamp: string;
    session_id: string;
    agent_name: string;
    activity_type: string;
    message: string;
    details?: Record<string, any>;
}

interface AgentActivityPanelProps {
    sessionId: string;
    isProcessing: boolean;
}

export const AgentActivityPanel: React.FC<AgentActivityPanelProps> = ({
    sessionId,
    isProcessing
}) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [activities, setActivities] = useState<AgentActivity[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    // Fetch activities when expanded or when processing
    useEffect(() => {
        if (!sessionId) return;

        const fetchActivities = async () => {
            try {
                setIsLoading(true);
                const response = await fetch(`/api/agent-activity/${sessionId}?limit=20`);
                if (response.ok) {
                    const data = await response.json();
                    setActivities(data.activities || []);
                }
            } catch (error) {
                console.error('Error fetching agent activities:', error);
            } finally {
                setIsLoading(false);
            }
        };

        if (isExpanded || isProcessing) {
            fetchActivities();
            // Poll every 2 seconds while processing
            if (isProcessing) {
                const interval = setInterval(fetchActivities, 2000);
                return () => clearInterval(interval);
            }
        }
    }, [sessionId, isExpanded, isProcessing]);

    const getActivityIcon = (activityType: string) => {
        switch (activityType) {
            case 'agent_completed':
                return <Check size={16} className={styles.iconSuccess} />;
            case 'error':
                return <AlertCircle size={16} className={styles.iconError} />;
            case 'agent_started':
            case 'tool_call':
            case 'decision':
                return <Activity size={16} className={styles.iconActivity} />;
            default:
                return <Activity size={16} className={styles.iconDefault} />;
        }
    };

    const formatTime = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        } catch {
            return timestamp;
        }
    };

    const getAgentColor = (agentName: string) => {
        const colors: Record<string, string> = {
            'SupervisorAgent': '#3b82f6',
            'PaymentAgent': '#10b981',
            'AccountAgent': '#8b5cf6',
            'TransactionAgent': '#f59e0b',
            'AIMoneyCoachAgent': '#ef4444',
            'ProdInfoFAQAgent': '#06b6d4',
            'EscalationCommsAgent': '#ec4899'
        };
        return colors[agentName] || '#6b7280';
    };

    return (
        <div className={styles.container}>
            <button
                className={styles.header}
                onClick={() => setIsExpanded(!isExpanded)}
                aria-expanded={isExpanded}
            >
                <div className={styles.headerLeft}>
                    <Activity size={20} className={styles.headerIcon} />
                    <h3 className={styles.title}>Agent Activity</h3>
                    {isProcessing && (
                        <Loader2 size={16} className={styles.loadingSpinner} />
                    )}
                </div>
                <div className={styles.headerRight}>
                    {activities.length > 0 && (
                        <span className={styles.badge}>{activities.length}</span>
                    )}
                    {isExpanded ? (
                        <ChevronUp size={20} className={styles.chevron} />
                    ) : (
                        <ChevronDown size={20} className={styles.chevron} />
                    )}
                </div>
            </button>

            <div className={`${styles.content} ${isExpanded ? styles.contentExpanded : ''}`}>
                {isLoading && activities.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Loader2 size={32} className={styles.loadingSpinner} />
                        <p>Loading activities...</p>
                    </div>
                ) : activities.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Activity size={32} className={styles.emptyIcon} />
                        <p>No agent activity yet</p>
                        <span className={styles.emptySubtext}>
                            Activity will appear here when agents start processing
                        </span>
                    </div>
                ) : (
                    <div className={styles.activityList}>
                        {activities.map((activity, index) => (
                            <div key={index} className={styles.activityItem}>
                                <div className={styles.activityHeader}>
                                    <div className={styles.activityAgent}>
                                        <span
                                            className={styles.agentDot}
                                            style={{ backgroundColor: getAgentColor(activity.agent_name) }}
                                        />
                                        <span className={styles.agentName}>
                                            {activity.agent_name}
                                        </span>
                                    </div>
                                    <span className={styles.activityTime}>
                                        {formatTime(activity.timestamp)}
                                    </span>
                                </div>
                                <div className={styles.activityBody}>
                                    <div className={styles.activityIcon}>
                                        {getActivityIcon(activity.activity_type)}
                                    </div>
                                    <div className={styles.activityContent}>
                                        <p className={styles.activityMessage}>
                                            {activity.message}
                                        </p>
                                        {activity.details && Object.keys(activity.details).length > 0 && (
                                            <div className={styles.activityDetails}>
                                                {Object.entries(activity.details).map(([key, value]) => (
                                                    <div key={key} className={styles.detailItem}>
                                                        <span className={styles.detailKey}>{key}:</span>
                                                        <span className={styles.detailValue}>
                                                            {typeof value === 'object' 
                                                                ? JSON.stringify(value) 
                                                                : String(value)
                                                            }
                                                        </span>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
