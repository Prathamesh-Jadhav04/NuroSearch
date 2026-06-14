import os
import json
import urllib.request
from flask import Flask, jsonify

app = Flask(__name__)

class OllamaClient:
    def __init__(self, host=None, port=None):
        env_url = os.environ.get('OLLAMA_BASE_URL')
        if env_url:
            url_clean = env_url.replace("http://", "").replace("https://", "")
            url_clean = url_clean.split("/")[0]
            if ":" in url_clean:
                self.host, port_str = url_clean.split(":", 1)
                try:
                    self.port = int(port_str)
                except ValueError:
                    self.port = 11434
            else:
                self.host = url_clean
                self.port = 11434
        else:
            self.host = host or os.environ.get('OLLAMA_HOST', '127.0.0.1')
            try:
                self.port = int(port or os.environ.get('OLLAMA_PORT', 11434))
            except ValueError:
                self.port = 11434
        self.embed_model = "nomic-embed-text"
        self.gen_model = "qwen2.5:0.5b"

    def _req(self, method, path, body=None):
        url = f"http://{self.host}:{self.port}{path}"
        data = body.encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, method=method)
        if data:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.read().decode("utf-8")
        except Exception:
            return None

    def is_available(self):
        return self._req("GET", "/api/tags") is not None

ollama = OllamaClient()

@app.route("/")
def home():
    return "OK"

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "ollama": "online" if ollama.is_available() else "offline"
    }), 200
