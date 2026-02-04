import { useState, useEffect } from 'react';

export interface AgentStatus {
    id: string;
    name: string;
    status: 'running' | 'stopped' | 'unknown';
    lastChecked: Date;
}

export const useAgentStatus = (agentIds: string[]) => {
    const [statuses, setStatuses] = useState<Map<string, AgentStatus>>(new Map());
    const [isChecking, setIsChecking] = useState(false);

    // Agent URLs for health checks
    const AGENT_URLS: Record<string, string> = {
        supervisor: 'http://localhost:9000',
        payment: 'http://localhost:9002',
        account: 'http://localhost:9001',
        transaction: 'http://localhost:9003',
        prodinfo: 'http://localhost:9004',
        coach: 'http://localhost:9005',
        escalation: 'http://localhost:9006',
    };

    const checkAgentStatus = async (agentId: string): Promise<'running' | 'stopped' | 'unknown'> => {
        try {
            const agentUrl = AGENT_URLS[agentId];
            if (!agentUrl) {
                console.warn(`No URL configured for agent: ${agentId}`);
                return 'unknown';
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

            const response = await fetch(`${agentUrl}/health`, {
                method: 'GET',
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            clearTimeout(timeoutId);

            if (response.ok) {
                const data = await response.json();
                // Check if response indicates healthy status
                if (data.status === 'healthy' || data.status === 'running') {
                    return 'running';
                }
                return 'stopped';
            }
            return 'stopped';
        } catch (error: any) {
            if (error.name === 'AbortError') {
                console.warn(`Health check timeout for ${agentId}`);
            } else {
                console.error(`Failed to check status for ${agentId}:`, error);
            }
            return 'unknown';
        }
    };

    const checkAllStatuses = async () => {
        setIsChecking(true);
        const newStatuses = new Map<string, AgentStatus>();

        for (const agentId of agentIds) {
            const status = await checkAgentStatus(agentId);
            newStatuses.set(agentId, {
                id: agentId,
                name: agentId,
                status,
                lastChecked: new Date()
            });
        }

        setStatuses(newStatuses);
        setIsChecking(false);
    };

    useEffect(() => {
        // Initial check
        checkAllStatuses();

        // Poll every 2 minutes
        const interval = setInterval(checkAllStatuses, 120000);

        return () => clearInterval(interval);
    }, [agentIds.join(',')]);

    return {
        statuses,
        isChecking,
        refresh: checkAllStatuses
    };
};
