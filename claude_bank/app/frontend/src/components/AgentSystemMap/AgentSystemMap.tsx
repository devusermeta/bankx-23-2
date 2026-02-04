import React, { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { Activity, Workflow } from 'lucide-react';
import styles from './AgentSystemMap.module.css';

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

interface AgentSystemMapProps {
    latestEvent: AgentEvent | null;
    activeAgent: string | null;
    isStreaming: boolean;
    isThinkingPanelVisible: boolean;
}

export interface AgentSystemMapRef {
    clearAndShowSupervisor: () => void;
}

type NodeId = 'supervisor' | 'payment' | 'account' | 'transaction' | 'prodinfo' | 'coach' | 'escalation' | 'mcp_tools';

interface NodeInfo {
    id: NodeId;
    label: string;
    icon: string;
    type: 'coordinator' | 'agent' | 'tool';
}

interface EdgeInfo {
    from: NodeId;
    to: NodeId;
}

const NODES: NodeInfo[] = [
    { id: 'supervisor', label: 'Supervisor', icon: '🎯', type: 'coordinator' },
    { id: 'payment', label: 'Payment Agent', icon: '💸', type: 'agent' },
    { id: 'account', label: 'Account Agent', icon: '🏦', type: 'agent' },
    { id: 'transaction', label: 'Transaction Agent', icon: '📊', type: 'agent' },
    { id: 'prodinfo', label: 'Product Info Agent', icon: '📚', type: 'agent' },
    { id: 'coach', label: 'AI Money Coach', icon: '🤖', type: 'agent' },
    { id: 'escalation', label: 'Escalation Agent', icon: '🎫', type: 'agent' },
    { id: 'mcp_tools', label: 'MCP Tools', icon: '🛠️', type: 'tool' }
];

const EDGES: EdgeInfo[] = [
    { from: 'supervisor', to: 'payment' },
    { from: 'supervisor', to: 'account' },
    { from: 'supervisor', to: 'transaction' },
    { from: 'supervisor', to: 'prodinfo' },
    { from: 'supervisor', to: 'coach' },
    { from: 'supervisor', to: 'escalation' },
    { from: 'payment', to: 'mcp_tools' },
    { from: 'account', to: 'mcp_tools' },
    { from: 'transaction', to: 'mcp_tools' },
    { from: 'escalation', to: 'mcp_tools' },
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
    'productinfo': 'prodinfo',  // "Product Info" normalized
    'prodinfoagent': 'prodinfo',
    'prodinfofaqagent': 'prodinfo',
    'coach': 'coach',
    'aimoneycoach': 'coach',
    'aimoneycoachagent': 'coach',
    'escalation': 'escalation',
    'escalationagent': 'escalation',
};

const ACTIVE_TTL = 3000; // 3 seconds glow duration

export const AgentSystemMap = forwardRef<AgentSystemMapRef, AgentSystemMapProps>(({
    latestEvent,
    activeAgent,
    isStreaming,
    isThinkingPanelVisible
}, ref) => {
    const [activeNodes, setActiveNodes] = useState<Set<NodeId>>(new Set());
    const [activeEdges, setActiveEdges] = useState<Set<string>>(new Set());
    const [timeline, setTimeline] = useState<AgentEvent[]>([]);
    const [cachedNodes, setCachedNodes] = useState<Set<NodeId>>(new Set());
    const [lastAgentEvent, setLastAgentEvent] = useState<{agent: NodeId, cached: boolean} | null>(null);
    const [isThinking, setIsThinking] = useState<boolean>(false); // Track supervisor thinking phase

    // Expose method to parent via ref
    useImperativeHandle(ref, () => ({
        clearAndShowSupervisor: () => {
            console.log('🗺️ [MAP] clearAndShowSupervisor called via ref');
            setActiveNodes(new Set(['supervisor']));
            setActiveEdges(new Set());
            setCachedNodes(new Set());
            setIsThinking(true); // Show supervisor as thinking (blue pulse)
        }
    }));

    // Convert agent name to node ID
    const getNodeIdFromAgent = (agentName?: string): NodeId | null => {
        if (!agentName) return null;
        const normalized = agentName.toLowerCase().replace(/[_\s-]/g, '');
        const nodeId = AGENT_NODE_MAP[normalized] || null;
        console.log(`🗺️ [MAP] getNodeIdFromAgent: "${agentName}" → normalized: "${normalized}" → nodeId: ${nodeId}`);
        return nodeId;
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

        // Add to timeline (keep last 10 events)
        setTimeline(prev => [...prev, latestEvent].slice(-10));

        // Activate nodes and edges based on event type
        const newActiveNodes = new Set<NodeId>();
        const newActiveEdges = new Set<string>();

        switch (latestEvent.type) {
            case 'agent_routing':
            case 'agent_handoff':
                const fromNode = getNodeIdFromAgent(latestEvent.from_agent || 'supervisor');
                const toNode = getNodeIdFromAgent(latestEvent.to_agent);
                
                // Stop thinking animation when routing completes
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
                
                // Clear previous highlights for new question (only on initial analyzing step)
                if (latestEvent.step === 'analyzing') {
                    console.log('🧹 [MAP] Clearing previous highlights for new question');
                    setActiveNodes(new Set(['supervisor'])); // Show supervisor immediately
                    setActiveEdges(new Set());
                    setCachedNodes(new Set());
                    setIsThinking(true); // Enable thinking animation
                    // Don't process further for analyzing step
                    break;
                }
                
                // Handle routing step - agent selection complete
                if (latestEvent.step === 'routing') {
                    console.log('🎯 [MAP] Routing step detected - stopping thinking animation');
                    setIsThinking(false); // Stop blue pulse
                    
                    // Try to extract agent from message like "Product Info Agent selected"
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
                    // Continue processing in case there's more info
                }
                
                // Check if agent is in the event
                if (latestEvent.agent) {
                    const selectedAgent = getNodeIdFromAgent(latestEvent.agent);
                    console.log(`🗺️ [MAP] Agent from event: ${latestEvent.agent}, Mapped to: ${selectedAgent}`);
                    
                    if (selectedAgent) {
                        // Transition from thinking to active agent
                        setIsThinking(false);
                        newActiveNodes.add('supervisor');
                        newActiveNodes.add(selectedAgent);
                        newActiveEdges.add(`supervisor-${selectedAgent}`);
                        
                        // Track if it's cached
                        if (latestEvent.cached) {
                            setCachedNodes(new Set([selectedAgent]));
                            console.log(`💾 [MAP] Cache hit for ${selectedAgent}`);
                        } else {
                            setCachedNodes(new Set());
                        }
                        
                        // Store for restoration when panel reopens
                        setLastAgentEvent({ agent: selectedAgent, cached: latestEvent.cached || false });
                        
                        console.log(`✅ [MAP] Activated nodes:`, Array.from(newActiveNodes), 'edges:', Array.from(newActiveEdges));
                    } else {
                        console.warn(`❌ [MAP] Could not map agent: ${latestEvent.agent}`);
                    }
                } else if (latestEvent.step === 'agent_selected' && latestEvent.message) {
                    // Fallback: try to extract from message
                    console.log(`🔍 [MAP] Trying to extract agent from message: "${latestEvent.message}"`);
                    const selectedAgent = getNodeIdFromAgent(latestEvent.message);
                    if (selectedAgent) {
                        newActiveNodes.add('supervisor');
                        newActiveNodes.add(selectedAgent);
                        newActiveEdges.add(`supervisor-${selectedAgent}`);
                        
                        // Check if cached in message
                        const isCached = latestEvent.message.toLowerCase().includes('cached');
                        if (isCached) {
                            setCachedNodes(new Set([selectedAgent]));
                            console.log(`💾 [MAP] Cache hit detected in message for ${selectedAgent}`);
                        }
                        console.log(`✅ [MAP] Activated from message:`, Array.from(newActiveNodes), 'edges:', Array.from(newActiveEdges));
                    } else {
                        console.warn(`❌ [MAP] Could not extract agent from message: "${latestEvent.message}"`);
                    }
                }
                break;
        }

        // Update active states (persist until new question)
        if (newActiveNodes.size > 0 || newActiveEdges.size > 0) {
            setActiveNodes(newActiveNodes);
            setActiveEdges(newActiveEdges);
        }
    }, [latestEvent]);

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
            // Panel closed - clear all highlights
            console.log('🗺️ [MAP] 🧹 Thinking panel closed - clearing highlights');
            setActiveNodes(new Set());
            setActiveEdges(new Set());
            setCachedNodes(new Set());
        } else if (isThinkingPanelVisible && lastAgentEvent) {
            // Panel reopened - restore last agent highlighting
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

    const formatEventDescription = (event: AgentEvent): string => {
        switch (event.type) {
            case 'agent_routing':
                return `Routed to ${event.to_agent || 'specialist'}`;
            case 'agent_handoff':
                return `${event.from_agent || 'Coordinator'} → ${event.to_agent || 'Agent'}`;
            case 'mcp_tool_call':
                return `Called ${event.tool_name || 'MCP tool'}`;
            case 'thinking':
                return event.message || event.step || 'Processing';
            default:
                return event.message || 'Activity';
        }
    };

    return (
        <div className={styles.container}>
            {/* Graph Visualization */}
            <div className={styles.graphSection}>
                <div className={styles.sectionHeader}>
                    <Workflow size={18} />
                    <h3>Agent System Map</h3>
                </div>

                <div className={styles.graph}>
                    {/* Coordinator Node (Top Center) */}
                    <div className={`${styles.node} ${styles.coordinator} ${isNodeThinking('supervisor') ? styles.thinking : (isNodeActive('supervisor') ? styles.active : '')}`}>
                        <span className={styles.nodeIcon}>{NODES.find(n => n.id === 'supervisor')?.icon}</span>
                        <span className={styles.nodeLabel}>Supervisor</span>
                    </div>

                    {/* Agent Nodes (Middle Row) */}
                    <div className={styles.agentsRow}>
                        {NODES.filter(n => n.type === 'agent').map(node => (
                            <div 
                                key={node.id}
                                data-agent={node.id}
                                className={`${styles.node} ${styles.agent} ${isNodeActive(node.id) ? styles.active : ''}`}
                            >
                                <span className={styles.nodeIcon}>{node.icon}</span>
                                <span className={styles.nodeLabel}>{node.label}</span>
                                {cachedNodes.has(node.id) && (
                                    <span className={styles.cacheBadge}>💾 CACHE</span>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Tool Node (Bottom Center) */}
                    <div className={`${styles.node} ${styles.tool} ${isNodeActive('mcp_tools') ? styles.active : ''}`}>
                        <span className={styles.nodeIcon}>{NODES.find(n => n.id === 'mcp_tools')?.icon}</span>
                        <span className={styles.nodeLabel}>MCP Tools</span>
                    </div>

                    {/* Edges SVG Overlay */}
                    <svg className={styles.edgesSvg}>
                        {/* Supervisor to Agents */}
                        {NODES.filter(n => n.type === 'agent').map((node, idx) => (
                            <line
                                key={`edge-supervisor-${node.id}`}
                                x1="50%"
                                y1="15%"
                                x2={`${20 + (idx * 15)}%`}
                                y2="45%"
                                className={`${styles.edge} ${isEdgeActive('supervisor', node.id) ? styles.edgeActive : ''}`}
                            />
                        ))}
                        {/* Agents to Tools */}
                        <line
                            x1="35%"
                            y1="55%"
                            x2="50%"
                            y2="85%"
                            className={`${styles.edge} ${isEdgeActive('payment', 'mcp_tools') ? styles.edgeActive : ''}`}
                        />
                        <line
                            x1="50%"
                            y1="55%"
                            x2="50%"
                            y2="85%"
                            className={`${styles.edge} ${isEdgeActive('account', 'mcp_tools') ? styles.edgeActive : ''}`}
                        />
                        <line
                            x1="65%"
                            y1="55%"
                            x2="50%"
                            y2="85%"
                            className={`${styles.edge} ${isEdgeActive('transaction', 'mcp_tools') ? styles.edgeActive : ''}`}
                        />
                    </svg>
                </div>
            </div>

            {/* Event Timeline */}
            {/* <div className={styles.timelineSection}>
                <div className={styles.sectionHeader}>
                    <Activity size={18} />
                    <h3>Live Event Trace</h3>
                    {timeline.length > 0 && (
                        <span className={styles.eventCount}>{timeline.length} cached</span>
                    )}
                </div>

                <div className={styles.timeline}>
                    {timeline.length === 0 ? (
                        <div className={styles.emptyTimeline}>
                            <Activity size={32} className={styles.emptyIcon} />
                            <p>No events yet</p>
                        </div>
                    ) : (
                        timeline.slice().reverse().map((event, idx) => (
                            <div key={`${event.timestamp}-${idx}`} className={styles.timelineEvent}>
                                <span className={styles.eventType}>{event.type.toUpperCase().replace('_', ' ')}</span>
                                <span className={styles.eventDescription}>{formatEventDescription(event)}</span>
                                <span className={styles.eventTime}>
                                    {new Date(event.timestamp).toLocaleTimeString('en-US', { 
                                        hour: '2-digit', 
                                        minute: '2-digit',
                                        second: '2-digit'
                                    })}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div> */}
        </div>
    );
});

AgentSystemMap.displayName = 'AgentSystemMap';
