# Use official Python slim image for smaller, faster builds
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install pipx and use it to install uv
RUN pip install --no-cache-dir pipx \
	&& pipx ensurepath \
	&& pipx install uv
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/app/common:${PYTHONPATH}"

# Copy service files from build context root
COPY app/business-api/python/payment-unified/ .
COPY app/common /app/common
COPY dynamic_data /app/dynamic_data
COPY schemas /app/schemas

# Create virtual environment and install dependencies
RUN uv venv --clear
RUN uv pip install -r requirements.txt

# Expose port
EXPOSE 8076

# Start the app with Python using the virtual environment
CMD [".venv/bin/python", "main.py"]
