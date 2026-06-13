"""
NuroSearch Document Ingestion Worker
Runs as a separate process alongside Flask.
Consumes document upload events from Kafka and processes them asynchronously.

Start with: python ingestion_worker.py
"""

import os
import json
import time
import logging
import requests
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [Worker] %(message)s')
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.environ.get('KAFKA_BOOTSTRAP', 'localhost:9092')
INGEST_TOPIC = 'nurosearch-document-ingestion'
STATUS_TOPIC = 'nurosearch-document-status'

def chunk_text(text: str, chunk_size: int = 250, overlap: int = 30) -> list[str]:
    """Split text into chunks of ~chunk_size words with overlap."""
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text]
    chunks = []
    step = max(chunk_size - overlap, 1)
    for i in range(0, len(words), step):
        end = min(i + chunk_size, len(words))
        chunks.append(" ".join(words[i:end]))
        if end == len(words):
            break
    return chunks

def embed_text(text: str) -> list[float]:
    """Call local Ollama for embedding. Same as Flask app."""
    # Find Ollama URL
    host = os.environ.get('OLLAMA_HOST', '127.0.0.1')
    port = os.environ.get('OLLAMA_PORT', '11434')
    env_url = os.environ.get('OLLAMA_BASE_URL')
    if env_url:
        url = f"{env_url.rstrip('/')}/api/embeddings"
    else:
        url = f"http://{host}:{port}/api/embeddings"
        
    try:
        response = requests.post(url, json={
            'model': 'nomic-embed-text',
            'prompt': text
        }, timeout=30)
        response.raise_for_status()
        data = response.json()
        embedding = data.get('embedding')
        if not embedding:
            raise ValueError(f"No embedding in response: {data}")
        return embedding
    except Exception as e:
        raise RuntimeError(f"Ollama embedding failed: {e}")

def process_document(event: dict, producer: KafkaProducer):
    """
    Full document processing pipeline:
    1. Chunk text
    2. Embed each chunk via Ollama
    3. Insert into DocumentDB HNSW index
    4. Publish status update to STATUS_TOPIC
    """
    doc_id = event['doc_id']
    title = event['title']
    text = event['text']
    
    logger.info(f"Processing document: {title} (id={doc_id})")
    
    # Publish "processing" status
    producer.send(STATUS_TOPIC, {
        'doc_id': doc_id, 'status': 'processing', 'progress': 0, 'title': title
    })
    
    chunks = chunk_text(text)
    logger.info(f"  Split into {len(chunks)} chunks")
    
    # Import doc_db from main
    from main import doc_db
    
    for i, chunk in enumerate(chunks):
        try:
            embedding = embed_text(chunk)
            
            chunk_title = f"{title} [{i+1}/{len(chunks)}]" if len(chunks) > 1 else title
            doc_db.insert(title=chunk_title, text=chunk, emb=embedding)
            
            progress = int((i + 1) / len(chunks) * 100)
            producer.send(STATUS_TOPIC, {
                'doc_id': doc_id, 'status': 'processing', 
                'progress': progress, 'chunk': i + 1, 'total': len(chunks), 'title': title
            })
            logger.info(f"  Chunk {i+1}/{len(chunks)} indexed")
            
        except Exception as e:
            logger.error(f"  Failed chunk {i}: {e}")
            producer.send(STATUS_TOPIC, {
                'doc_id': doc_id, 'status': 'error', 'error': str(e), 'title': title
            })
            return
    
    producer.send(STATUS_TOPIC, {
        'doc_id': doc_id, 'status': 'complete', 'progress': 100, 'n_chunks': len(chunks), 'title': title
    })
    logger.info(f"Document {title} processing complete ({len(chunks)} chunks)")

def run_worker():
    logger.info("NuroSearch Ingestion Worker starting...")
    logger.info(f"Connecting to Kafka at {KAFKA_BOOTSTRAP}...")
    
    try:
        consumer = KafkaConsumer(
            INGEST_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id='nurosearch-ingest-workers',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            api_version=(0, 10)
        )
        
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            api_version=(0, 10)
        )
    except Exception as e:
        logger.error(f"Failed to initialize Kafka consumer/producer: {e}")
        return
    
    logger.info(f"Listening on topic: {INGEST_TOPIC}")
    
    for message in consumer:
        event = message.value
        logger.info(f"Received ingestion event: {event.get('title', 'unknown')}")
        try:
            process_document(event, producer)
            producer.flush()
        except Exception as e:
            logger.error(f"Worker error: {e}")

if __name__ == '__main__':
    run_worker()
