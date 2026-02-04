import { Stack } from "@fluentui/react";
import { animated, useSpring } from "@react-spring/web";
import { useEffect, useState } from "react";

import styles from "./Answer.module.css";
import { AnswerIcon } from "./AnswerIcon";

interface ThinkingStep {
    step: string;
    message: string;
    status: string;
    duration?: number;
}

interface AnswerLoadingProps {
    currentThinkingSteps?: ThinkingStep[];
}

export const AnswerLoading = ({ currentThinkingSteps = [] }: AnswerLoadingProps) => {
    const [displayMessage, setDisplayMessage] = useState("Thinking about your question");
    const [elapsedTime, setElapsedTime] = useState(0);

    const animatedStyles = useSpring({
        from: { opacity: 0 },
        to: { opacity: 1 }
    });

    // Update display message based on current thinking step
    useEffect(() => {
        if (currentThinkingSteps.length > 0) {
            const latestStep = currentThinkingSteps[currentThinkingSteps.length - 1];
            const message = getContextualMessage(latestStep);
            setDisplayMessage(message);
        }
    }, [currentThinkingSteps]);

    // Track elapsed time
    useEffect(() => {
        const timer = setInterval(() => {
            setElapsedTime(prev => prev + 0.1);
        }, 100);
        return () => clearInterval(timer);
    }, []);

    const getContextualMessage = (step: ThinkingStep): string => {
        const stepLower = step.step.toLowerCase();
        const messageLower = step.message.toLowerCase();

        // Supervisor routing phase
        if (stepLower.includes("analyzing")) {
            return "🤔 Understanding your question";
        }
        
        // Cache checking
        if (stepLower.includes("cache") || messageLower.includes("cache")) {
            return "⚡ Checking your account data";
        }

        // Agent routing - show context-aware message
        if (stepLower.includes("routing")) {
            // Payment Agent - extract recipient name if available
            if (messageLower.includes("payment")) {
                // Try to extract recipient name from context
                const recipientMatch = step.message.match(/to\s+([A-Z][a-z]+)/i);
                if (recipientMatch) {
                    return `💸 Preparing transfer to ${recipientMatch[1]}...`;
                }
                return "💸 Preparing payment transfer...";
            }
            if (messageLower.includes("account")) {
                return "📊 Loading account details...";
            }
            if (messageLower.includes("transaction")) {
                return "💳 Fetching transaction history...";
            }
            if (messageLower.includes("money coach")) {
                return "💡 Consulting AI Money Coach...";
            }
            if (messageLower.includes("product") || messageLower.includes("prodinfo")) {
                return "🏦 Looking up product information...";
            }
            return "🎯 Routing to specialist...";
        }

        // MCP Tools invoked
        if (stepLower.includes("mcp")) {
            if (messageLower.includes("payment")) {
                return "🔍 Validating payment details...";
            }
            if (messageLower.includes("account")) {
                return "🔍 Retrieving account data...";
            }
            if (messageLower.includes("transaction")) {
                return "🔍 Loading transaction records...";
            }
            return "🔍 Accessing banking services...";
        }

        // Response generation
        if (stepLower.includes("generating")) {
            return "✅ Payment ready for confirmation";
        }

        // Default fallback
        return "🤖 Processing your request";
    };

    return (
        <animated.div style={{ ...animatedStyles }}>
            <Stack className={styles.answerContainer} verticalAlign="space-between">
                <AnswerIcon />
                <Stack.Item grow>
                    <p className={styles.answerText}>
                        {displayMessage}
                        <span className={styles.loadingdots} />
                    </p>
                    <p style={{ fontSize: "11px", color: "#888", marginTop: "4px" }}>
                        {elapsedTime.toFixed(1)}s
                    </p>
                </Stack.Item>
            </Stack>
        </animated.div>
    );
};
