import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Pre-mock kafka before importing ingestion_worker
with patch('kafka.KafkaConsumer'), patch('kafka.KafkaProducer'):
    import ingestion_worker

def test_chunk_text():
    text = "hello " * 300
    chunks = ingestion_worker.chunk_text(text, chunk_size=250, overlap=30)
    assert len(chunks) > 1
    assert all(len(c.split()) <= 250 for c in chunks)

@patch('ingestion_worker.embed_text')
@patch('main.doc_db')
def test_process_document(mock_doc_db, mock_embed):
    mock_embed.return_value = [0.1] * 768
    
    mock_producer = MagicMock()
    event = {
        'doc_id': 'test-doc-id',
        'title': 'Test Title',
        'text': 'This is a test text'
    }
    
    ingestion_worker.process_document(event, mock_producer)
    
    # Verify mock producer was called to send updates
    assert mock_producer.send.call_count >= 2
    # Verify doc_db.insert was called
    assert mock_doc_db.insert.call_count >= 1
