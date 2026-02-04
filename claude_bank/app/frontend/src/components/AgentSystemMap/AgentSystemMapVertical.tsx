import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Activity, Workflow, ChevronRight, Info, RefreshCw, Plus, Trash2, X } from 'lucide-react';
import styles from './AgentSystemMapVertical.module.css';
import { useAgentStatus } from '../../hooks/useAgentStatus';
import { MCPRegistry } from '../MCPRegistry/MCPRegistry';

export interface AgentEvent {
    type: 'agent_routing' | 'agent_handoff' | 'mcp_tool_call' | 'text_chunk' | 'thinking';
    timestamp: string;
    agent?: string;
    from_agent?: string;
    to_agent?: string;
    tool_name?: string;
    step?: string;
    message?: string;
    cached?: boolean;
}

interface AgentSystemMapVerticalProps {
    latestEvent: AgentEvent | null;
    activeAgent: string | null;
    isStreaming: boolean;
    isThinkingPanelVisible: boolean;
}

export interface AgentSystemMapVerticalRef {
    clearAndShowSupervisor: () => void;
}

type NodeId = 'supervisor' | 'payment' | 'account' | 'transaction' | 'prodinfo' | 'coach' | 'escalation' | 'mcp_tools';

interface NodeInfo {
    id: NodeId;
    label: string;
    icon: string;
    type: 'coordinator' | 'agent' | 'tool';
    description: string;
    status?: 'running' | 'stopped' | 'unknown';
}

interface AgentCardDetails {
    name: string;
    description: string;
    url?: string;
    version: string;
    capabilities: string[];
    agent_id?: string;
    blueprint_id?: string;
    object_id?: string;
    endpoints?: {
        chat?: string;
        health?: string;
    };
    protocol?: string;
    platform?: string;
    mcp_backed?: boolean;
    foundry_v2_hosted?: boolean;
    metadata?: Record<string, any>;
}

// Agent URLs for API calls
const AGENT_URLS: Record<string, string> = {
    supervisor: 'http://localhost:9000',
    payment: 'http://localhost:9002',
    account: 'http://localhost:9001',
    transaction: 'http://localhost:9003',
    prodinfo: 'http://localhost:9004',
    coach: 'http://localhost:9005',
    escalation: 'http://localhost:9006',
};

const NODES: NodeInfo[] = [
    { 
        id: 'supervisor', 
        label: 'Supervisor', 
        icon: '🎯', 
        type: 'coordinator',
        description: 'Orchestrates agent routing and manages conversation flow'
    },
    { 
        id: 'payment', 
        label: 'Payment Agent', 
        icon: '💸', 
        type: 'agent',
        description: 'Handles payment processing, beneficiary management, and transaction execution'
    },
    { 
        id: 'account', 
        label: 'Account Agent', 
        icon: '🏦', 
        type: 'agent',
        description: 'Manages account resolution, balance inquiries, and limits checking'
    },
    { 
        id: 'transaction', 
        label: 'Transaction Agent', 
        icon: '📊', 
        type: 'agent',
        description: 'Handles transaction history, analytics, and reporting'
    },
    { 
        id: 'prodinfo', 
        label: 'Product Info Agent', 
        icon: '📚', 
        type: 'agent',
        description: 'Provides product information and answers FAQs'
    },
    { 
        id: 'coach', 
        label: 'AI Money Coach', 
        icon: '🤖', 
        type: 'agent',
        description: 'Offers financial advice and personalized coaching'
    },
    { 
        id: 'escalation', 
        label: 'Escalation Agent', 
        icon: '🎫', 
        type: 'agent',
        description: 'Handles complex issues and escalates to human support'
    }
];

const AGENT_NODE_MAP: Record<string, NodeId> = {
    'supervisor': 'supervisor',
    'supervisoragent': 'supervisor',
    'payment': 'payment',
    'paymentagent': 'payment',
    'account': 'account',
    'accountagent': 'account',
    'transaction': 'transaction',
    'transactionagent': 'transaction',
    'prodinfo': 'prodinfo',
    'productinfo': 'prodinfo',
    'prodinfoagent': 'prodinfo',
    'prodinfofaqagent': 'prodinfo',
    'coach': 'coach',
    'aimoneycoach': 'coach',
    'aimoneycoachagent': 'coach',
    'escalation': 'escalation',
    'escalationagent': 'escalation',
};

export const AgentSystemMapVertical = forwardRef<AgentSystemMapVerticalRef, AgentSystemMapVerticalProps>(({
    latestEvent,
    activeAgent,
    isStreaming,
    isThinkingPanelVisible
}, ref) => {
    const [activeNodes, setActiveNodes] = useState<Set<NodeId>>(new Set());
    const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set());
    const [cachedNodes, setCachedNodes] = useState<Set<NodeId>>(new Set());
    const [lastAgentEvent, setLastAgentEvent] = useState<{agent: NodeId, cached: boolean} | null>(null);
    const [isThinking, setIsThinking] = useState<boolean>(false);
    const [selectedAgent, setSelectedAgent] = useState<NodeId | null>(null);
    const [hoveredAgent, setHoveredAgent] = useState<NodeId | null>(null);
    const [agentCardDetails, setAgentCardDetails] = useState<AgentCardDetails | null>(null);
    const [loadingDetails, setLoadingDetails] = useState<boolean>(false);
    const [showAddAgentModal, setShowAddAgentModal] = useState<boolean>(false);
    const [newAgentUrl, setNewAgentUrl] = useState<string>('');
    const [addAgentError, setAddAgentError] = useState<string | null>(null);
    const [addAgentSuccess, setAddAgentSuccess] = useState<string | null>(null);
    const [isAddingAgent, setIsAddingAgent] = useState<boolean>(false);
    const [dynamicNodes, setDynamicNodes] = useState<NodeInfo[]>([]);
    const [isLoadingNodes, setIsLoadingNodes] = useState<boolean>(true);
    const [viewMode, setViewMode] = useState<'agent-map' | 'mcp-registry'>('agent-map');

    // Agent status checking - will be updated after nodes are loaded
    const agentIds = dynamicNodes.filter(n => n.type === 'agent' || n.type === 'coordinator').map(n => n.id);
    const { statuses, isChecking, refresh } = useAgentStatus(agentIds);

    // Fetch agent list dynamically from backend
    const fetchAgentList = async () => {
        setIsLoadingNodes(true);
        try {
            const response = await fetch('http://localhost:8080/api/agent-cards');
            if (!response.ok) {
                throw new Error('Failed to fetch agent list');
            }
            
            const data = await response.json();
            const agents = data.agents || {};
            
            // Define fixed positions for agents
            const agentOrder: Record<string, number> = {
                supervisor: 0,
                account: 1,
                payment: 2,
                transaction: 3,
                prodinfo: 4,
                coach: 5,
                escalation: 6,
            };
            
            // Convert to NodeInfo array
            const nodes: NodeInfo[] = [];
            
            // Add agents from the response
            for (const [agentId, agentData] of Object.entries<any>(agents)) {
                // Determine type - supervisor is coordinator, others are agents
                const type = agentId === 'supervisor' ? 'coordinator' : 'agent';
                
                // Get icon and description from agent data or use defaults
                const defaultIcons: Record<string, string> = {
                    supervisor: '🎯',
                    payment: '💸',
                    account: '🏦',
                    transaction: '📊',
                    prodinfo: '📚',
                    coach: '🤖',
                    escalation: '🎫',
                };
                
                const normalizedId = normalizeAgentId(agentId);
                
                nodes.push({
                    id: agentId as NodeId,
                    label: agentData.name || agentId,
                    icon: defaultIcons[agentId] || '🤖',
                    type,
                    description: agentData.description || '',
                    status: agentData.status,
                });
            }
            
            // Sort nodes by predefined order, custom agents go to the end
            nodes.sort((a, b) => {
                const normalizedA = normalizeAgentId(a.id);
                const normalizedB = normalizeAgentId(b.id);
                const orderA = agentOrder[normalizedA] !== undefined ? agentOrder[normalizedA] : 999;
                const orderB = agentOrder[normalizedB] !== undefined ? agentOrder[normalizedB] : 999;
                return orderA - orderB;
            });
            
            setDynamicNodes(nodes);
        } catch (error) {
            console.error('Failed to fetch agent list:', error);
            // Fallback to static NODES if fetch fails
            setDynamicNodes(NODES);
        } finally {
            setIsLoadingNodes(false);
        }
    };

    // Fetch agent list on mount
    useEffect(() => {
        fetchAgentList();
    }, []);

    // Expose method to parent via ref
    useImperativeHandle(ref, () => ({
        clearAndShowSupervisor: () => {
            console.log('🗺️ [MAP] clearAndShowSupervisor called via ref');
            setActiveNodes(new Set(['supervisor']));
            setActiveEdges(new Set());
            setCachedNodes(new Set());
            setIsThinking(true);
            setSelectedAgent(null);
        }
    }));

    // Convert agent name to node ID - now searches dynamic nodes
    const getNodeIdFromAgent = (agentName?: string): NodeId | null => {
        if (!agentName) return null;
        
        // Normalize the incoming agent name
        const normalized = agentName.toLowerCase().replace(/[_\s-]/g, '');
        
        console.log(`🗺️ [MAP] getNodeIdFromAgent called with "${agentName}", dynamicNodes count: ${dynamicNodes.length}`);
        
        // First try the old AGENT_NODE_MAP for backward compatibility
        const staticNodeId = AGENT_NODE_MAP[normalized];
        if (staticNodeId) {
            // Now find the actual dynamic node that matches this type
            const matchingNode = dynamicNodes.find(node => {
                const nodeNormalized = normalizeAgentId(node.id);
                return nodeNormalized === staticNodeId;
            });
            
            if (matchingNode) {
                console.log(`🗺️ [MAP] getNodeIdFromAgent: "${agentName}" → normalized: "${normalized}" → static: "${staticNodeId}" → dynamic: "${matchingNode.id}"`);
                return matchingNode.id as NodeId;
            } else {
                console.log(`🗺️ [MAP] getNodeIdFromAgent: "${agentName}" → found static "${staticNodeId}" but no matching dynamic node`);
            }
        }
        
        console.log(`🗺️ [MAP] getNodeIdFromAgent: "${agentName}" → not found`);
        return null;
    };
    
    // Helper to normalize agent ID (reuse from fetchAgentList)
    const normalizeAgentId = (agentId: string): string => {
        const baseName = agentId.split(':')[0].toLowerCase();
        
        if (baseName.includes('payment')) return 'payment';
        if (baseName.includes('account')) return 'account';
        if (baseName.includes('transaction')) return 'transaction';
        if (baseName.includes('prodinfo') || baseName.includes('productinfo')) return 'prodinfo';
        if (baseName.includes('coach')) return 'coach';
        if (baseName.includes('escalation')) return 'escalation';
        if (baseName.includes('supervisor')) return 'supervisor';
        
        return agentId;
    };

    // Process incoming events
    useEffect(() => {
        if (!latestEvent) return;

        console.log(`🗺️ [MAP] ⭐ NEW EVENT RECEIVED:`, {
            type: latestEvent.type,
            step: latestEvent.step,
            message: latestEvent.message,
            agent: latestEvent.agent,
            cached: latestEvent.cached,
            fullEvent: latestEvent
        });

        const newActiveNodes = new Set<NodeId>();
        const newActiveEdges = new Set<string>();

        switch (latestEvent.type) {
            case 'agent_routing':
            case 'agent_handoff':
                const fromNode = getNodeIdFromAgent(latestEvent.from_agent || 'supervisor');
                const toNode = getNodeIdFromAgent(latestEvent.to_agent);
                
                setIsThinking(false);
                
                if (fromNode) newActiveNodes.add(fromNode);
                if (toNode) newActiveNodes.add(toNode);
                if (fromNode && toNode) {
                    newActiveEdges.add(`${fromNode}-${toNode}`);
                }
                break;

            case 'mcp_tool_call':
                const agentNode = getNodeIdFromAgent(latestEvent.agent);
                if (agentNode) {
                    newActiveNodes.add(agentNode);
                    newActiveNodes.add('mcp_tools');
                    newActiveEdges.add(`${agentNode}-mcp_tools`);
                }
                break;

            case 'text_chunk':
                const textAgentNode = getNodeIdFromAgent(latestEvent.agent);
                if (textAgentNode) {
                    newActiveNodes.add(textAgentNode);
                }
                break;

            case 'thinking':
                console.log(`🗺️ [MAP] Processing thinking event - Step: "${latestEvent.step}", Message: "${latestEvent.message}"`);
                
                if (latestEvent.step === 'analyzing') {
                    console.log('🧹 [MAP] Clearing previous highlights for new question');
                    setActiveNodes(new Set(['supervisor']));
                    setActiveEdges(new Set());
                    setCachedNodes(new Set());
                    setIsThinking(true);
                    break;
                }
                
                if (latestEvent.step === 'routing') {
                    console.log('🎯 [MAP] Routing step detected - stopping thinking animation');
                    setIsThinking(false);
                    
                    const message = latestEvent.message || '';
                    const agentMatch = message.match(/(\w+(?:\s+\w+)*)\s+Agent\s+selected/i);
                    if (agentMatch) {
                        const agentName = agentMatch[1].trim();
                        console.log(`🔍 [MAP] Extracted agent name from routing: "${agentName}"`);
                        const selectedAgent = getNodeIdFromAgent(agentName);
                        if (selectedAgent) {
                            newActiveNodes.add('supervisor');
                            newActiveNodes.add(selectedAgent);
                            newActiveEdges.add(`supervisor-${selectedAgent}`);
                            console.log(`✅ [MAP] Activated from routing:`, Array.from(newActiveNodes));
                        }
                    }
                }
                
                if (latestEvent.agent) {
                    const selectedAgentNode = getNodeIdFromAgent(latestEvent.agent);
                    console.log(`🗺️ [MAP] Agent from event: ${latestEvent.agent}, Mapped to: ${selectedAgentNode}, cached: ${latestEvent.cached}`);
                    
                    if (selectedAgentNode) {
                        setIsThinking(false);
                        newActiveNodes.add('supervisor');
                        newActiveNodes.add(selectedAgentNode);
                        newActiveEdges.add(`supervisor-${selectedAgentNode}`);
                        
                        if (latestEvent.cached) {
                            setCachedNodes(new Set([selectedAgentNode]));
                            console.log(`💾 [MAP] Setting cached node: ${selectedAgentNode}`);
                        } else {
                            setCachedNodes(new Set());
                            console.log(`🗺️ [MAP] Clearing cached nodes (not cached)`);
                        }
                        
                        setLastAgentEvent({ agent: selectedAgentNode, cached: latestEvent.cached || false });
                        
                        console.log(`✅ [MAP] Activated nodes:`, Array.from(newActiveNodes), 'edges:', Array.from(newActiveEdges));
                    } else {
                        console.warn(`❌ [MAP] Could not map agent: ${latestEvent.agent}`);
                    }
                }
                break;
        }

        if (newActiveNodes.size > 0 || newActiveEdges.size > 0) {
            setActiveNodes(newActiveNodes);
            setActiveEdges(newActiveEdges);
        }
    }, [latestEvent, dynamicNodes]); // Added dynamicNodes dependency so mapping works

    // Keep active agent highlighted
    useEffect(() => {
        if (activeAgent && isStreaming) {
            const nodeId = getNodeIdFromAgent(activeAgent);
            if (nodeId) {
                setActiveNodes(prev => new Set([...prev, nodeId]));
            }
        }
    }, [activeAgent, isStreaming]);

    // Sync highlighting with thinking panel visibility
    useEffect(() => {
        if (!isThinkingPanelVisible) {
            console.log('🗺️ [MAP] 🧹 Thinking panel closed - clearing highlights');
            setActiveNodes(new Set());
            setActiveEdges(new Set());
            setCachedNodes(new Set());
        } else if (isThinkingPanelVisible && lastAgentEvent) {
            console.log('🗺️ [MAP] 🔄 Thinking panel opened - restoring highlights for:', lastAgentEvent.agent);
            setActiveNodes(new Set(['supervisor', lastAgentEvent.agent]));
            setActiveEdges(new Set([`supervisor-${lastAgentEvent.agent}`]));
            if (lastAgentEvent.cached) {
                setCachedNodes(new Set([lastAgentEvent.agent]));
            }
        }
    }, [isThinkingPanelVisible, lastAgentEvent]);

    const isNodeActive = (nodeId: NodeId) => activeNodes.has(nodeId);
    const isNodeThinking = (nodeId: NodeId) => nodeId === 'supervisor' && isThinking;
    const isEdgeActive = (from: NodeId, to: NodeId) => activeEdges.has(`${from}-${to}`);

    // Fetch agent card details from centralized copilot server endpoint
    const fetchAgentCardDetails = async (nodeId: NodeId) => {
        setLoadingDetails(true);
        try {
            // Use centralized endpoint on copilot server (port 8080)
            const response = await fetch(`http://localhost:8080/api/agent-cards/${nodeId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`Failed to fetch agent card: ${response.statusText}`);
            }

            const data = await response.json();
            
            // Check if agent is offline/error
            if (data.status && data.status !== 'online') {
                // Agent is offline, timeout, or error
                const fallbackDetails: AgentCardDetails = {
                    name: data.name || dynamicNodes.find((n) => n.id === nodeId)?.label || 'Unknown Agent',
                    description: dynamicNodes.find((n) => n.id === nodeId)?.description || 'Agent not responding',
                    url: data.base_url || AGENT_URLS[nodeId] || 'unknown',
                    version: 'unknown',
                    capabilities: ['Agent offline - unable to fetch capabilities'],
                    agent_id: nodeId,
                    endpoints: {
                        chat: `${data.base_url || AGENT_URLS[nodeId]}/a2a/invoke`,
                        health: `${data.base_url || AGENT_URLS[nodeId]}/health`,
                    },
                    protocol: 'a2a',
                    metadata: { 
                        status: data.status,
                        error: data.error || 'Agent not responding',
                        base_url: data.base_url
                    },
                };
                setAgentCardDetails(fallbackDetails);
                return;
            }
            
            // Agent is online - filter metadata to remove redundant fields
            const filteredMetadata = { ...data.metadata };
            // Remove agent_name and agent_version since they're shown in AGENT ID
            delete filteredMetadata.agent_name;
            delete filteredMetadata.agent_version;
            
            // Transform API response to our interface
            const cardDetails: AgentCardDetails = {
                name: data.name || dynamicNodes.find((n) => n.id === nodeId)?.label || 'Unknown Agent',
                description: data.description || dynamicNodes.find((n) => n.id === nodeId)?.description || '',
                url: data.base_url || data.url || AGENT_URLS[nodeId] || 'unknown',
                version: data.version || '1.0.0',
                capabilities: data.capabilities || [],
                agent_id: data.agent_id || nodeId,
                blueprint_id: data.blueprint_id,
                object_id: data.object_id,
                endpoints: data.endpoints || {
                    chat: data.endpoint ? `${data.base_url}${data.endpoint}` : `${data.base_url || AGENT_URLS[nodeId]}/a2a/invoke`,
                    health: `${data.base_url || AGENT_URLS[nodeId]}/health`,
                },
                protocol: data.protocol || 'a2a',
                platform: data.platform || undefined,
                mcp_backed: data.mcp_backed,
                foundry_v2_hosted: data.foundry_v2_hosted,
                metadata: filteredMetadata,
            };

            console.log('🔍 Agent Card Details:', {
                agent: nodeId,
                blueprint_id: cardDetails.blueprint_id,
                object_id: cardDetails.object_id,
                raw_data: { blueprint_id: data.blueprint_id, object_id: data.object_id }
            });

            setAgentCardDetails(cardDetails);
        } catch (error) {
            console.error(`Failed to fetch agent card details for ${nodeId}:`, error);
            // Fallback to basic info from dynamicNodes
            const fallbackDetails: AgentCardDetails = {
                name: dynamicNodes.find((n) => n.id === nodeId)?.label || 'Unknown Agent',
                description: dynamicNodes.find((n) => n.id === nodeId)?.description || 'Agent unavailable',
                url: AGENT_URLS[nodeId] || 'unknown',
                version: 'unknown',
                capabilities: ['Unable to fetch capabilities'],
                agent_id: nodeId,
                endpoints: {
                    chat: `${AGENT_URLS[nodeId]}/a2a/invoke`,
                    health: `${AGENT_URLS[nodeId]}/health`,
                },
                protocol: 'a2a',
                metadata: { error: 'Failed to fetch agent card' },
            };
            setAgentCardDetails(fallbackDetails);
        } finally {
            setLoadingDetails(false);
        }
    };

    // Get all agents (excluding coordinator) - use dynamic nodes
    const allAgents = dynamicNodes.filter(n => n.type === 'agent');

    const handleAgentClick = (nodeId: NodeId) => {
        setSelectedAgent(nodeId);
        fetchAgentCardDetails(nodeId);
    };

    const handleCloseModal = () => {
        setSelectedAgent(null);
        setAgentCardDetails(null);
    };

    const handleRefreshWithCards = () => {
        // Refresh agent list, health status, and agent card if modal is open
        fetchAgentList();
        refresh();
        if (selectedAgent) {
            fetchAgentCardDetails(selectedAgent);
        }
    };

    const handleAddAgent = async () => {
        if (!newAgentUrl.trim()) {
            setAddAgentError('Please enter an agent URL');
            return;
        }

        setIsAddingAgent(true);
        setAddAgentError(null);
        setAddAgentSuccess(null);

        try {
            const response = await fetch('http://localhost:8080/api/agent-cards/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: newAgentUrl.trim() }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to add agent');
            }

            const data = await response.json();
            setAddAgentSuccess(`Agent "${data.agent_name}" added successfully!`);
            setNewAgentUrl('');
            
            // Refresh agent list after short delay
            setTimeout(() => {
                fetchAgentList();
                refresh();
                setShowAddAgentModal(false);
                setAddAgentSuccess(null);
            }, 1500);
        } catch (error: any) {
            setAddAgentError(error.message || 'Failed to add agent');
        } finally {
            setIsAddingAgent(false);
        }
    };

    const handleRemoveAgent = async (nodeId: NodeId) => {
        if (!confirm(`Are you sure you want to remove the ${dynamicNodes.find(n => n.id === nodeId)?.label || nodeId} agent?`)) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8080/api/agent-cards/${nodeId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to remove agent');
            }

            // Close the modal and refresh
            handleCloseModal();
            fetchAgentList();
            refresh();
        } catch (error: any) {
            alert(`Failed to remove agent: ${error.message}`);
        }
    };

    const renderAgentCard = (node: NodeInfo) => {
        const isActive = isNodeActive(node.id);
        const agentStatus = statuses.get(node.id);
        const isThinkingNode = isNodeThinking(node.id);
        const isCached = cachedNodes.has(node.id);
        const isSelected = selectedAgent === node.id;
        const isHovered = hoveredAgent === node.id;
        
        // Debug logging
        // console.log(`Rendering ${node.id}: active=${isActive}, cached=${isCached}, cachedNodes=`, Array.from(cachedNodes));

        return (
            <div 
                key={node.id}
                className={`${styles.agentCard} ${isActive ? styles.active : ''} ${isThinkingNode ? styles.thinking : ''} ${isSelected ? styles.selected : ''}`}
                onClick={() => handleAgentClick(node.id)}
                onMouseEnter={() => setHoveredAgent(node.id)}
                onMouseLeave={() => setHoveredAgent(null)}
            >
                <div className={styles.agentCardHeader}>
                    <span className={styles.agentIcon}>{node.icon}</span>
                    <span className={styles.agentLabel}>{node.label}</span>
                    {agentStatus && (
                        <span className={`${styles.statusDot} ${styles[agentStatus.status]}`}></span>
                    )}
                    {isCached && <span className={styles.cacheBadge}>Cache</span>}
                </div>
                
                <div className={styles.agentDescription}>
                    {node.description && node.description.length > 80 
                        ? `${node.description.substring(0, 80)}...` 
                        : node.description}
                </div>
            </div>
        );
    };

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <Workflow size={20} />
                <h3>Agent System Map</h3>
                {!selectedAgent && (
                    <>
                        {/* View Toggle Buttons */}
                        <div className={styles.viewToggle}>
                            <button
                                className={`${styles.toggleButton} ${viewMode === 'agent-map' ? styles.active : ''}`}
                                onClick={() => setViewMode('agent-map')}
                            >
                                Agent Map
                            </button>
                            <button
                                className={`${styles.toggleButton} ${viewMode === 'mcp-registry' ? styles.active : ''}`}
                                onClick={() => setViewMode('mcp-registry')}
                            >
                                MCP Registry
                            </button>
                        </div>
                        
                        {viewMode === 'agent-map' && (
                            <>
                                <button 
                                    className={styles.addAgentButton}
                                    onClick={() => setShowAddAgentModal(true)}
                                    title="Add new agent"
                                >
                                    <Plus size={16} />
                                </button>
                                <button 
                                    className={styles.refreshButton}
                                    onClick={handleRefreshWithCards}
                                    disabled={isChecking}
                                    title="Refresh agent status and cards"
                                >
                                    <RefreshCw size={16} className={isChecking ? styles.spinning : ''} />
                                </button>
                            </>
                        )}
                    </>
                )}
                {viewMode === 'agent-map' && (
                    <div className={styles.legend}>
                        <span className={styles.legendItem}>
                            <span className={styles.legendDot} style={{ background: '#3b82f6' }}></span>
                            Active
                        </span>
                        <span className={styles.legendItem}>
                            <span className={styles.legendDot} style={{ background: '#10b981' }}></span>
                            Cached
                        </span>
                    </div>
                )}
            </div>

            {/* Show MCP Registry or Agent Map based on viewMode */}
            {viewMode === 'mcp-registry' ? (
                <MCPRegistry />
            ) : !selectedAgent ? (
                isLoadingNodes ? (
                    <div className={styles.verticalTimeline}>
                        <div className={styles.loadingContainer}>
                            <RefreshCw size={24} className={styles.spinning} />
                            <p>Loading agents...</p>
                        </div>
                    </div>
                ) : (
                <div className={styles.verticalTimeline}>
                    {/* Supervisor - Centered at Top */}
                    <div className={styles.supervisorRow}>
                    <div className={styles.agentSlot}></div>
                    <div className={styles.supervisorCenter}>
                        {dynamicNodes.find(n => n.id === 'supervisor') && renderAgentCard(dynamicNodes.find(n => n.id === 'supervisor')!)}
                        <div className={styles.timelineLine}>
                            <div className={styles.timelineDot}></div>
                        </div>
                    </div>
                    <div className={styles.agentSlot}></div>
                </div>

                {/* All Agents - Alternating Left/Right */}
                {allAgents.map((agent, index) => (
                    <div key={agent.id} className={styles.agentRow}>
                        {index % 2 === 0 ? (
                            <>
                                <div className={styles.agentSlot}>
                                    {renderAgentCard(agent)}
                                </div>
                                <div className={styles.timelineLine}>
                                    <div className={styles.timelineDot}></div>
                                </div>
                                <div className={styles.agentSlot}></div>
                            </>
                        ) : (
                            <>
                                <div className={styles.agentSlot}></div>
                                <div className={styles.timelineLine}>
                                    <div className={styles.timelineDot}></div>
                                </div>
                                <div className={styles.agentSlot}>
                                    {renderAgentCard(agent)}
                                </div>
                            </>
                        )}
                    </div>
                ))}
                </div>
                )
            ) : (
                /* Agent Card Details View */
                <div className={styles.cardViewContainer}>
                    <div className={styles.cardView}>
                        <div className={styles.cardHeader}>
                            <button className={styles.backButton} onClick={handleCloseModal}>
                                ← Back to Map
                            </button>
                            <h2>
                                {dynamicNodes.find(n => n.id === selectedAgent)?.icon} {dynamicNodes.find(n => n.id === selectedAgent)?.label}
                            </h2>
                            <button 
                                className={styles.removeButton} 
                                onClick={() => selectedAgent && handleRemoveAgent(selectedAgent)}
                                title="Remove this agent"
                            >
                                <Trash2 size={16} />
                                Remove Agent
                            </button>
                        </div>
                        
                        <div className={styles.cardBody}>
                            {loadingDetails ? (
                                <div className={styles.loading}>Loading agent details...</div>
                            ) : agentCardDetails ? (
                                <>
                                    <div className={styles.detailSection}>
                                        <div className={styles.detailLabel}>Description</div>
                                        <div className={styles.detailValue}>{agentCardDetails.description}</div>
                                    </div>

                                    <div className={styles.detailSection}>
                                        <div className={styles.detailLabel}>Version</div>
                                        <div className={styles.detailValue}>{agentCardDetails.version}</div>
                                    </div>

                                    <div className={styles.detailSection}>
                                        <div className={styles.detailLabel}>Agent ID</div>
                                        <div className={styles.detailValue}>{agentCardDetails.agent_id}</div>
                                    </div>

                                    {console.log('🎨 Rendering IDs:', { 
                                        blueprint_id: agentCardDetails.blueprint_id, 
                                        object_id: agentCardDetails.object_id,
                                        hasBlueprintId: !!agentCardDetails.blueprint_id,
                                        hasObjectId: !!agentCardDetails.object_id
                                    })}

                                    {agentCardDetails.blueprint_id && (
                                        <div className={styles.detailSection}>
                                            <div className={styles.detailLabel}>Blueprint ID</div>
                                            <div className={styles.detailValue}>{agentCardDetails.blueprint_id}</div>
                                        </div>
                                    )}

                                    {agentCardDetails.object_id && (
                                        <div className={styles.detailSection}>
                                            <div className={styles.detailLabel}>Object ID</div>
                                            <div className={styles.detailValue}>{agentCardDetails.object_id}</div>
                                        </div>
                                    )}

                                    <div className={styles.detailSection}>
                                        <div className={styles.detailLabel}>Protocol</div>
                                        <div className={styles.detailValue}>
                                            <span className={styles.protocol}>{agentCardDetails.protocol}</span>
                                        </div>
                                    </div>

                                    {agentCardDetails.platform && (
                                        <div className={styles.detailSection}>
                                            <div className={styles.detailLabel}>Platform</div>
                                            <div className={styles.detailValue}>
                                                <span className={styles.platform}>{agentCardDetails.platform}</span>
                                            </div>
                                        </div>
                                    )}

                                    <div className={styles.detailSection}>
                                        <div className={styles.detailLabel}>Capabilities</div>
                                        <div className={styles.capabilitiesList}>
                                            {agentCardDetails.capabilities.map((cap, idx) => (
                                                <span key={idx} className={styles.capability}>{cap}</span>
                                            ))}
                                        </div>
                                    </div>

                                    {agentCardDetails.endpoints && (
                                        <div className={styles.detailSection}>
                                            <div className={styles.detailLabel}>Endpoints</div>
                                            <div className={styles.endpoints}>
                                                {agentCardDetails.endpoints.chat && (
                                                    <div className={styles.endpoint}>
                                                        <span className={styles.endpointType}>Chat:</span>
                                                        <span className={styles.endpointUrl}>{agentCardDetails.endpoints.chat}</span>
                                                    </div>
                                                )}
                                                {agentCardDetails.endpoints.health && (
                                                    <div className={styles.endpoint}>
                                                        <span className={styles.endpointType}>Health:</span>
                                                        <span className={styles.endpointUrl}>{agentCardDetails.endpoints.health}</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {agentCardDetails.metadata && Object.keys(agentCardDetails.metadata).length > 0 && (
                                        <div className={styles.detailSection}>
                                            <div className={styles.detailLabel}>Metadata</div>
                                            <div className={styles.metadata}>
                                                {Object.entries(agentCardDetails.metadata).map(([key, value]) => (
                                                    <div key={key} className={styles.metadataItem}>
                                                        <span className={styles.metadataKey}>{key}:</span>
                                                        <span className={styles.metadataValue}>{JSON.stringify(value)}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </>
                            ) : (
                                <div className={styles.error}>Failed to load agent details</div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Add Agent Modal */}
            {showAddAgentModal && (
                <div className={styles.modalOverlay} onClick={() => setShowAddAgentModal(false)}>
                    <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
                        <div className={styles.modalHeader}>
                            <h3>Add New Agent</h3>
                            <button className={styles.modalCloseButton} onClick={() => setShowAddAgentModal(false)}>
                                <X size={20} />
                            </button>
                        </div>
                        <div className={styles.modalBody}>
                            <label htmlFor="agentUrl" className={styles.inputLabel}>
                                Agent URL
                            </label>
                            <input
                                id="agentUrl"
                                type="text"
                                className={styles.input}
                                placeholder="http://localhost:9999"
                                value={newAgentUrl}
                                onChange={(e) => setNewAgentUrl(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleAddAgent()}
                                disabled={isAddingAgent}
                            />
                            <p className={styles.inputHint}>
                                Enter the base URL of the agent (e.g., http://localhost:9999)
                            </p>
                            
                            {addAgentError && (
                                <div className={styles.errorMessage}>
                                    {addAgentError}
                                </div>
                            )}
                            
                            {addAgentSuccess && (
                                <div className={styles.successMessage}>
                                    {addAgentSuccess}
                                </div>
                            )}
                        </div>
                        <div className={styles.modalFooter}>
                            <button 
                                className={styles.cancelButton} 
                                onClick={() => setShowAddAgentModal(false)}
                                disabled={isAddingAgent}
                            >
                                Cancel
                            </button>
                            <button 
                                className={styles.addButton} 
                                onClick={handleAddAgent}
                                disabled={isAddingAgent}
                            >
                                {isAddingAgent ? 'Adding...' : 'Add Agent'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
});

AgentSystemMapVertical.displayName = 'AgentSystemMapVertical';
