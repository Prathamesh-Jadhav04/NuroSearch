#!/bin/bash

# Set Ollama models directory explicitly
export OLLAMA_MODELS=/app/ollama_models

# Start Ollama service in background
if command -v ollama >/dev/null 2>&1; then
    echo "Starting Ollama server..."
    ollama serve > /tmp/ollama.log 2>&1 &
    
    echo "Waiting for Ollama to start (max 30 seconds)..."
    timeout=30
    counter=0
    until curl -s http://127.0.0.1:11434/api/tags >/dev/null || [ $counter -eq $timeout ]; do
        sleep 1
        counter=$((counter + 1))
    done
    
    if [ $counter -eq $timeout ]; then
        echo "Ollama server failed to start within $timeout seconds."
    else
        echo "Ollama server started successfully."
    fi
else
    echo "Ollama not installed, skipping startup"
fi

# Start NuroSearch Cluster Workers & Coordinator (skipped on Hugging Face Spaces to conserve CPU/RAM)
echo "Starting Cluster Workers..."
python worker.py --port 8081 --node-id worker-1 --raft-host 127.0.0.1 --raft-port 8181 --partners 127.0.0.1:8182,127.0.0.1:8183 > /tmp/worker-1.log 2>&1 &
python worker.py --port 8082 --node-id worker-2 --raft-host 127.0.0.1 --raft-port 8182 --partners 127.0.0.1:8181,127.0.0.1:8183 > /tmp/worker-2.log 2>&1 &
python worker.py --port 8083 --node-id worker-3 --raft-host 127.0.0.1 --raft-port 8183 --partners 127.0.0.1:8181,127.0.0.1:8182 > /tmp/worker-3.log 2>&1 &

echo "Starting Coordinator..."
python coordinator.py > /tmp/coordinator.log 2>&1 &

# Start Flask Main Server via Gunicorn (replaces script process as PID 1)
echo "Starting main application via Gunicorn..."
exec gunicorn --bind 0.0.0.0:7860 --workers 1 --threads 4 --timeout 120 main:app
