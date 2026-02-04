/**
 * SSE (Server-Sent Events) Stream Parser
 * Parses text/event-stream responses with "data: " prefix and "\n\n" separators
 */

export type SSEEvent = {
  type: 'message' | 'error' | 'thinking';
  data: any;
};

export type SSECallback = (event: SSEEvent) => void;

/**
 * Read SSE stream from a Response object
 * @param response - The fetch Response with text/event-stream content
 * @param onEvent - Callback function called for each parsed SSE event
 * @param onError - Optional callback for error handling
 */
export async function readSSEStream(
  response: Response,
  onEvent: SSECallback,
  onError?: (error: Error) => void
): Promise<void> {
  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Split by SSE event separator (\n\n)
      const events = buffer.split('\n\n');
      
      // Keep the last incomplete event in the buffer
      buffer = events.pop() || '';

      // Process complete events
      for (const eventText of events) {
        if (!eventText.trim()) {
          continue;
        }

        // Parse SSE format: "data: {json}"
        const lines = eventText.split('\n');
        let data = '';
        let eventType = 'message';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            data = line.slice(6); // Remove "data: " prefix
          } else if (line.startsWith('event: ')) {
            eventType = line.slice(7); // Remove "event: " prefix
          }
        }

        if (!data) {
          continue;
        }

        try {
          const parsed = JSON.parse(data);
          
          // Determine event type
          let type: SSEEvent['type'] = 'message';
          if (parsed.type === 'thinking') {
            type = 'thinking';
          } else if (parsed.error || eventType === 'error') {
            type = 'error';
          }

          onEvent({
            type,
            data: parsed
          });
        } catch (error) {
          console.error('Failed to parse SSE event:', data, error);
          if (onError) {
            onError(new Error(`Failed to parse SSE event: ${error}`));
          }
        }
      }
    }
  } catch (error) {
    console.error('Error reading SSE stream:', error);
    if (onError) {
      onError(error as Error);
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}

/**
 * Alternative: Use EventSource API for SSE (for GET requests)
 * Note: EventSource only works with GET, not POST
 * This is kept for reference but we use fetch + readSSEStream for POST
 */
export function createEventSource(
  url: string,
  onMessage: (data: any) => void,
  onError?: (error: Event) => void
): EventSource {
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (error) {
      console.error('Failed to parse EventSource message:', error);
    }
  };

  if (onError) {
    eventSource.onerror = onError;
  }

  return eventSource;
}
