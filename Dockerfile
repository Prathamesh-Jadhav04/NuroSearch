FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    zstd \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama (manually download and extract binary to avoid systemd/installer script errors)
RUN curl -fsSL https://ollama.com/download/ollama-linux-amd64.tar.zst | tar -x --zstd -C /usr

# Install Python dependencies (cached layer with CPU PyTorch resolution)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Set Ollama model storage path and pre-download models (cached layer)
ENV OLLAMA_MODELS=/app/ollama_models
RUN mkdir -p /app/ollama_models && \
    (ollama serve & PID=$! && sleep 5 && ollama pull nomic-embed-text && ollama pull qwen2.5:0.5b && kill $PID && wait $PID || true)

# Copy source
COPY . .

# Convert CRLF to LF for start.sh and make it executable
RUN tr -d '\r' < start.sh > start_lf.sh && mv start_lf.sh start.sh && chmod +x start.sh

# Create non-root user for security (handling pre-existing UID 1000)
RUN (id -u 1000 >/dev/null 2>&1 || useradd -m -u 1000 nurosearch) && chown -R 1000:1000 /app
USER 1000

EXPOSE 7860

CMD ["/bin/bash", "/app/start.sh"]
