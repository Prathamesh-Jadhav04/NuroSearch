import json
import random
import sys
import sqlite3
import requests

# Default configuration
PORT = 8080
BASE_URL = f"http://localhost:{PORT}"
DIMS = 16
DOC_DIMS = 768

print("========================================")
print("     NuroSearch Dummy Data Seeder       ")
print("========================================")

# 1. Generate 20 distinct 16-D vectors with different categories
categories = ["sports", "tech", "health", "finance", "space"]
vector_data = [
    # sports
    {
        "meta": "Football match: Real Madrid vs Barcelona El Clasico highlights and scores.",
        "cat": "sports",
        "emb": [0.95, 0.1, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3]
    },
    {
        "meta": "Olympic games athletics finals: 100m sprint gold medal winner breakdown.",
        "cat": "sports",
        "emb": [0.9, 0.15, 0.0, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.35]
    },
    {
        "meta": "Wimbledon tennis tournament: Grand Slam finals championship match point.",
        "cat": "sports",
        "emb": [0.88, 0.05, 0.08, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.4]
    },
    {
        "meta": "NBA basketball finals: LA Lakers vs Boston Celtics game 7 analysis.",
        "cat": "sports",
        "emb": [0.92, 0.08, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.32]
    },
    # tech
    {
        "meta": "Quantum computing breakthrough: Qubit coherence time increases ten-fold.",
        "cat": "tech",
        "emb": [0.05, 0.96, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.1]
    },
    {
        "meta": "Generative AI model training pipelines: Reinforcement Learning from Human Feedback (RLHF).",
        "cat": "tech",
        "emb": [0.1, 0.92, 0.1, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.2]
    },
    {
        "meta": "Cybersecurity protocols: Zero-trust architecture implementation guide.",
        "cat": "tech",
        "emb": [0.0, 0.89, 0.05, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.25, 0.3]
    },
    {
        "meta": "Microchip manufacturing: 2nm lithography process scale-up in semiconductor fabs.",
        "cat": "tech",
        "emb": [0.08, 0.94, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.25]
    },
    # health
    {
        "meta": "Healthy diet: Mediterranean diet recipes rich in olive oil, fish, and greens.",
        "cat": "health",
        "emb": [0.0, 0.05, 0.95, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.25]
    },
    {
        "meta": "Cancer immunotherapy: Monoclonal antibodies targeting PD-1 receptors.",
        "cat": "health",
        "emb": [0.0, 0.1, 0.92, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.3]
    },
    {
        "meta": "Cardiovascular fitness: High-Intensity Interval Training (HIIT) benefits for heart rate.",
        "cat": "health",
        "emb": [0.3, 0.05, 0.88, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.28]
    },
    {
        "meta": "Mental health: Mindfulness meditation techniques for stress reduction.",
        "cat": "health",
        "emb": [0.0, 0.0, 0.96, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.22]
    },
    # finance
    {
        "meta": "Stock market trends: S&P 500 reaches all-time high amidst tech rally.",
        "cat": "finance",
        "emb": [0.1, 0.2, 0.0, 0.94, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.05, 0.18]
    },
    {
        "meta": "Central bank interest rates: Federal Reserve hints at rate cuts next quarter.",
        "cat": "finance",
        "emb": [0.0, 0.1, 0.05, 0.97, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.12]
    },
    {
        "meta": "Cryptocurrency regulation: European Union implements MiCA framework for digital assets.",
        "cat": "finance",
        "emb": [0.0, 0.3, 0.0, 0.91, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.15]
    },
    {
        "meta": "Inflation hedge: Gold prices surge past record highs due to global uncertainty.",
        "cat": "finance",
        "emb": [0.0, 0.05, 0.0, 0.95, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.22]
    },
    # space
    {
        "meta": "Mars exploration: Perseverance rover discovers complex organic molecules in crater.",
        "cat": "space",
        "emb": [0.0, 0.1, 0.0, 0.05, 0.96, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.2]
    },
    {
        "meta": "James Webb Space Telescope: Infrared images reveal galaxies from early universe.",
        "cat": "space",
        "emb": [0.0, 0.15, 0.0, 0.0, 0.92, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.25]
    },
    {
        "meta": "Exoplanet discovery: Kepler-186f found orbiting in habitable zone of red dwarf.",
        "cat": "space",
        "emb": [0.0, 0.05, 0.1, 0.0, 0.94, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.15, 0.28]
    },
    {
        "meta": "Asteroid defense: DART mission successfully alters asteroid orbit by kinetic impact.",
        "cat": "space",
        "emb": [0.1, 0.08, 0.0, 0.0, 0.95, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.25]
    }
]

# Standardize vectors (so they have length 1 for clean cosine distance metrics)
for v in vector_data:
    # pad with zeros if not full length
    if len(v["emb"]) < DIMS:
        v["emb"] += [0.0] * (DIMS - len(v["emb"]))
    # normalize
    mag = sum(x**2 for x in v["emb"]) ** 0.5
    if mag > 0:
        v["emb"] = [x / mag for x in v["emb"]]

# Document data for RAG/hybrid search
documents = [
    {
        "title": "Introduction to Artificial Intelligence",
        "text": "Artificial Intelligence (AI) refers to the simulation of human intelligence in machines that are programmed to think like humans and mimic their actions. The term may also be applied to any machine that exhibits traits associated with a human mind such as learning and problem-solving. AI includes subfields like machine learning and deep learning, which focus on developing algorithms that can learn from data."
    },
    {
        "title": "Exploring the Solar System",
        "text": "The solar system consists of our Sun and everything bound to it by gravity, including the eight planets (Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune), dozens of moons, and millions of asteroids and comets. Mars is currently the target of intense robotic exploration, with rovers searching for signs of past water and potential organic compounds."
    },
    {
        "title": "A Guide to Clean Eating",
        "text": "A healthy diet is crucial for maintaining good health and preventing chronic diseases. Clean eating focuses on consuming whole foods that are minimally processed, refined, and handled, making them as close to their natural form as possible. This includes plenty of fresh fruits, vegetables, lean proteins, whole grains, and healthy fats while limiting added sugars and sodium."
    },
    {
        "title": "Financial Markets and Stocks",
        "text": "Financial markets allow buyers and sellers to trade financial assets such as stocks, bonds, currencies, and derivatives. The stock market is a collection of exchanges where shares of publicly held companies are bought and sold. Stock prices fluctuate based on company performance, investor sentiment, interest rates set by central banks, and macroeconomic trends."
    },
    {
        "title": "History of the Olympic Games",
        "text": "The modern Olympic Games are the leading international sporting event featuring summer and winter sports competitions in which thousands of athletes from around the world participate in a variety of competitions. The Olympic Games are considered the world's foremost sports competition with more than 200 nations participating. The first modern Games were held in Athens, Greece, in 1896."
    }
]

# Check if the server is running
server_online = False
try:
    resp = requests.get(f"{BASE_URL}/status", timeout=2)
    if resp.status_code == 200:
        server_online = True
        print(f"[HTTP] Connected to server at {BASE_URL}")
except Exception:
    pass

if not server_online:
    # Try alternative port
    PORT = 7860
    BASE_URL = f"http://localhost:{PORT}"
    try:
        resp = requests.get(f"{BASE_URL}/status", timeout=2)
        if resp.status_code == 200:
            server_online = True
            print(f"[HTTP] Connected to server at {BASE_URL}")
    except Exception:
        pass

if not server_online:
    print(f"\n[WARNING] Could not connect to NuroSearch server on port 8080 or 7860.")
    print("Ensure the server is running using: python main.py")
    print("Seeding will proceed directly via SQLite database injection where possible.\n")

# Seeding Vectors
inserted_vectors = 0
if server_online:
    print("Seeding vectors via HTTP API...")
    for item in vector_data:
        try:
            r = requests.post(f"{BASE_URL}/insert", json={
                "metadata": item["meta"],
                "category": item["cat"],
                "embedding": item["emb"]
            })
            if r.status_code == 200:
                inserted_vectors += 1
        except Exception as e:
            print(f"Failed to insert vector via HTTP: {e}")
            break
else:
    # SQLite Direct insertion
    try:
        conn = sqlite3.connect("vectors.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS vectors (id INTEGER PRIMARY KEY AUTOINCREMENT, metadata TEXT, category TEXT, embedding TEXT)")
        for item in vector_data:
            cursor.execute(
                "INSERT INTO vectors (metadata, category, embedding) VALUES (?, ?, ?)",
                (item["meta"], item["cat"], json.dumps(item["emb"]))
            )
        conn.commit()
        conn.close()
        inserted_vectors = len(vector_data)
        print("Seeded vectors directly into vectors.db SQLite database.")
    except Exception as e:
        print(f"SQLite seeding failed: {e}")

print(f"-> Seeded {inserted_vectors}/{len(vector_data)} vectors successfully.")

# Seeding Documents
inserted_docs = 0
ollama_online = False
if server_online:
    try:
        status_data = requests.get(f"{BASE_URL}/status").json()
        ollama_online = status_data.get("ollamaAvailable", False)
    except Exception:
        pass

if server_online and ollama_online:
    print("Ollama is ONLINE. Seeding documents via HTTP API...")
    for doc in documents:
        try:
            r = requests.post(f"{BASE_URL}/doc/insert", json={
                "title": doc["title"],
                "text": doc["text"]
            })
            if r.status_code == 200:
                inserted_docs += 1
            else:
                print(f"API insertion returned: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"Failed to insert document: {e}")
else:
    # Ollama is offline or server is offline; insert directly to SQLite with mock 768-D embeddings
    try:
        conn = sqlite3.connect("vectors.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, text TEXT, embedding TEXT)")
        
        # Generate 768-D mock embeddings
        for doc in documents:
            # Generate deterministic mock embedding based on hash
            random.seed(doc["title"])
            emb = [random.gauss(0, 1) for _ in range(DOC_DIMS)]
            mag = sum(x**2 for x in emb) ** 0.5
            if mag > 0:
                emb = [x / mag for x in emb]
                
            cursor.execute(
                "INSERT INTO documents (title, text, embedding) VALUES (?, ?, ?)",
                (doc["title"], doc["text"], json.dumps(emb))
            )
        conn.commit()
        conn.close()
        inserted_docs = len(documents)
        print("Seeded documents directly into vectors.db SQLite database (with mock 768-D embeddings).")
        if server_online:
            print("[IMPORTANT] Please restart the NuroSearch server to load these new SQLite documents into memory!")
    except Exception as e:
        print(f"SQLite document seeding failed: {e}")

print(f"-> Seeded {inserted_docs}/{len(documents)} documents successfully.")
print("\nDone! Use the generated scripts and guide to test every feature.")
