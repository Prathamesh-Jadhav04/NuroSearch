import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app as flask_app, DIMS
from tests.benchmark_gate import random_vector

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

def test_stats_endpoint_returns_200(client):
    response = client.get('/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'count' in data
    assert 'algorithms' in data

def test_search_returns_results(client):
    v_str = ','.join(str(x) for x in random_vector(DIMS))
    response = client.get(f'/search?v={v_str}&k=5&algo=hnsw&metric=cosine')
    assert response.status_code == 200
    data = response.get_json()
    assert 'results' in data

def test_query_endpoint_sql(client):
    query_str = "SELECT * FROM vectors WHERE category = 'sports' LIMIT 2"
    response = client.post('/query', json={"query": query_str})
    assert response.status_code == 200
    data = response.get_json()
    assert data['query'] == query_str
    assert 'ast' in data
    assert 'compiled' in data
    assert 'results' in data
