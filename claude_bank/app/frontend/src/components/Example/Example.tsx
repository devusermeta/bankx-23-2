import { Card } from "@/components/ui/card";
import { ArrowRight } from "lucide-react";

interface Props {
    text: string;
    value: string;
    onClick: (value: string) => void;
}

export const Example = ({ text, value, onClick }: Props) => {
    return (
        <Card 
            className="p-4 cursor-pointer transition-all duration-200 hover:scale-105 hover:shadow-lg hover:border-primary/50 group"
            onClick={() => onClick(value)}
        >
            <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium group-hover:text-primary transition-colors">
                    {text}
                </p>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
            </div>
        </Card>
    );
};
