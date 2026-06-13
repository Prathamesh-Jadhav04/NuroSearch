import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import coordinator app
import coordinator

@pytest.fixture
def client():
    coordinator.app.config['TESTING'] = True
    with coordinator.app.test_client() as client:
        yield client

def test_consistent_hashing():
    # Verify same ID always hashes to same worker
    w1 = coordinator.get_worker_for_id("doc_1")
    w2 = coordinator.get_worker_for_id("doc_1")
    assert w1['id'] == w2['id']
    
    # Verify different IDs distribute (e.g. check at least some variance)
    workers = set()
    for i in range(100):
        w = coordinator.get_worker_for_id(f"doc_{i}")
        workers.add(w['id'])
    assert len(workers) > 1  # Should distribute to multiple workers

@patch('requests.post')
def test_coordinator_insert(mock_post, client):
    # Set up mock response from worker
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"status": "inserted", "node": "worker-1"}
    mock_resp.status_code = 200
    mock_post.return_value = mock_resp
    
    response = client.post('/insert', json={"doc_id": "doc_1", "embedding": [0.1]*16})
    assert response.status_code == 200
    assert response.json['status'] == 'inserted'
    assert mock_post.called

@patch('requests.get')
def test_coordinator_search(mock_get, client):
    # Mock responses from 3 workers
    mock_resp_1 = MagicMock()
    mock_resp_1.status_code = 200
    mock_resp_1.json.return_value = {
        "results": [{"id": "doc_1", "distance": 0.1, "node": "worker-1"}]
    }
    
    mock_resp_2 = MagicMock()
    mock_resp_2.status_code = 200
    mock_resp_2.json.return_value = {
        "results": [{"id": "doc_2", "distance": 0.05, "node": "worker-2"}]
    }
    
    mock_resp_3 = MagicMock()
    mock_resp_3.status_code = 200
    mock_resp_3.json.return_value = {
        "results": [{"id": "doc_3", "distance": 0.3, "node": "worker-3"}]
    }
    
    # Side effect returns different response based on worker URL
    def get_side_effect(url, params=None, timeout=None):
        if "8081" in url:
            return mock_resp_1
        elif "8082" in url:
            return mock_resp_2
        else:
            return mock_resp_3
            
    mock_get.side_effect = get_side_effect
    
    # Reset worker health states
    for w in coordinator.WORKERS:
        w["alive"] = True
        
    response = client.get('/search?v=0.1,0.2&k=2')
    assert response.status_code == 200
    
    # Scatter gather: should merge and return top 2
    # doc_2 has distance 0.05 (best), doc_1 has 0.1 (second best)
    results = response.json['results']
    assert len(results) == 2
    assert results[0]['id'] == 'doc_2'
    assert results[1]['id'] == 'doc_1'
    assert response.json['nodes_queried'] == 3
