FROM python:3.11-slim

WORKDIR /app

# Copy shared dependencies
COPY app/a2a-sdk /app/a2a-sdk
COPY app/common /app/common

# Copy agent files
COPY app/agents/escalation-comms-agent /app/agents/escalation-comms-agent

# Install dependencies
WORKDIR /app/agents/escalation-comms-agent
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8104

# Run the agent
CMD ["python", "main.py"]
