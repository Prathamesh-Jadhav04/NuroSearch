#!/bin/bash

# Start Ollama service in background
if command -v ollama >/dev/null 2>&1; then
    echo "Starting Ollama server..."
    ollama serve > /tmp/ollama.log 2>&1 &
    
    echo "Waiting for Ollama to start..."
    until curl -s http://127.0.0.1:11434/api/tags >/dev/null; do
        sleep 1
    done
    
    echo "Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
    
    echo "Pulling qwen2.5:0.5b..."
    ollama pull qwen2.5:0.5b
else
    echo "Ollama not installed, skipping startup"
fi

# Start NuroSearch Cluster Workers
echo "Starting Cluster Workers..."
python worker.py --port 8081 --node-id worker-1 --raft-host 127.0.0.1 --raft-port 8181 --partners 127.0.0.1:8182,127.0.0.1:8183 > /tmp/worker-1.log 2>&1 &
python worker.py --port 8082 --node-id worker-2 --raft-host 127.0.0.1 --raft-port 8182 --partners 127.0.0.1:8181,127.0.0.1:8183 > /tmp/worker-2.log 2>&1 &
python worker.py --port 8083 --node-id worker-3 --raft-host 127.0.0.1 --raft-port 8183 --partners 127.0.0.1:8181,127.0.0.1:8182 > /tmp/worker-3.log 2>&1 &

# Start Coordinator
echo "Starting Coordinator..."
python coordinator.py > /tmp/coordinator.log 2>&1 &

# Start Flask Main Server (replaces script process as PID 1)
echo "Starting main application..."
exec python main.py
