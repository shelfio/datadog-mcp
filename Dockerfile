# Use Python 3.13 slim image
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install UV
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY datadog_mcp/ datadog_mcp/

# Install dependencies
RUN uv sync

# Set environment variables for Datadog API (will be overridden at runtime)
ENV DD_API_KEY=""
ENV DD_APP_KEY=""

# Expose the server (though MCP uses stdio, this is for documentation)
EXPOSE 8080

# Run the MCP server
CMD ["uv", "run", "python", "datadog_mcp/server.py"]