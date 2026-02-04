import React from 'react';
import { X } from 'lucide-react';
import styles from '../AgentSystemMap/AgentSystemMapVertical.module.css';

export interface MCPToolParameter {
    name: string;
    type: string;
    description: string;
    required: boolean;
}

export interface MCPTool {
    name: string;
    description: string;
    parameters: MCPToolParameter[];
}

export interface MCPService {
    name: string;
    port: number;
    status: 'healthy' | 'degraded' | 'offline';
    url: string;
    tools: MCPTool[];
    used_by_agents: string[];
    error_message?: string;
}

interface MCPToolDetailsModalProps {
    service: MCPService;
    onClose: () => void;
}

export const MCPToolDetailsModal: React.FC<MCPToolDetailsModalProps> = ({ service, onClose }) => {
    // Status emoji mapping
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

    // Status label mapping
    const getStatusLabel = (status: string) => {
        return status.charAt(0).toUpperCase() + status.slice(1);
    };

    return (
        <div className={styles.modalOverlay} onClick={onClose}>
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
                <div className={styles.modalHeader}>
                    <div className={styles.modalHeaderContent}>
                        <h3 className={styles.modalTitle}>
                            {service.name} MCP Service
                        </h3>
                        <div className={styles.modalSubtitle}>
                            Port {service.port}
                        </div>
                    </div>
                    <button className={styles.modalCloseButton} onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>
                
                <div className={styles.modalBody}>
                    <div className={styles.mcpDetailsContainer}>
                        {/* Status Section */}
                        <div className={styles.detailSection}>
                            <div className={styles.detailLabel}>Status</div>
                            <div className={styles.detailValue}>
                                <span className={`${styles.statusBadge} ${styles[`status${getStatusLabel(service.status)}`]}`}>
                                    {getStatusEmoji(service.status)} {getStatusLabel(service.status)}
                                </span>
                            </div>
                        </div>

                        {/* Error Message if present */}
                        {service.error_message && (
                            <div className={styles.detailSection}>
                                <div className={styles.detailLabel}>Error</div>
                                <div className={`${styles.detailValue} ${styles.errorMessage}`}>
                                    {service.error_message}
                                </div>
                            </div>
                        )}

                        {/* Service URL */}
                        <div className={styles.detailSection}>
                            <div className={styles.detailLabel}>Service URL</div>
                            <div className={styles.detailValue}>
                                <code className={styles.codeBlock}>{service.url}</code>
                            </div>
                        </div>

                        {/* Available Tools Section */}
                        <div className={styles.detailSection}>
                            <div className={styles.detailLabel}>
                                📋 Available Tools ({service.tools.length})
                            </div>
                            {service.tools.length > 0 ? (
                                <div className={styles.toolsList}>
                                    {service.tools.map((tool, idx) => (
                                        <div key={idx} className={styles.toolCard}>
                                            <div className={styles.toolHeader}>
                                                <span className={styles.toolNumber}>{idx + 1}.</span>
                                                <span className={styles.toolName}>{tool.name}</span>
                                            </div>
                                            <div className={styles.toolDescription}>
                                                {tool.description || 'No description available'}
                                            </div>
                                            
                                            {tool.parameters.length > 0 && (
                                                <>
                                                    <div className={styles.parametersLabel}>Parameters:</div>
                                                    <div className={styles.toolParameters}>
                                                        {tool.parameters.map((param, paramIdx) => (
                                                            <div key={paramIdx} className={styles.parameter}>
                                                                <div className={styles.parameterHeader}>
                                                                    <code className={styles.parameterName}>
                                                                        {param.name}
                                                                    </code>
                                                                    <span className={styles.parameterType}>
                                                                        {param.type}
                                                                    </span>
                                                                    {param.required && (
                                                                        <span className={styles.requiredBadge}>required</span>
                                                                    )}
                                                                </div>
                                                                {param.description && (
                                                                    <div className={styles.parameterDescription}>
                                                                        {param.description}
                                                                    </div>
                                                                )}
                                                            </div>
                                                        ))}
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className={styles.noTools}>
                                    No tools available
                                </div>
                            )}
                        </div>

                        {/* Used By Agents Section */}
                        <div className={styles.detailSection}>
                            <div className={styles.detailLabel}>
                                🤖 Used By Agents
                            </div>
                            {service.used_by_agents.length > 0 ? (
                                <div className={styles.agentsList}>
                                    {service.used_by_agents.map((agent, idx) => (
                                        <span key={idx} className={styles.agentBadge}>
                                            • {agent}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <div className={styles.noAgents}>
                                    Not used by any specific agent (system-wide)
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Close Button */}
                    <div className={styles.modalFooter}>
                        <button className={styles.closeButton} onClick={onClose}>
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
