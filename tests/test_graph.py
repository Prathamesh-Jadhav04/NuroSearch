import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graph import KnowledgeGraph

@patch('requests.post')
def test_extract_triples(mock_post):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "response": '[{"subject": "A", "relation": "B", "object": "C"}]'
    }
    mock_post.return_value = mock_resp
    
    kg = KnowledgeGraph()
    triples = kg.extract_triples("A B C", "doc1")
    assert len(triples) == 1
    assert triples[0]["subject"] == "A"
    assert triples[0]["relation"] == "B"
    assert triples[0]["object"] == "C"

def test_dry_run_fallback():
    # Verify that when driver is None (unconnected), operations don't fail/crash
    kg = KnowledgeGraph()
    kg.available = False
    kg.driver = None
    
    kg.store_triples([{"subject": "A", "relation": "B", "object": "C"}], "doc1")
    res = kg.graph_search("A")
    assert res == []
    
    ctx = kg.hybrid_rag_context("What about Apple?", ["vector chunk info"])
    assert "vector chunk info" in ctx
    assert "No graph facts found" in ctx
