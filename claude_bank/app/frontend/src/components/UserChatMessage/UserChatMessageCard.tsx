import { User } from "lucide-react";
import { Card, CardContent } from "../ui/card";

interface UserChatMessageCardProps {
    message: string;
    timestamp?: Date;
    userName?: string;
}

export const UserChatMessageCard = ({ message, timestamp, userName }: UserChatMessageCardProps) => {
    return (
        <Card className="bg-primary/5 border-primary/20 shadow-sm">
            <CardContent className="pt-6">
                {/* User Icon & Timestamp */}
                <div className="flex items-center gap-2 mb-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 border border-primary/20">
                        <User className="h-4 w-4 text-primary" />
                    </div>
                    <span className="text-xs font-medium text-foreground">{userName || 'You'}</span>
                    {timestamp && (
                        <>
                            <span className="text-xs text-muted-foreground">•</span>
                            <span className="text-xs text-muted-foreground">
                                {timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </>
                    )}
                </div>

                {/* Message Content */}
                <div className="text-base leading-relaxed whitespace-pre-wrap">
                    {message}
                </div>
            </CardContent>
        </Card>
    );
};
