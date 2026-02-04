import React, { useEffect, useState } from 'react';
import { MessageSquare, Calendar, User, Clock, ChevronRight, Bot, UserCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';

interface Message {
    timestamp: string;
    role: 'user' | 'assistant';
    content: string;
    metadata?: Record<string, any>;
}

interface BankingOperation {
    timestamp: string;
    type: string;
    details: Record<string, any>;
}

interface ConversationMetadata {
    azure_thread_id: string;
    agent_types: string[];
    banking_operations: BankingOperation[];
}

interface SessionSummary {
    session_id: string;
    created_at: string;
    updated_at: string;
    message_count: number;
    agent_operations_count: number;
}

interface FullConversation {
    session_id: string;
    created_at: string;
    updated_at: string;
    messages: Message[];
    metadata: ConversationMetadata;
}

export const ConversationsPage = () => {
    const [sessions, setSessions] = useState<SessionSummary[]>([]);
    const [selectedSession, setSelectedSession] = useState<FullConversation | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;

    useEffect(() => {
        console.log('🚀 [CONVERSATIONS] ConversationsPage mounted, initializing...');
        fetchSessions();
    }, []);

    const fetchSessions = async () => {
        console.log('🔄 [CONVERSATIONS] Fetching conversation sessions...');
        try {
            setLoading(true);
            const response = await fetch('/api/conversations/');
            console.log('📡 [CONVERSATIONS] API response status:', response.status);
            
            if (!response.ok) {
                console.error('❌ [CONVERSATIONS] Failed to fetch conversations:', response.status, response.statusText);
                throw new Error('Failed to fetch conversations');
            }
            
            const data = await response.json();
            console.log('✅ [CONVERSATIONS] Received sessions:', data.length, 'sessions');
            console.log('📊 [CONVERSATIONS] Session data:', data);
            setSessions(data);
        } catch (err) {
            console.error('❌ [CONVERSATIONS] Error fetching sessions:', err);
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
            console.log('🏁 [CONVERSATIONS] Fetch sessions complete');
        }
    };

    const fetchFullConversation = async (sessionId: string) => {
        console.log('🔍 [CONVERSATIONS] Fetching full conversation for session:', sessionId);
        try {
            const response = await fetch(`/api/conversations/${sessionId}`);
            console.log('📡 [CONVERSATIONS] Detail API response status:', response.status);
            
            if (!response.ok) {
                console.error('❌ [CONVERSATIONS] Failed to fetch conversation details:', response.status);
                throw new Error('Failed to fetch conversation details');
            }
            
            const data = await response.json();
            console.log('✅ [CONVERSATIONS] Received full conversation:', data);
            console.log('💬 [CONVERSATIONS] Message count:', data.messages?.length || 0);
            console.log('🔧 [CONVERSATIONS] Banking operations:', data.metadata?.banking_operations?.length || 0);
            setSelectedSession(data);
        } catch (err) {
            console.error('❌ [CONVERSATIONS] Error fetching conversation details:', err);
            setError(err instanceof Error ? err.message : 'Unknown error');
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleString();
    };

    // Pagination calculations
    const totalPages = Math.ceil(sessions.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentSessions = sessions.slice(startIndex, endIndex);

    const goToPage = (page: number) => {
        setCurrentPage(page);
        setSelectedSession(null); // Clear selection when changing pages
    };

    const nextPage = () => {
        if (currentPage < totalPages) {
            goToPage(currentPage + 1);
        }
    };

    const prevPage = () => {
        if (currentPage > 1) {
            goToPage(currentPage - 1);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-muted-foreground">Loading conversations...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-destructive">Error: {error}</div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Conversations</h1>
                    <p className="text-muted-foreground">View and analyze customer chat sessions</p>
                </div>
                <Button onClick={fetchSessions} variant="outline">
                    Refresh
                </Button>
            </div>

            <div className="grid gap-6 lg:grid-cols-3">
                {/* Sessions List */}
                <div className="lg:col-span-1">
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">
                                Chat Sessions ({sessions.length})
                                {totalPages > 1 && (
                                    <span className="text-sm font-normal text-muted-foreground ml-2">
                                        Page {currentPage} of {totalPages}
                                    </span>
                                )}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            {sessions.length === 0 ? (
                                <div className="text-center text-muted-foreground py-8">
                                    No conversations yet
                                </div>
                            ) : (
                                currentSessions.map((session) => (
                                    <div
                                        key={session.session_id}
                                        onClick={() => fetchFullConversation(session.session_id)}
                                        className={`p-4 rounded-lg border cursor-pointer transition-colors hover:bg-accent ${
                                            selectedSession?.session_id === session.session_id ? 'bg-accent' : ''
                                        }`}
                                    >
                                        <div className="flex items-start justify-between">
                                            <div className="space-y-1 flex-1">
                                                <div className="flex items-center gap-2">
                                                    <MessageSquare className="h-4 w-4 text-primary" />
                                                    <span className="font-medium text-sm">
                                                        {session.message_count} messages
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <Bot className="h-3 w-3" />
                                                    {session.agent_operations_count} operations
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <Calendar className="h-3 w-3" />
                                                    {formatDate(session.updated_at)}
                                                </div>
                                            </div>
                                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                        </div>
                                    </div>
                                ))
                            )}

                            {/* Pagination Controls */}
                            {totalPages > 1 && (
                                <div className="flex items-center justify-between pt-4 border-t">
                                    <Button 
                                        onClick={prevPage} 
                                        disabled={currentPage === 1}
                                        variant="outline"
                                        size="sm"
                                    >
                                        Previous
                                    </Button>
                                    <div className="text-sm text-muted-foreground">
                                        {startIndex + 1}-{Math.min(endIndex, sessions.length)} of {sessions.length}
                                    </div>
                                    <Button 
                                        onClick={nextPage} 
                                        disabled={currentPage === totalPages}
                                        variant="outline"
                                        size="sm"
                                    >
                                        Next
                                    </Button>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Conversation Details */}
                <div className="lg:col-span-2">
                    {selectedSession ? (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">Conversation Details</CardTitle>
                                <div className="text-sm text-muted-foreground space-y-1">
                                    <div>Session ID: {selectedSession.session_id}</div>
                                    <div>Started: {formatDate(selectedSession.created_at)}</div>
                                    <div>Last Updated: {formatDate(selectedSession.updated_at)}</div>
                                    <div>{selectedSession.messages.length} messages, {selectedSession.metadata.banking_operations.length} operations</div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                {selectedSession.messages.map((msg, idx) => {
                                    // Find matching banking operation for this message
                                    const operation = selectedSession.metadata.banking_operations.find(
                                        op => Math.abs(new Date(op.timestamp).getTime() - new Date(msg.timestamp).getTime()) < 5000
                                    );
                                    const agentName = operation?.type.replace(/_/g, ' ').replace(/agent call/i, '').trim();

                                    return (
                                        <div key={idx} className="flex gap-3 pb-4 border-b last:border-0">
                                            {/* Icon */}
                                            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center" 
                                                 style={{
                                                     backgroundColor: msg.role === 'user' ? '#dbeafe' : '#f3e8ff',
                                                 }}>
                                                {msg.role === 'user' ? (
                                                    <UserCircle className="h-4 w-4 text-blue-600" />
                                                ) : (
                                                    <Bot className="h-4 w-4 text-purple-600" />
                                                )}
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <div className="text-sm font-medium">
                                                        {msg.role === 'user' ? 'User' : 'AI Assistant'}
                                                    </div>
                                                    {msg.role === 'assistant' && agentName && (
                                                        <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                                                            {agentName}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className={`text-sm p-3 rounded-lg whitespace-pre-wrap ${
                                                    msg.role === 'user' 
                                                        ? 'bg-blue-50 dark:bg-blue-950/30 text-foreground' 
                                                        : 'bg-purple-50 dark:bg-purple-950/30 text-foreground'
                                                }`}>
                                                    {msg.content}
                                                </div>
                                                <div className="text-xs text-muted-foreground">
                                                    {formatDate(msg.timestamp)}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </CardContent>
                        </Card>
                    ) : (
                        <Card>
                            <CardContent className="flex items-center justify-center h-96">
                                <div className="text-center space-y-2">
                                    <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto" />
                                    <p className="text-muted-foreground">Select a conversation to view details</p>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
};
