import React, { useState, useEffect } from 'react';
import { Brain, Check, Loader2, X } from 'lucide-react';
import styles from './ThinkingPanel.module.css';

export interface ThinkingStep {
    id: string;
    step: string;
    message: string;
    status: 'in_progress' | 'completed' | 'failed';
    timestamp: number;
    duration?: number;
}

interface ThinkingPanelProps {
    isOpen: boolean;
    onClose: () => void;
    currentSteps: ThinkingStep[];
    messageId?: string; // For showing historical thinking logs
}

const STEP_LABELS: Record<string, { icon: string; label: string }> = {
    'authenticating': { icon: '🔐', label: 'Authenticating user' },
    'checking_cache': { icon: '🔄', label: 'Checking cache' },
    'analyzing': { icon: '🧠', label: 'Supervisor Agent analyzing request' },
    'routing': { icon: '🎯', label: 'Determining specialist agent' },
    'agent_selected': { icon: '🤖', label: 'Agent selected' },
    'gathering_data': { icon: '�', label: 'MCP Tool Calling' },
    'processing': { icon: '⚙️', label: 'Processing' },
    'generating': { icon: '✅', label: 'Generating response' },
    'complete': { icon: '✨', label: 'Complete' }
};

export const ThinkingPanel: React.FC<ThinkingPanelProps> = ({
    isOpen,
    onClose,
    currentSteps,
    messageId
}) => {
    const [totalDuration, setTotalDuration] = useState<number>(0);

    useEffect(() => {
        console.log(`🧠 [THINKING PANEL] Panel state changed - isOpen: ${isOpen}, steps count: ${currentSteps.length}`);
        if (currentSteps.length > 0) {
            console.log('🧠 [THINKING PANEL] Current steps:', currentSteps);
            const total = currentSteps.reduce((sum, step) => sum + (step.duration || 0), 0);
            setTotalDuration(total);
            console.log(`🧠 [THINKING PANEL] Total duration: ${total.toFixed(2)}s`);
        }
    }, [currentSteps, isOpen]);

    const getStepIcon = (step: ThinkingStep) => {
        const stepInfo = STEP_LABELS[step.step] || { icon: '💭', label: step.message };
        
        if (step.status === 'completed') {
            return <Check size={20} className={styles.iconCompleted} />;
        } else if (step.status === 'in_progress') {
            return <Loader2 size={20} className={styles.iconInProgress} />;
        } else if (step.status === 'failed') {
            return <X size={20} className={styles.iconFailed} />;
        }
        return null;
    };

    const getStepLabel = (step: ThinkingStep) => {
        const stepInfo = STEP_LABELS[step.step];
        // For agent_selected step, always show the custom message (e.g., "🎯 AccountAgent selected")
        if (step.step === 'agent_selected' && step.message) {
            console.log('🤖 [THINKING PANEL DEBUG] Agent selected step received:', {
                step: step.step,
                message: step.message,
                status: step.status,
                stepInfo: stepInfo
            });
            return step.message; // Already includes emoji from backend
        }
        // For other steps, use standard label
        return stepInfo ? `${stepInfo.icon} ${stepInfo.label}` : `💭 ${step.message}`;
    };

    const formatDuration = (seconds: number) => {
        if (seconds < 1) {
            return `${(seconds * 1000).toFixed(0)}ms`;
        }
        return `${seconds.toFixed(1)}s`;
    };

    if (!isOpen) return null;

    return (
        <div className={styles.panel}>
            <div className={styles.header}>
                <div className={styles.headerLeft}>
                    <Brain size={20} className={styles.brainIcon} />
                    <h3 className={styles.title}>AI Thinking Process</h3>
                </div>
                <button 
                    onClick={onClose} 
                    className={styles.closeButton}
                    aria-label="Close thinking panel"
                >
                    <X size={20} />
                </button>
            </div>

            <div className={styles.content}>
                {currentSteps.length === 0 ? (
                    <div className={styles.emptyState}>
                        <Brain size={48} className={styles.emptyIcon} />
                        <p className={styles.emptyText}>No thinking process to display</p>
                        <span className={styles.emptySubtext}>
                            Ask a question to see how the AI thinks
                        </span>
                    </div>
                ) : (
                    <>
                        <div className={styles.stepsList}>
                            {currentSteps.map((step, index) => (
                                <div 
                                    key={step.id} 
                                    className={`${styles.stepItem} ${
                                        step.status === 'completed' ? styles.stepCompleted :
                                        step.status === 'in_progress' ? styles.stepInProgress :
                                        step.status === 'failed' ? styles.stepFailed : ''
                                    }`}
                                >
                                    <div className={styles.stepIconContainer}>
                                        {getStepIcon(step)}
                                        {index < currentSteps.length - 1 && (
                                            <div className={styles.stepConnector} />
                                        )}
                                    </div>
                                    <div className={styles.stepContent}>
                                        <div className={styles.stepHeader}>
                                            <span className={styles.stepLabel}>
                                                {getStepLabel(step)}
                                            </span>
                                        </div>
                                        {step.message && step.message !== getStepLabel(step) && (
                                            <p className={styles.stepMessage}>
                                                {step.message}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};
