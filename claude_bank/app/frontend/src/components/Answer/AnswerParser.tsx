import { renderToStaticMarkup } from "react-dom/server";
import { getCitationFilePath } from "../../api";

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: string[];
    followupQuestions: string[];
};

function parseMarkdownTable(tableText: string): string {
    const lines = tableText.trim().split('\n');
    if (lines.length < 3) return tableText; // Need at least header, separator, and one row
    
    // Parse header
    const headerCells = lines[0].split('|').map(cell => cell.trim()).filter(cell => cell);
    
    // Skip separator line (index 1)
    
    // Parse body rows
    const bodyRows = lines.slice(2).map(line => {
        return line.split('|').map(cell => cell.trim()).filter(cell => cell);
    });
    
    // Build HTML table
    let html = '<table>';
    
    // Header
    html += '<thead><tr>';
    headerCells.forEach(cell => {
        html += `<th>${cell}</th>`;
    });
    html += '</tr></thead>';
    
    // Body
    html += '<tbody>';
    bodyRows.forEach(row => {
        if (row.length > 0) {
            html += '<tr>';
            row.forEach(cell => {
                html += `<td>${cell}</td>`;
            });
            html += '</tr>';
        }
    });
    html += '</tbody></table>';
    
    return html;
}

export function parseAnswerToHtml(answer: string, isStreaming: boolean, onCitationClicked: (citationFilePath: string) => void): HtmlParsedAnswer {
    console.log('📝 [ANSWER PARSER DEBUG] Raw answer received:', {
        length: answer.length,
        preview: answer.substring(0, 200),
        isStreaming: isStreaming
    });
    
    const citations: string[] = [];
    const followupQuestions: string[] = [];

    // Extract any follow-up questions that might be in the answer
    let parsedAnswer = answer.replace(/<<([^>>]+)>>/g, (match, content) => {
        followupQuestions.push(content);
        return "";
    });

    // trim any whitespace from the end of the answer after removing follow-up questions
    parsedAnswer = parsedAnswer.trim();
    
    // Convert Markdown tables to HTML tables BEFORE processing other markdown
    // Match markdown table pattern: lines with pipes (|)
    // Updated regex to match tables even without leading newline
    const tableRegex = /(\n|^)(\|[^\n]+\|\n){2,}/g;
    parsedAnswer = parsedAnswer.replace(tableRegex, (match) => {
        // Preserve leading newline if it exists
        const hasLeadingNewline = match.startsWith('\n');
        const tableContent = hasLeadingNewline ? match.substring(1) : match;
        return (hasLeadingNewline ? '\n' : '') + parseMarkdownTable(tableContent) + '\n';
    });

    // Omit a citation that is still being typed during streaming
    if (isStreaming) {
        let lastIndex = parsedAnswer.length;
        for (let i = parsedAnswer.length - 1; i >= 0; i--) {
            if (parsedAnswer[i] === "]") {
                break;
            } else if (parsedAnswer[i] === "[") {
                lastIndex = i;
                break;
            }
        }
        const truncatedAnswer = parsedAnswer.substring(0, lastIndex);
        parsedAnswer = truncatedAnswer;
    }

    const parts = parsedAnswer.split(/\[([^\]]+)\]/g);

    const fragments: string[] = parts.map((part, index) => {
        if (index % 2 === 0) {
            // Debug: log original part
            console.log('📝 [ANSWER PARSER] Original part:', part.substring(0, 200));
            
            // Convert markdown to HTML
            let formattedPart = part
                // First, convert bold: **text** -> <strong>text</strong>
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                // Then, convert italic: *text* -> <em>text</em>
                .replace(/\*(.+?)\*/g, '<em>$1</em>')
                // Convert lines starting with "- " to new line with bullet
                .replace(/\n- /g, '<br/><br/>• ')
                // Handle first line if it starts with "-"
                .replace(/^- /g, '• ')
                // Convert remaining newlines to <br/>
                .replace(/\n/g, '<br/>');
            
            // Debug: log formatted part
            console.log('📝 [ANSWER PARSER] Formatted part:', formattedPart.substring(0, 200));
            
            return formattedPart;
        } else {
            let citationIndex: number;
            if (citations.indexOf(part) !== -1) {
                citationIndex = citations.indexOf(part) + 1;
            } else {
                citations.push(part);
                citationIndex = citations.length;
            }

            const path = getCitationFilePath(part);

            return renderToStaticMarkup(
                <a className="supContainer" title={part} onClick={() => onCitationClicked(path)}>
                    <sup>{citationIndex}</sup>
                </a>
            );
        }
    });

    const finalHtml = fragments.join("");
    console.log('📝 [ANSWER PARSER DEBUG] Final HTML output:', {
        htmlLength: finalHtml.length,
        htmlPreview: finalHtml.substring(0, 300),
        hasTables: finalHtml.includes('<table>'),
        citationsCount: citations.length
    });
    
    return {
        answerHtml: finalHtml,
        citations,
        followupQuestions
    };
}
