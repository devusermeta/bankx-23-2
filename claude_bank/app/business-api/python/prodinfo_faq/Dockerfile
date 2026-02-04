# Use official Python slim image for smaller, faster builds
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install pipx and use it to install uv
RUN pip install --no-cache-dir pipx \
	&& pipx ensurepath \
	&& pipx install uv
ENV PATH="/root/.local/bin:$PATH"

# Copy service files from build context root
COPY app/business-api/python/prodinfo_faq/ .
COPY app/common /app/common

# Create virtual environment and install dependencies
RUN uv venv
RUN uv sync --frozen

# Expose port
EXPOSE 8076

# Start the app with Python using the virtual environment
CMD [".venv/bin/python", "main.py"]
