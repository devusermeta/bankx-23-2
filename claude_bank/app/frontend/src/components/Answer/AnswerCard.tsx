import { useState } from "react";
import { Copy, Check, ThumbsUp, ThumbsDown, Brain } from "lucide-react";
import { Button } from "../ui/button";
import { Card, CardContent } from "../ui/card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

interface AnswerCardProps {
    content: string;
    isStreaming?: boolean;
    timestamp?: Date;
    onFeedback?: (feedback: 'positive' | 'negative') => void;
    onThinkingClicked?: () => void;
    hasThinkingLog?: boolean;
    // Inline confirmation props
    showConfirmation?: boolean;
    onConfirm?: () => void;
    onCancel?: () => void;
    isConfirming?: boolean;
}

export const AnswerCard = ({ content, isStreaming, timestamp, onFeedback, onThinkingClicked, hasThinkingLog = false, showConfirmation = false, onConfirm, onCancel, isConfirming = false }: AnswerCardProps) => {
    const [copied, setCopied] = useState(false);
    const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);

    const copyToClipboard = async () => {
        try {
            await navigator.clipboard.writeText(content);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    const handleFeedback = (type: 'positive' | 'negative') => {
        setFeedback(type);
        onFeedback?.(type);
    };

    return (
        <Card className="shadow-sm hover:shadow-md transition-shadow duration-200">
            <CardContent className="pt-6">
                {/* AI Icon & Timestamp */}
                <div className="flex items-center gap-2 mb-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-purple-600">
                        <span className="text-white text-sm font-semibold">AI</span>
                    </div>
                    <span className="text-xs text-muted-foreground">BankX Assistant</span>
                    {timestamp && (
                        <>
                            <span className="text-xs text-muted-foreground">•</span>
                            <span className="text-xs text-muted-foreground">
                                {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </>
                    )}
                </div>

                {/* Answer Content */}
                <div className="prose prose-sm max-w-none dark:prose-invert prose-p:leading-relaxed prose-pre:bg-muted prose-pre:border prose-pre:border-border">
                    <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeRaw]}
                    >
                        {content}
                    </ReactMarkdown>
                </div>

                {/* Inline Confirmation Buttons */}
                {showConfirmation && !isStreaming && (
                    <div className="flex items-center gap-3 mt-6 pt-4 border-t border-border">
                        <Button
                            variant="ghost"
                            size="default"
                            onClick={onCancel}
                            disabled={isConfirming}
                            className="flex-1 text-sm font-semibold rounded-full bg-slate-200 text-slate-900 hover:bg-slate-300 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                            style={{ minWidth: '110px', padding: '0.5rem 1.35rem' }}
                        >
                            Cancel
                        </Button>
                        <Button
                            variant="default"
                            size="default"
                            onClick={onConfirm}
                            disabled={isConfirming}
                            className="flex-1 text-sm font-semibold rounded-full bg-blue-700 hover:bg-blue-800 hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                            style={{ minWidth: '110px', padding: '0.5rem 1.35rem' }}
                        >
                            {isConfirming ? 'Processing...' : 'Approve'}
                        </Button>
                    </div>
                )}

                {/* Actions Bar */}
                {!isStreaming && !showConfirmation && (
                    <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                        {onThinkingClicked && (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={onThinkingClicked}
                                className="text-xs"
                                style={{ color: hasThinkingLog ? '#667eea' : '#999' }}
                            >
                                <Brain className="h-3.5 w-3.5 mr-1.5" />
                                AI Thinking
                            </Button>
                        )}
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={copyToClipboard}
                            className="text-xs"
                        >
                            {copied ? (
                                <>
                                    <Check className="h-3.5 w-3.5 mr-1.5" />
                                    Copied
                                </>
                            ) : (
                                <>
                                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                                    Copy
                                </>
                            )}
                        </Button>
                        
                        <div className="flex items-center gap-1 ml-auto">
                            <Button
                                variant={feedback === 'positive' ? 'default' : 'ghost'}
                                size="sm"
                                onClick={() => handleFeedback('positive')}
                                className="text-xs"
                            >
                                <ThumbsUp className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                                variant={feedback === 'negative' ? 'default' : 'ghost'}
                                size="sm"
                                onClick={() => handleFeedback('negative')}
                                className="text-xs"
                            >
                                <ThumbsDown className="h-3.5 w-3.5" />
                            </Button>
                        </div>
                    </div>
                )}

                {/* Streaming indicator */}
                {isStreaming && (
                    <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
                        <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                            <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                        </div>
                        <span className="text-xs">Typing...</span>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
