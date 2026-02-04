# Use official Python slim image for smaller, faster builds
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install pipx and use it to install uv
RUN pip install --no-cache-dir pipx \
	&& pipx ensurepath \
	&& pipx install uv
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files (from build context root)
COPY app/copilot/pyproject.toml app/copilot/uv.lock ./

# Install pinned dependencies using uv pip
RUN uv pip install --system -r pyproject.toml --prerelease=allow

# Copy application code
COPY app/copilot/app ./app
COPY app/common ./common

# Copy JSON data directories (memory, observability, etc.)
# NOTE: conversations and dynamic_data JSON files are NOT copied - they come from Azure Files
COPY memory /app/memory
COPY app/copilot/observability /app/observability
COPY schemas /app/schemas
COPY config /app/config

# Create conversations directory for Azure Files mount (no Python files here)
RUN mkdir -p /app/conversations /app/dynamic_data /app/lib

# Copy conversation manager to /app/lib/ (separate from Azure Files mount)
COPY conversations/conversation_manager.py /app/lib/

# Expose port
EXPOSE 8080

# Start the app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
