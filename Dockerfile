
FROM python:3.12-slim

# Install git + Docker CLI (for sandboxed test execution)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
    > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Set default Git identity so the FixerAgent can commit fixes without errors
RUN git config --global user.email "bot@agentic-pipeline.local" \
    && git config --global user.name "Agentic Fixer Bot"

# Install only the Python dependencies this project actually uses
COPY requirements.docker.txt ./
RUN pip install --no-cache-dir -r requirements.docker.txt

# Copy the application code
COPY . .

# Create repos directory for cloned repositories
RUN mkdir -p /app/repos

EXPOSE 8000

# Run the FastAPI app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
