
FROM python:3.12-slim

# Install git, java, curl, and unzip (java is needed by sonar-scanner)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    default-jre-headless \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Download and install sonar-scanner-cli
RUN curl -o /tmp/sonar-scanner.zip -L https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-6.2.1.4610.zip \
    && unzip /tmp/sonar-scanner.zip -d /opt \
    && mv /opt/sonar-scanner-6.2.1.4610 /opt/sonar-scanner \
    && rm /tmp/sonar-scanner.zip

# Add sonar-scanner to PATH
ENV PATH="/opt/sonar-scanner/bin:${PATH}"

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

# Make startup script executable
RUN chmod +x start.sh

EXPOSE 8000 8501

# Run both FastAPI (8000) and Streamlit (8501)
CMD ["./start.sh"]
