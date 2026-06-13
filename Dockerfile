FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Convert CRLF to LF for start.sh and make it executable
RUN sed -i -e 's/\r$//' /app/start.sh && chmod +x /app/start.sh

# Non-root user for security
RUN useradd -m -u 1000 nurosearch && chown -R nurosearch:nurosearch /app
USER nurosearch

EXPOSE 7860

CMD ["/bin/bash", "/app/start.sh"]
