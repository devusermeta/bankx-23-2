import { Example } from "./Example";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    { text: "I want to know my account balance", value: "I want to know my account balance"},
    { text: "What are the minimum deposit for savings account?", value: "What are the minimum deposit for savings account?" },
    { text: "How to be financially secure?", value: "How to be financially secure?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <div className="w-full">
            <p className="text-sm text-muted-foreground mb-4 text-center font-medium">
                Try these examples to get started:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {EXAMPLES.map((x, i) => (
                    <Example key={i} text={x.text} value={x.value} onClick={onExampleClicked} />
                ))}
            </div>
        </div>
    );
};
